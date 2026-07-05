from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


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
    monkeypatch.setattr(bw, "_SENSOR_DWELL_MS", 100)

    br = bw.request_via_browser(
        "POST",
        "https://api.example.test/availability",
        json_body={"o": "MAD", "d": "JFK"},
        warmup_url="https://www.example.test",
        warmup_referer_path="/",
    )
    assert br is not None
    assert br.status_code == 200
    assert nav_log[:3] == [
        "timeout:15000",
        "https://www.example.test/",
        "dwell:100",
    ]
    assert api_log == [("https://api.example.test/availability", {})]


def test_request_via_browser_warmup_nav_failure_does_not_abort_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
