"""Optional headless-browser warmup for Akamai/Datadome anti-bot.

When the env flag ``IBERIA_USE_BROWSER_WARMUP=1`` or
``EASYJET_USE_BROWSER_WARMUP=1`` is set on a provider, the warmup helper
will spawn a headless Chromium via Playwright, navigate to the provider's
marketing URL, wait for the JS sensor to set its cookies (Datadome sets
``datadome``, Akamai sets ``_abck`` / ``bm_sz``), and return those cookies
for the caller to merge into its HTTP session.

The cookies are returned with full domain / path so the merge can build
real ``http.cookiejar.Cookie`` objects. Empirically, Akamai/Datadome issue
domain-scoped tokens (e.g. ``.iberia.com``, ``www.easyjet.com``) and the
stdlib jar's RFC 6265 domain-matching rejects cookies added with an empty
domain on send. Build Cookie with explicit domain from the Playwright
context.

Playwright is imported lazily and optionally: the project does not depend on
it at install time. If the package is missing or the Chromium binary isn't
downloaded, the call must fail soft (returning ``None``) so the rest of the
warmup path falls back to curl_cffi best-effort.

Install (out-of-band, only when this path is turned on):
    uv pip install playwright
    playwright install chromium
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from http.cookiejar import Cookie
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HarvestedCookie:
    """One cookie harvested from Playwright, with the fields needed to
    rebuild it on a stdlib ``http.cookiejar.Cookie`` for curl_cffi.

    ``secure`` defaults to True because Akamai / Datadome WAF tokens are
    only ever stamped on the HTTPS path; if Playwright's ``cookies()``
    report omits the flag, defaulting to True keeps the cookie in the
    right slot for the subsequent API calls.

    ``expires`` is normalized to ``None`` for the values Playwright
    reports as session cookies (``-1``, ``0``, or absent), so the stdlib
    jar sets ``discard=True`` instead of getting confused by ``-1``.
    """

    name: str
    value: str
    domain: str
    path: str
    secure: bool = True
    expires: int | None = None

    @classmethod
    def from_playwright_entry(cls, entry: Mapping[str, object]) -> "HarvestedCookie | None":
        """Normalize a Playwright ``context.cookies()[i]`` entry.

        Returns ``None`` for entries that don't have a non-empty string
        name+value (catches ``name=None``, ``value=None``, and the
        ``name=""`` case Playwright emits after cookie deletion). Without
        this filter, an empty-name cookie would be stamped into the jar as
        ``domain="" + name=""`` and the stdlib jar would silently fail to
        match it on subsequent sends.
        """
        name = entry.get("name")
        value = entry.get("value")
        if not (isinstance(name, str) and isinstance(value, str) and name and value):
            return None
        domain = entry.get("domain") or ""
        path = entry.get("path") or "/"
        secure = bool(entry.get("secure", True))
        raw_expires = entry.get("expires")
        # Playwright reports -1 (or omits) for session cookies; stdlib
        # jar expects ``None`` for those and rejects ``-1``.
        expires: int | None = None
        if isinstance(raw_expires, (int, float)) and raw_expires > 0:
            expires = int(raw_expires)
        return cls(name=name, value=value, domain=domain, path=path, secure=secure, expires=expires)


def _import_playwright() -> Any:
    """Late-bound Playwright import; returns None when not installed."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError:
        logger.info("playwright not installed; browser warmup is a no-op")
        return None
    return sync_playwright


# Akamai's sensor obfuscation script obfuscates a sensor JS payload that
# collects mouse/window events and only stamps a valid ``_abck`` cookie
# once enough telemetry has accumulated. Datadome performs a similar dance
# with its own sensor JS. Empirically, 500ms is too short; WAF tokens are
# not yet stable on the first poll. 2500ms is the target observed in
# cloudscraper + nodriver reference runs.
_SENSOR_DWELL_MS: int = 2500


