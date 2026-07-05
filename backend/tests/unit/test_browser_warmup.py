"""Direct tests for the optional browser warmup helper.

The helper is allowed to fail soft when Playwright (or its Chromium binary)
is missing; production code must never crash because Playwright cannot be
imported. These tests pin that contract via simple monkeypatching of
``sys.modules`` so no real Chromium is required.
"""

from __future__ import annotations

import sys
from http.cookiejar import Cookie
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from app.infrastructure.providers import _browser_warmup
from app.infrastructure.providers._browser_warmup import HarvestedCookie


# ─────────────────────────────────────────────────────────────────────────
# harvest_cookies_with_browser: Playwright is missing or Chromium-binary
# missing → ``None`` (no crash). Dwell time is 2500ms (Akamai sensor).
# ─────────────────────────────────────────────────────────────────────────


def test_harvest_returns_none_when_playwright_is_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If Playwright cannot be imported, the helper is a no-op."""
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    monkeypatch.setattr(_browser_warmup, "_import_playwright", lambda: None)
    assert _browser_warmup.harvest_cookies_with_browser("https://example.com") is None


def test_sensor_dwell_constant_is_long_enough_for_akamai_sensor() -> None:
    """Akamai's sensor JS needs at least 1.5s of telemetry to stamp ``_abck``.

    Anything below 1500ms lets the WAF reject the WAF-token as stale on the
    next request. The constant must stay >= 1500.
    """
    assert _browser_warmup._SENSOR_DWELL_MS >= 1500


def test_harvest_returns_none_when_chromium_launch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If Playwright is importable but the Chromium binary is missing, soft-fail.

    Simulates ``p.chromium.launch(...)`` raising an exception (the typical
    "Executable doesn't exist" error when ``playwright install chromium``
    hasn't been run).
    """
    fake_pw = SimpleNamespace(
        chromium=SimpleNamespace(
            launch=lambda headless: (_ for _ in ()).throw(
                RuntimeError("Executable doesn't exist")
            )
        )
    )

    class _FakeCM:
        def __enter__(self) -> Any:
            return fake_pw

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    module = ModuleType("playwright.sync_api")
    module.sync_playwright = lambda: _FakeCM()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", module)

    assert _browser_warmup.harvest_cookies_with_browser("https://example.com") is None


# ─────────────────────────────────────────────────────────────────────────
# merge_cookies_into_session: builds domain-aware stdlib ``Cookie`` objects
# so curl_cffi's stdlib jar keeps each cookie under the Playwright-reported
# domain. RFC 6265 strict-matching then actually sends them on later requests.
# ─────────────────────────────────────────────────────────────────────────


def test_merge_cookies_into_session_sets_stdlib_cookies_with_domain() -> None:
    """Each HarvestedCookie becomes a stdlib http.cookiejar.Cookie with the
    supplied domain + path. The jar correctly rejects empty-domain entries
    in production; this test confirms we don't fall back to that bad shape.
    """
    seen: list[Cookie] = []

    class _Jar:
        def set_cookie(self, cookie: Cookie) -> None:
            seen.append(cookie)

    class _Session:
        cookies = _Jar()

    cookies = [
        HarvestedCookie(name="datadome", value="abc", domain=".easyjet.com", path="/", secure=False),
        HarvestedCookie(name="_abck", value="xyz", domain=".iberia.com", path="/", secure=False),
    ]
    _browser_warmup.merge_cookies_into_session(_Session(), cookies)

    by_name = {c.name: c for c in seen}
    assert by_name["datadome"].domain == ".easyjet.com"
    assert by_name["datadome"].domain_initial_dot is True
    assert by_name["_abck"].domain == ".iberia.com"
    assert by_name["_abck"].domain_initial_dot is True


def test_merge_cookies_into_session_uses_requests_set_shortcut_when_available() -> None:
    """``requests.cookies.RequestsCookieJar.set(name, value)`` is still hit
    first; only on failed shortcut do we fall through to Cookie+set_cookie.
    """
    seen: dict[str, str] = {}

    class _Jar:
        def set(self, name: str, value: str) -> None:  # noqa: D401 - shortcut
            seen[name] = value

    class _Session:
        cookies = _Jar()

    cookies = [
        HarvestedCookie(name="datadome", value="abc", domain=".easyjet.com", path="/"),
    ]
    _browser_warmup.merge_cookies_into_session(_Session(), cookies)
    assert seen == {"datadome": "abc"}


