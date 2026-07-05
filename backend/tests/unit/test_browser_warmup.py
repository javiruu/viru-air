"""Direct tests for the optional browser warmup helper.

The helper is allowed to fail soft when Playwright (or its Chromium binary)
is missing; production code must never crash because Playwright cannot be
imported. These tests pin that contract via simple monkeypatching of
``sys.modules`` so no real Chromium is required.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
import typing

import pytest

from app.infrastructure.providers import _browser_warmup


def test_harvest_returns_none_when_playwright_is_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If Playwright cannot be imported, the helper is a no-op."""
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    monkeypatch.setattr(_browser_warmup, "_import_playwright", lambda: None)
    assert _browser_warmup.harvest_cookies_with_browser("https://example.com") is None


def test_merge_cookies_into_session_sets_jar_entries() -> None:
    """Every cookie in the mapping is written into the session cookie jar."""
    jar: dict[str, str] = {}

    class _Jar:
        def set(self, name: str, value: str) -> None:
            jar[name] = value

    class _Session:
        cookies = _Jar()

    _browser_warmup.merge_cookies_into_session(_Session(), {"datadome": "abc", "_abck": "xyz"})
    assert jar == {"datadome": "abc", "_abck": "xyz"}


def test_merge_cookies_into_session_handles_none_and_missing_jar() -> None:
    """No-op resilience: missing/None maps and sessions without a jar."""

    class _SessionNoJar:
        pass

    _browser_warmup.merge_cookies_into_session(_SessionNoJar(), None)
    _browser_warmup.merge_cookies_into_session(_SessionNoJar(), {})
    _browser_warmup.merge_cookies_into_session(_SessionNoJar(), {"x": "y"})


def test_merge_cookies_into_session_swallows_jar_errors(caplog: pytest.LogCaptureFixture) -> None:
    """A jar that throws is logged at DEBUG and does not crash the helper."""

    class _BrokenJar:
        def set(self, name: str, value: str) -> None:
            raise RuntimeError("jar cannot be written right now")

    class _Session:
        cookies = _BrokenJar()

    caplog.set_level("DEBUG", logger="app.infrastructure.providers._browser_warmup")
    _browser_warmup.merge_cookies_into_session(_Session(), {"x": "y"})  # no raise


def test_iberia_provider_skips_browser_warmup_when_env_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Iberia env gate keeps Playwright import on the cold path."""
    monkeypatch.delenv("IBERIA_USE_BROWSER_WARMUP", raising=False)

    from app.infrastructure.providers.iberia_provider import IberiaProvider

    calls: list[tuple[str, str]] = []

    def fake_harvest(url: str, *, referer_path: str = "", timeout_ms: int = 15000):
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

    def fake_harvest(url: str, *, referer_path: str = "", timeout_ms: int = 15000):
        calls.append((url, referer_path))
        return {"_abck": "fresh-token"}

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

    def fake_harvest(url: str, *, referer_path: str = "", timeout_ms: int = 15000):
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

    def fake_harvest(url: str, *, referer_path: str = "", timeout_ms: int = 15000):
        recorded["url"] = url
        recorded["referer_path"] = referer_path
        return {"datadome": "fresh"}

    monkeypatch.setattr(
        "app.infrastructure.providers._browser_warmup.harvest_cookies_with_browser",
        fake_harvest,
    )
    monkeypatch.setattr(
        "app.infrastructure.providers._browser_warmup.merge_cookies_into_session",
        lambda session, cookies: recorded.setdefault("merged", list(cookies or {})),
    )

    provider = EasyJetProvider()
    provider._warmed_marketing = True
    provider._browser_warmup("https://www.easyjet.com", referer_path="/en/", kind="marketing")
    assert recorded["url"] == "https://www.easyjet.com"
    assert recorded["referer_path"] == "/en/"
    assert recorded["merged"] == ["datadome"]


def test_harvest_returns_none_when_chromium_launch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If Playwright is importable but the Chromium binary is missing, soft-fail.

    Simulates `p.chromium.launch(...)` raising an exception (the typical
    "Executable doesn't exist" error when `playwright install chromium`
    hasn't been run).
    """
    fake_pw = SimpleNamespace(
        chromium=SimpleNamespace(
            launch=lambda headless: (_ for _ in ()).throw(
                RuntimeError("Executable doesn't exist")
            )
        )
    )
    fake_sync = lambda: (_ for _ in ()).throw(RuntimeError("not used"))  # noqa: ARG005 - sig
    # We need sync_playwright() to return a context manager whose __enter__
    # yields the fake_pw object.
    class _FakeCM:
        def __enter__(self): return fake_pw
        def __exit__(self, exc_type, exc, tb): return False
    fake_sync = lambda: _FakeCM()

    module = ModuleType("playwright.sync_api")
    module.sync_playwright = fake_sync  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", module)

    assert _browser_warmup.harvest_cookies_with_browser("https://example.com") is None