def harvest_cookies_with_browser(
    target_url: str,
    *,
    referer_path: str = "",
    timeout_ms: int = 15000,
) -> list[HarvestedCookie] | None:
    """Drive a headless Chromium to ``target_url`` and return harvested cookies.

    Returns ``None`` on any failure (Playwright missing, Chromium missing,
    target unreachable). Each cookie is returned with full domain / path so
    the merge path can build a domain-aware ``http.cookiejar.Cookie`` capabale
    of passing the RFC 6265 strict domain-match check on subsequent sends.
    """
    sync_playwright = _import_playwright()
    if sync_playwright is None:
        return None

    full_url = f"{target_url}{referer_path}"
    harvested: list[HarvestedCookie] = []
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as exc:  # noqa: BLE001 - want broad catch
                logger.info("Chromium binary not installed (%s); falling back", type(exc).__name__)
                return None
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    locale="en-GB",
                )
                context.set_default_timeout(timeout_ms)
                page = context.new_page()
                page.goto(full_url, wait_until="domcontentloaded", timeout=timeout_ms)
                # Akamai's sensor JS needs ≥1.5s of telemetry to stamp a
                # stable ``_abck``; Datadome similar. Don't poll early.
                page.wait_for_timeout(_SENSOR_DWELL_MS)
                record = context.cookies()
                for entry in record:
                    cookie = HarvestedCookie.from_playwright_entry(entry)
                    if cookie is not None:
                        harvested.append(cookie)
            finally:
                try:
                    browser.close()
                except Exception:  # noqa: BLE001 - best effort
                    pass
    except Exception as exc:  # noqa: BLE001 - top safety net
        logger.info("Browser warmup failed (%s): %s", type(exc).__name__, exc)
        return None
    return harvested


@dataclass(frozen=True, slots=True)
class BrowserResponse:
    """Minimal duck-typed response shim that the captcha helper can read.

    Built from Playwright's ``APIResponse`` so the provider's existing
    ``detect_captcha_kind(response, rules=...)`` works without depending on
    ``curl_cffi.Response``. ``.text``, ``.status_code`` and ``.json()`` are
    enough for the captcha rule sweep + the downstream
    ``ProviderSourceFetchError`` path.
    """

    status_code: int
    body_text: str

    @property
    def text(self) -> str:  # captcha helper reads ``.text``
        return self.body_text

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> object:
        return json.loads(self.body_text)


def request_via_browser(
    method: str,
    url: str,
    *,
    json_body: Mapping[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout_ms: int = 15000,
    warmup_url: str | None = None,
    warmup_referer_path: str = "",
) -> BrowserResponse | None:
    """Run an HTTP request through real Chromium and return a ``BrowserResponse``.

    Goes through real Chromium's TLS / HTTP/2 stack so Akamai bot-manager
    sees a TLS JA4 + frame order + header order + cookie set that's
    indistinguishable from a real browser tab — instead of a ``curl_cffi``
    impersonation profile the bot-manager has long since catalogued.

    ``warmup_url`` is the contract that turns this from "real stack, cold
    cookies" into "real stack, sensor cookies already attached". When
    supplied, the helper navigates there *on the same context* the API call
    then runs through; Akamai's sensor JS executes during that navigation
    and stamps ``_abck`` / ``bm_sz`` (Datadome stamps ``datadome``) on the
    context cookie jar, so the subsequent ``request.fetch`` carries them on
    exactly the HTTP/2 connection the JS sensor's telemetry was generated
    for. Without the warmup navigation the request goes through Chromium's
    networking but with no sensor cookies — Akamai bot-manager still 403s in
    that case. ``warmup_referer_path`` is appended to ``warmup_url`` when
    non-empty so providers can keep using their per-language landing pages.

    Returns ``None`` whenever Playwright can't service the request
    (Playwright missing, Chromium binary missing, launch failure, request
    exception, warmup-nav failure). The provider must keep its curl_cffi
    fallback intact so a ``None`` here means "use the curl path".
    """
    sync_playwright = _import_playwright()
    if sync_playwright is None:
        return None

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as exc:  # noqa: BLE001 - want broad catch
                logger.info("Chromium binary not installed (%s); falling back", type(exc).__name__)
                return None
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    locale="en-GB",
                )
                context.set_default_timeout(timeout_ms)
                if warmup_url:
                    try:
                        page = context.new_page()
                        target = (
                            f"{warmup_url.rstrip('/')}{warmup_referer_path}"
                            if warmup_referer_path
                            else warmup_url
                        )
                        page.goto(target, wait_until="domcontentloaded", timeout=timeout_ms)
                        # Sensor JS needs the same dwell window the standalone
                        # ``harvest_cookies_with_browser`` uses; without it the
                        # ``_abck`` we want to send on the API call isn't ready
                        # yet (Akamai rotates it once ≥1.5s of telemetry lands).
                        page.wait_for_timeout(_SENSOR_DWELL_MS)
                    except Exception as exc:  # noqa: BLE001 - warmup is best-effort
                        logger.info(
                            "Browser warmup nav failed (%s): %s",
                            type(exc).__name__,
                            exc,
                        )
                request = context.request
                response = request.fetch(
                    url,
                    method=method.upper(),
                    headers=dict(headers or {}),
                    data=json.dumps(dict(json_body)) if json_body is not None else None,
                    timeout=max(1.0, timeout_ms / 1000),
                )
                return BrowserResponse(status_code=response.status, body_text=response.text() or "")
            finally:
                try:
                    browser.close()
                except Exception:  # noqa: BLE001 - best effort
                    pass
    except Exception as exc:  # noqa: BLE001 - top safety net
        logger.info("Browser request failed (%s): %s", type(exc).__name__, exc)
        return None