def test_merge_cookies_into_session_handles_none_and_empty_inputs() -> None:
    """No-op resilience: None or empty list does nothing."""

    class _SessionNoJar:
        pass

    _browser_warmup.merge_cookies_into_session(_SessionNoJar(), None)
    _browser_warmup.merge_cookies_into_session(_SessionNoJar(), [])


def test_merge_cookies_into_session_swallows_jar_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A jar that throws is logged at DEBUG and does not crash the helper."""

    class _BrokenJar:
        def set(self, name: str, value: str) -> None:
            raise RuntimeError("jar cannot be written right now")

    class _Session:
        cookies = _BrokenJar()

    caplog.set_level("DEBUG", logger="app.infrastructure.providers._browser_warmup")
    _browser_warmup.merge_cookies_into_session(
        _Session(),
        [HarvestedCookie(name="x", value="y", domain="example.com", path="/")],
    )  # no raise


def test_merge_cookies_from_mapping_is_a_test_only_back_compat_helper() -> None:
    """The mapping shim exists for tests that don't need full domain info.

    It must coexist with the slow path so test fixtures and the production
    path don't fight over which one is canonical.
    """
    seen: dict[str, str] = {}

    class _Jar:
        def set(self, name: str, value: str) -> None:
            seen[name] = value

    _browser_warmup.merge_cookies_from_mapping(SimpleNamespace(cookies=_Jar()), {"a": "1", "b": "2"})
    assert seen == {"a": "1", "b": "2"}


# ─────────────────────────────────────────────────────────────────────────
# Iberia + easyJet env-gate: opt-in cookie harvest is exercised only when
# the env var is set. Idempotent marker prevents respawning Playwright per
# request.
# ─────────────────────────────────────────────────────────────────────────


def test_iberia_provider_skips_browser_warmup_when_env_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Iberia env gate keeps Playwright import on the cold path."""
    monkeypatch.delenv("IBERIA_USE_BROWSER_WARMUP", raising=False)

    from app.infrastructure.providers.iberia_provider import IberiaProvider

    calls: list[tuple[str, str]] = []

    def fake_harvest(
        url: str, *, referer_path: str = "", timeout_ms: int = 15000
    ) -> list[HarvestedCookie] | None:
        calls.append((url, referer_path))
        return None

    monkeypatch.setattr(
        "app.infrastructure.providers._browser_warmup.harvest_cookies_with_browser",
        fake_harvest,
    )

    provider = IberiaProvider(
        api_base_url="https://api.example.test",
        base_url="https://www.iberia.example.test",
        authorization="Basic t",
        market="ES",
        language="es",
    )
    provider._warmed = True  # skip curl warmup; focus on browser warmup opt-in

    # Without the env flag, the browser path is not invoked.
    provider._browser_warmup("https://www.iberia.example.test", referer_path="/")
    assert calls == []


def test_iberia_provider_invokes_browser_warmup_when_env_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IBERIA_USE_BROWSER_WARMUP", "1")

    from app.infrastructure.providers.iberia_provider import IberiaProvider

    calls: list[tuple[str, str]] = []
    harvested = [
        HarvestedCookie(name="_abck", value="fresh-token", domain=".iberia.com", path="/"),
    ]

    def fake_harvest(
        url: str, *, referer_path: str = "", timeout_ms: int = 15000
    ) -> list[HarvestedCookie] | None:
        calls.append((url, referer_path))
        return harvested

    monkeypatch.setattr(
        "app.infrastructure.providers._browser_warmup.harvest_cookies_with_browser",
        fake_harvest,
    )
    monkeypatch.setattr(
        "app.infrastructure.providers._browser_warmup.merge_cookies_into_session",
        lambda session, cookies: None,
    )

    provider = IberiaProvider(
        api_base_url="https://api.example.test",
        base_url="https://www.iberia.example.test",
        authorization="Basic t",
        market="ES",
        language="es",
    )
    provider._warmed = True
    provider._browser_warmup("https://www.iberia.example.test", referer_path="/")
    assert calls == [("https://www.iberia.example.test", "/")]


