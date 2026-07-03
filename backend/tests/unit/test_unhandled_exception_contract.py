import logging

import pytest
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import ApiError
from app.core.request_diagnostics import sanitize_request_body
from app.main import app
import app.main as main_module


class _SensitivePayload(BaseModel):
    name: str
    password: str


def test_health_returns_ok_with_correlation_header(client: TestClient) -> None:
    response = client.get("/health", headers={"x-correlation-id": "corr-health-1"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-correlation-id"] == "corr-health-1"


def test_cors_preflight_allows_localhost_origin(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "origin": "http://localhost:3000",
            "access-control-request-method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_http_exception_string_detail_returns_error_envelope(client: TestClient) -> None:
    router = APIRouter()

    @router.get("/_test/http-string")
    def http_string() -> dict[str, str]:
        raise HTTPException(status_code=404, detail="watch_not_found")

    app.include_router(router)

    try:
        response = client.get("/_test/http-string", headers={"x-correlation-id": "corr-http-string"})

        assert response.status_code == 404
        assert response.json() == {
            "status": 404,
            "code": "watch_not_found",
            "message": "Watch not found.",
            "details": [],
            "correlation_id": "corr-http-string",
        }
    finally:
        app.router.routes.pop()


def test_http_exception_dict_detail_returns_error_envelope(client: TestClient) -> None:
    router = APIRouter()

    @router.get("/_test/http-dict")
    def http_dict() -> dict[str, str]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "route_conflict",
                "message": "Route conflict.",
                "details": {"route": "AGP-DUB"},
            },
        )

    app.include_router(router)

    try:
        response = client.get("/_test/http-dict", headers={"x-correlation-id": "corr-http-dict"})

        assert response.status_code == 409
        assert response.json() == {
            "status": 409,
            "code": "route_conflict",
            "message": "Route conflict.",
            "details": {"route": "AGP-DUB"},
            "correlation_id": "corr-http-dict",
        }
    finally:
        app.router.routes.pop()


def test_api_error_returns_retryable_error_envelope(client: TestClient) -> None:
    router = APIRouter()

    @router.get("/_test/api-error")
    def api_error() -> dict[str, str]:
        raise ApiError(
            status=429,
            code="rate_limited",
            message="Too many requests.",
            details=[{"scope": "quick_search"}],
            retry_after_sec=30,
        )

    app.include_router(router)

    try:
        response = client.get("/_test/api-error", headers={"x-correlation-id": "corr-api-error"})

        assert response.status_code == 429
        assert response.json() == {
            "status": 429,
            "code": "rate_limited",
            "message": "Too many requests.",
            "details": [{"scope": "quick_search"}],
            "correlation_id": "corr-api-error",
            "retry_after_sec": 30,
        }
    finally:
        app.router.routes.pop()


def test_validation_error_redacts_sensitive_body_in_logs(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    router = APIRouter()

    @router.post("/_test/validation-redaction")
    def validation_redaction(payload: _SensitivePayload) -> dict[str, str]:
        return {"name": payload.name}

    app.include_router(router)

    try:
        with caplog.at_level(logging.ERROR, logger="app.access"):
            response = client.post(
                "/_test/validation-redaction",
                json={"password": "plain-secret"},
                headers={"x-correlation-id": "corr-validation"},
            )

        assert response.status_code == 422
        payload = response.json()
        assert payload["code"] == "validation_error"
        assert payload["correlation_id"] == "corr-validation"
        assert "plain-secret" not in str(payload)
        assert "plain-secret" not in caplog.text
        assert '"password": "***"' in caplog.text
    finally:
        app.router.routes.pop()


def test_unhandled_exception_returns_json_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    router = APIRouter()

    @router.get("/_test/unhandled-boom")
    def unhandled_boom() -> dict[str, str]:
        raise RuntimeError("boom")

    app.include_router(router)
    monkeypatch.setattr(main_module, "WATCHLIST_STARTUP_REFRESH_ENABLED", False)
    monkeypatch.setattr(main_module, "FARE_MEMORY_BOOT_WARMUP_ENABLED", False)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/_test/unhandled-boom", headers={"x-correlation-id": "corr-test-1234"})

        assert response.status_code == 500
        assert response.json() == {
            "status": 500,
            "code": "internal_server_error",
            "message": "Internal server error.",
            "details": [],
            "correlation_id": "corr-test-1234",
        }
        assert response.headers["x-correlation-id"] == "corr-test-1234"
    finally:
        app.router.routes.pop()


def test_request_body_sanitizer_redacts_nested_sensitive_fields() -> None:
    sanitized = sanitize_request_body(
        {
            "email": "user@viru.local",
            "password": "plain",
            "profile": {
                "api_key": "key",
                "nestedToken": "token",
                "display_name": "Viru",
            },
            "headers": [{"authorization": "Bearer secret"}],
        }
    )

    assert sanitized == {
        "email": "user@viru.local",
        "password": "***",
        "profile": {
            "api_key": "***",
            "nestedToken": "***",
            "display_name": "Viru",
        },
        "headers": [{"authorization": "***"}],
    }