def merge_cookies_into_session(session: Any, cookies: list[HarvestedCookie] | None) -> None:
    """Copy harvested cookies into the session cookie jar with their proper domain.

    Always constructs ``http.cookiejar.Cookie`` explicitly so the stdlib jar
    (used by curl_cffi) keeps each cookie under its real domain. RFC 6265
    strict-matching then sends those cookies on subsequent requests to
    matching hosts, which is what Akamai / Datadome require to recognise the
    replay as legit.

    The dual-shape shortcut is preserved for testing: requests-style
    ``RequestsCookieJar.set(name, value)`` is still tried first for callers
    that build sessions with that surface; on a failed shortcut (curl_cffi's
    stdlib jar) the path falls back to stdlib Cookie + ``set_cookie``.
    """
    if not cookies:
        return
    jar = getattr(session, "cookies", None)
    if jar is None:
        return
    try:
        for entry in cookies:
            if hasattr(jar, "set") and callable(getattr(jar, "set", None)):
                try:
                    jar.set(entry.name, entry.value)  # type: ignore[attr-defined]
                    continue
                except TypeError:
                    # Some jars don't accept the 2-arg shortcut; fall through
                    # to the stdlib-style path below.
                    pass
            cookie = Cookie(
                version=0,
                name=entry.name,
                value=entry.value,
                port=None,
                port_specified=False,
                domain=entry.domain,
                domain_specified=bool(entry.domain),
                domain_initial_dot=entry.domain.startswith("."),
                path=entry.path or "/",
                path_specified=bool(entry.path),
                secure=entry.secure,
                expires=entry.expires,
                discard=entry.expires is None,
                comment=None,
                comment_url=None,
                rest={},
                rfc2109=False,
            )
            jar.set_cookie(cookie)
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        logger.debug("merge_cookies_into_session skipped: %s", exc)


def merge_cookies_from_mapping(session: Any, cookies: Mapping[str, str] | None) -> None:
    """TESTS-ONLY — DO NOT CALL FROM PRODUCTION CODE.

    Accepts a flat ``name → value`` mapping (which is what the legacy
    helper returned) and pushes it into the session jar via the requests-
    style ``set`` shortcut. The cookies are stamped with empty domain, so
    they will NOT survive RFC 6265 domain matching on real curls — they
    only round-trip inside ``requests.testing`` rigs.

    Production paths must always go through
    :func:`harvest_cookies_with_browser` + :func:`merge_cookies_into_session`
    so each cookie carries its real Playwright-reported ``domain``. This
    shim exists to keep unit fixtures happy without forcing every test to
    construct ``HarvestedCookie`` entries by hand.
    """
    if not cookies:
        return
    jar = getattr(session, "cookies", None)
    if jar is None:
        return
    try:
        for name, value in cookies.items():
            if hasattr(jar, "set") and callable(getattr(jar, "set", None)):
                jar.set(name, value)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        logger.debug("merge_cookies_from_mapping skipped: %s", exc)
