"""Optional headless-browser warmup for Akamai/Datadome anti-bot.

When the env flag `USE_BROWSER_WARMUP=1` is set on a provider, the warmup
helper will spawn a headless Chromium via Playwright, navigate to the
provider's marketing URL, wait for the JS sensor to set its cookies (Datadome
sets `datadome`, Akamai sets `_abck` / `bm_sz`), and return those cookies for
the caller to merge into its HTTP session.

Playwright is imported lazily and optionally: the project does not depend on
it at install time. If the package is missing or the Chromium binary isn't
downloaded, the call must fail soft (returning `None`) so the rest of the
warmup path falls back to curl_cffi best-effort.

Install (out-of-band, only when this path is turned on):
    uv pip install playwright
    playwright install chromium
"""

from __future__ import annotations

from collections.abc import Mapping
from http.cookiejar import Cookie
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _import_playwright() -> Any:
    """Late-bound Playwright import; returns None when not installed."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError:
        logger.info("playwright not installed; browser warmup is a no-op")
        return None
    return sync_playwright


def harvest_cookies_with_browser(
    target_url: str,
    *,
    referer_path: str = "",
    timeout_ms: int = 15000,
) -> Mapping[str, str] | None:
    """Drive a headless Chromium to ``target_url`` and return harvested cookies.

    Returns ``None`` on any failure (Playwright missing, Chromium missing,
    target unreachable). The cookies are mapped to a flat ``str -> str`` dict
    for direct injection into a requests/curl_cffi session cookie jar.
    """
    sync_playwright = _import_playwright()
    if sync_playwright is None:
        return None

    full_url = f"{target_url}{referer_path}"
    cookies: dict[str, str] = {}
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
                # Give the JS sensor a few hundred ms to push its cookies.
                page.wait_for_timeout(500)
                playwright_cookies = context.cookies()
            finally:
                try:
                    browser.close()
                except Exception:  # noqa: BLE001 - best effort
                    pass
        for entry in playwright_cookies:
            name = entry.get("name")
            value = entry.get("value")
            if isinstance(name, str) and isinstance(value, str):
                cookies[name] = value
    except Exception as exc:  # noqa: BLE001 - top safety net
        logger.info("Browser warmup failed (%s): %s", type(exc).__name__, exc)
        return None
    return cookies


def merge_cookies_into_session(session: Any, cookies: Mapping[str, str] | None) -> None:
    """Copy a cookie mapping into a requests/curl_cffi session cookie jar.

    Works for both stdlib :class:`http.cookiejar.CookieJar` (the type used by
    ``curl_cffi``) and ``requests.cookies.RequestsCookieJar`` (used by the
    ``requests``-shaped sessions we run in tests):

    - If the jar exposes a ``set(name, value)`` shorthand (requests-style) we
      use it directly and skip the heavier Cookie construction.
    - Otherwise we build a fully populated ``http.cookiejar.Cookie`` and call
      ``jar.set_cookie(cookie)``, which works on the stdlib jar and on
      RequestsCookieJar alike.

    This avoids silently no-op'ing the merge when the surface differs, which
    would otherwise see Playwright spin up correctly and then lose every
    harvested cookie to a swallowed ``AttributeError``.
    """
    if not cookies:
        return
    jar = getattr(session, "cookies", None)
    if jar is None:
        return
    try:
        for name, value in cookies.items():
            if hasattr(jar, "set") and callable(getattr(jar, "set", None)):
                try:
                    jar.set(name, value)  # type: ignore[attr-defined]
                    continue
                except TypeError:
                    # Some jars don't accept the 2-arg shortcut; fall through
                    # to the stdlib-style path below.
                    pass
            cookie = Cookie(
                version=0,
                name=name,
                value=value,
                port=None,
                port_specified=False,
                domain="",
                domain_specified=False,
                domain_initial_dot=False,
                path="/",
                path_specified=True,
                secure=False,
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={},
                rfc2109=False,
            )
            jar.set_cookie(cookie)
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        logger.debug("merge_cookies_into_session skipped: %s", exc)