def test_easyjet_provider_skips_browser_warmup_when_env_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EASYJET_USE_BROWSER_WARMUP", raising=False)

    from app.infrastructure.providers.easyjet_provider import EasyJetProvider

    calls: list[tuple[str, str]] = []

    def fake_harvest(
        url: str, *, referer_path: str = "", timeout_ms: int = 15000
    ) -> list[HarvestedCookie] | None:
        calls.append((url, referer_path))
        return None

    monkeypatch.setattr(
        "app.infrastructure.providers._browser_warmup.harvest_cookies_with_browser",
        fake_harvest,
    )

    provider = EasyJetProvider()
    provider._warmed_marketing = True
    provider._warmed_flightconnections = True
    provider._browser_warmup("https://www.easyjet.com", referer_path="/en/", kind="marketing")
    assert calls == []


def test_easyjet_provider_invokes_browser_warmup_when_env_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EASYJET_USE_BROWSER_WARMUP", "1")

    from app.infrastructure.providers.easyjet_provider import EasyJetProvider

    recorded: dict[str, object] = {}

    def fake_harvest(
        url: str, *, referer_path: str = "", timeout_ms: int = 15000
    ) -> list[HarvestedCookie] | None:
        recorded["url"] = url
        recorded["referer_path"] = referer_path
        return [HarvestedCookie(name="datadome", value="fresh", domain=".easyjet.com", path="/")]

    monkeypatch.setattr(
        "app.infrastructure.providers._browser_warmup.harvest_cookies_with_browser",
        fake_harvest,
    )
    monkeypatch.setattr(
        "app.infrastructure.providers._browser_warmup.merge_cookies_into_session",
        lambda session, cookies: recorded.setdefault("merged", [c.name for c in cookies or []]),
    )

    provider = EasyJetProvider()
    provider._warmed_marketing = True
    provider._browser_warmup("https://www.easyjet.com", referer_path="/en/", kind="marketing")
    assert recorded["url"] == "https://www.easyjet.com"
    assert recorded["referer_path"] == "/en/"
    assert recorded["merged"] == ["datadome"]


# ─────────────────────────────────────────────────────────────────────────
# request_via_browser (Playwright-direct POST/GET helper): the last code-side
# lever against Akamai bot-manager once cookies + curl_cffi fingerprinting
# aren't enough. Returns None on any failure so the curl_cffi fallback wins.
# ─────────────────────────────────────────────────────────────────────────


def test_browser_response_text_and_json_properties() -> None:
    from app.infrastructure.providers._browser_warmup import BrowserResponse

    br = BrowserResponse(status_code=200, body_text='{"flights": []}')
    assert br.status_code == 200
    assert br.text == '{"flights": []}'
    assert br.ok is True
    assert br.json() == {"flights": []}

    br_403 = BrowserResponse(status_code=403, body_text="")
    assert br_403.ok is False


