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
