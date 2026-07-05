from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import logging
import os
from typing import Any, Final

from app.infrastructure.providers._browser_cookies import (
    HarvestedCookie,
    merge_cookies_from_mapping,
    merge_cookies_into_session,
)

logger = logging.getLogger(__name__)

__all__ = (
    "BrowserResponse",
    "HarvestedCookie",
    "browser_warmup_enabled",
    "harvest_cookies_with_browser",
    "merge_cookies_from_mapping",
    "merge_cookies_into_session",
    "request_via_browser",
    "request_via_browser_when_enabled",
    "warm_session_with_browser",
)

_ENABLED_FLAG_VALUES: Final[frozenset[str]] = frozenset({"1", "true", "yes", "on"})


def browser_warmup_enabled(env_var: str) -> bool:
    return os.getenv(env_var, "").strip().lower() in _ENABLED_FLAG_VALUES

def _import_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError:
        logger.info("playwright not installed; browser warmup is a no-op")
        return None
    return sync_playwright


_SENSOR_DWELL_MS: int = 2500


def harvest_cookies_with_browser(
    target_url: str,
    *,
    referer_path: str = "",
    timeout_ms: int = 15000,
) -> list[HarvestedCookie] | None:
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


def warm_session_with_browser(
    session: Any,
    *,
    env_var: str,
    base_url: str,
    referer_path: str = "",
) -> bool:
    if not browser_warmup_enabled(env_var):
        return False
    cookies = harvest_cookies_with_browser(base_url, referer_path=referer_path)
    merge_cookies_into_session(session, cookies)
    return True


def request_via_browser_when_enabled(
    env_var: str,
    method: str,
    url: str,
    *,
    json_body: Mapping[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout_ms: int = 15000,
    warmup_url: str | None = None,
    warmup_referer_path: str = "",
) -> BrowserResponse | None:
    if not browser_warmup_enabled(env_var):
        return None
    return request_via_browser(
        method,
        url,
        json_body=json_body,
        headers=headers,
        timeout_ms=timeout_ms,
        warmup_url=warmup_url,
        warmup_referer_path=warmup_referer_path,
    )
