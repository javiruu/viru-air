from __future__ import annotations

import json
import logging
import time

from fastapi import Request
from starlette.requests import ClientDisconnect
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.request_context import get_correlation_id

type JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]

_SENSITIVE_BODY_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
)


def sanitize_request_body(body: JsonValue) -> JsonValue:
    if isinstance(body, dict):
        sanitized: dict[str, JsonValue] = {}
        for key, value in body.items():
            key_lower = key.lower()
            if any(part in key_lower for part in _SENSITIVE_BODY_KEY_PARTS):
                sanitized[key] = "***"
            else:
                sanitized[key] = sanitize_request_body(value)
        return sanitized
    if isinstance(body, list):
        return [sanitize_request_body(item) for item in body]
    return body


async def safe_request_body(request: Request) -> JsonValue:
    try:
        body = await request.body()
    except (ClientDisconnect, RuntimeError):
        return None
    if not body:
        return None
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body.decode("utf-8", errors="replace")[:2000]
    return sanitize_request_body(parsed)


def scope_headers(scope: Scope) -> dict[str, str]:
    headers: dict[str, str] = {}
    for raw_key, raw_value in scope.get("headers", []):
        if not isinstance(raw_key, bytes) or not isinstance(raw_value, bytes):
            continue
        key = raw_key.decode("latin-1").lower()
        value = raw_value.decode("latin-1")
        headers[key] = value
    return headers


class AccessLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger("app.access")
        self.app_logger = logging.getLogger("app.main")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = None

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            try:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                headers = scope_headers(scope)
                log_payload = {
                    "event": "http",
                    "correlation_id": get_correlation_id() or headers.get("x-correlation-id") or "-",
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status_code or 500,
                    "elapsed_ms": elapsed_ms,
                    "client": scope.get("client")[0] if scope.get("client") else None,
                    "origin": headers.get("origin"),
                    "referer": headers.get("referer"),
                    "user_agent": headers.get("user-agent"),
                    "content_type": headers.get("content-type"),
                    "ac_request_method": headers.get("access-control-request-method"),
                    "ac_request_headers": headers.get("access-control-request-headers"),
                }
                self.logger.info(json.dumps(log_payload, ensure_ascii=False))
            except (KeyError, TypeError, ValueError):
                self.app_logger.exception("access_log_emit_failed")