def test_request_via_browser_returns_browser_response_when_chromium_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.infrastructure.providers import _browser_warmup

    class _FakeResponse:
        status = 200

        def text(self) -> str:
            return '{"flights": []}'

    class _FakeRequest:
        def fetch(self, *args: Any, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse()

    class _FakeContext:
        request = _FakeRequest()

        def set_default_timeout(self, ms: int) -> None:
            return None

    class _FakeBrowser:
        def new_context(self, **kwargs: Any) -> _FakeContext:
            return _FakeContext()

        def close(self) -> None:
            pass

    class _FakePW:
        chromium = SimpleNamespace(launch=lambda headless=True: _FakeBrowser())

    class _FakeCM:
        def __enter__(self) -> _FakePW:
            return _FakePW()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    module = ModuleType("playwright.sync_api")
    module.sync_playwright = lambda: _FakeCM()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", module)

    br = _browser_warmup.request_via_browser(
        "POST", "https://example.com", json_body={"a": 1}
    )
    assert br is not None
    assert br.status_code == 200
    assert br.json() == {"flights": []}


def test_request_via_browser_returns_none_when_chromium_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.infrastructure.providers import _browser_warmup

    class _FakePW:
        chromium = SimpleNamespace(
            launch=lambda headless=True: (_ for _ in ()).throw(
                RuntimeError("Executable doesn't exist")
            )
        )

    class _FakeCM:
        def __enter__(self) -> _FakePW:
            return _FakePW()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    module = ModuleType("playwright.sync_api")
    module.sync_playwright = lambda: _FakeCM()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", module)

    assert _browser_warmup.request_via_browser("POST", "https://example.com") is None


def test_request_via_browser_returns_none_when_playwright_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.infrastructure.providers import _browser_warmup

    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    monkeypatch.setattr(_browser_warmup, "_import_playwright", lambda: None)

    assert _browser_warmup.request_via_browser("POST", "https://example.com") is None


def test_request_via_browser_warmup_nav_shares_context_with_api_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Warmup navigation and the API request MUST share the same browser
    context so the ``_abck`` cookie set during the sensor JS phase gets
    actually attached to the subsequent ``request.fetch`` (different
    contexts = different cookie jars = cold POST = Akamai 403).
    """
    from app.infrastructure.providers import _browser_warmup

    class _FakeResponse:
        status = 200

        def text(self) -> str:
            return '{"ok": true}'

    nav_log: list[str] = []
    api_log: list[tuple[str, dict[str, str]]] = []

    class _FakeRequest:
        def fetch(self, url: str, **kwargs: Any) -> _FakeResponse:
            api_log.append((url, dict(kwargs.get("headers") or {})))
            return _FakeResponse()

    class _FakePage:
        def goto(self, url: str, **kwargs: Any) -> None:
            nav_log.append(url)

        def wait_for_timeout(self, ms: int) -> None:
            nav_log.append(f"dwell:{ms}")

    class _FakeContext:
        request = _FakeRequest()

        def set_default_timeout(self, ms: int) -> None:
            return None

        def new_page(self) -> _FakePage:
            return _FakePage()

        def set_default_timeout(self, ms: int) -> None:
            nav_log.append(f"timeout:{ms}")

    class _FakeBrowser:
        contexts: list[_FakeContext] = []

        def new_context(self, **kwargs: Any) -> _FakeContext:
            ctx = _FakeContext()
            self.contexts.append(ctx)
            return ctx

        def close(self) -> None:
            pass

    class _FakePW:
        chromium = SimpleNamespace(launch=lambda headless=True: _FakeBrowser())

    class _FakeCM:
        def __enter__(self) -> _FakePW:
            return _FakePW()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    bw = _browser_warmup
    monkeypatch.setattr(bw, "_import_playwright", lambda: lambda: _FakeCM())
    monkeypatch.setattr(bw, "_SENSOR_DWELL_MS", 100)  # tiny dwell to keep test fast

    br = bw.request_via_browser(
        "POST",
        "https://api.example.test/availability",
        json_body={"o": "MAD", "d": "JFK"},
        warmup_url="https://www.example.test",
        warmup_referer_path="/",
    )
    assert br is not None
    assert br.status_code == 200
    # Warmup nav happened BEFORE the API fetch (and on the only context).
    assert nav_log[:3] == [
        "timeout:15000",
        "https://www.example.test/",
        "dwell:100",
    ]
    assert api_log == [("https://api.example.test/availability", {})]


def test_request_via_browser_warmup_nav_failure_does_not_abort_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the warmup navigation times out or the page goto fails, the POST
    still goes through. A failed warmup is a soft warning; the API request
    is independent and may still succeed if Akamai's bot-manager is in a
    lenient mood or if the analyzer can infer the cookie from prior calls.
    Returns ``None`` is also acceptable; the failure to fetch is reported by
    the provider via the standard curl_cffi fallback.
    """
    from app.infrastructure.providers import _browser_warmup

    class _FakeResponse:
        status = 200

        def text(self) -> str:
            return "{}"

    class _FakeRequest:
        def fetch(self, url: str, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse()

    class _FakePage:
        def goto(self, url: str, **kwargs: Any) -> None:
            raise RuntimeError("net::ERR_TIMED_OUT")

        def wait_for_timeout(self, ms: int) -> None:
            pass

    class _FakeContext:
        request = _FakeRequest()

        def set_default_timeout(self, ms: int) -> None:
            return None

        def new_page(self) -> _FakePage:
            return _FakePage()

        def set_default_timeout(self, ms: int) -> None:
            pass

    class _FakeBrowser:
        def new_context(self, **kwargs: Any) -> _FakeContext:
            return _FakeContext()

        def close(self) -> None:
            pass

    class _FakePW:
        chromium = SimpleNamespace(launch=lambda headless=True: _FakeBrowser())

    class _FakeCM:
        def __enter__(self) -> _FakePW:
            return _FakePW()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    bw = _browser_warmup
    monkeypatch.setattr(bw, "_import_playwright", lambda: lambda: _FakeCM())
    monkeypatch.setattr(bw, "_SENSOR_DWELL_MS", 1)

    br = bw.request_via_browser(
        "POST",
        "https://api.example.test/availability",
        warmup_url="https://www.example.test",
    )
    assert br is not None
    assert br.status_code == 200
