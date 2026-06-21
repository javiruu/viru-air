from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.main import app


def test_unhandled_exception_returns_json_envelope() -> None:
    router = APIRouter()

    @router.get("/_test/unhandled-boom")
    def unhandled_boom() -> dict[str, str]:
        raise RuntimeError("boom")

    app.include_router(router)

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
