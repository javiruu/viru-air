from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_api
from tests.helpers import register_and_token


def test_register_login_and_me(client: TestClient) -> None:
    register = client.post("/api/v1/auth/register", json={"email": "qa@viru.dev", "password": "password123"})
    assert register.status_code == 200
    assert "access_token" in register.json()
    token = register.json()["access_token"]

    login = client.post("/api/v1/auth/login", json={"email": "qa@viru.dev", "password": "password123"})
    assert login.status_code == 200
    assert "access_token" in login.json()
    assert "refresh_token" in login.json()

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "qa@viru.dev"


def test_me_without_token_returns_standardized_auth_error(client: TestClient) -> None:
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401
    assert me.json()["code"] == "invalid_auth"
    assert me.json()["status"] == 401


def test_login_with_invalid_credentials_returns_standardized_auth_error(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "qa@viru.dev", "password": "Pass1234"})
    login = client.post("/api/v1/auth/login", json={"email": "qa@viru.dev", "password": "wrong-pass"})
    assert login.status_code == 401
    assert login.json()["code"] == "invalid_auth"
    assert login.json()["status"] == 401


def test_register_duplicate_returns_409(client: TestClient) -> None:
    payload = {"email": "dup@viru.dev", "password": "Pass1234"}
    first = client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["code"] == "email_exists"


def test_refresh_rotates_token_and_revokes_previous(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "refresh@viru.dev", "password": "Pass1234"})
    login = client.post("/api/v1/auth/login", json={"email": "refresh@viru.dev", "password": "Pass1234"})
    refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != refresh_token
    assert "access_token" in refreshed.json()

    old_refresh_reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert old_refresh_reuse.status_code == 401
    assert old_refresh_reuse.json()["code"] == "invalid_auth"


def test_refresh_with_expired_token_fails(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(auth_api, "REFRESH_TOKEN_DAYS", 0)
    client.post("/api/v1/auth/register", json={"email": "expired@viru.dev", "password": "Pass1234"})
    login = client.post("/api/v1/auth/login", json={"email": "expired@viru.dev", "password": "Pass1234"})
    refresh_token = login.json()["refresh_token"]
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 401
    assert refreshed.json()["code"] == "invalid_auth"


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    access_token = register_and_token(client, email="logout@viru.dev", password="Pass1234")
    login = client.post("/api/v1/auth/login", json={"email": "logout@viru.dev", "password": "Pass1234"})
    refresh_token = login.json()["refresh_token"]

    logout = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout.status_code == 200

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 401
    assert refreshed.json()["code"] == "invalid_auth"


def test_forgot_password_returns_generic_message_for_existing_and_missing_email(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "exists@viru.dev", "password": "Pass1234"})
    existing = client.post("/api/v1/auth/forgot-password", json={"email": "exists@viru.dev"})
    missing = client.post("/api/v1/auth/forgot-password", json={"email": "missing@viru.dev"})
    assert existing.status_code == 200
    assert missing.status_code == 200
    assert existing.json() == {"message": "Si el correo existe, te enviaremos instrucciones."}
    assert missing.json() == {"message": "Si el correo existe, te enviaremos instrucciones."}


def test_reset_password_changes_password_and_revokes_refresh_tokens(client: TestClient, monkeypatch) -> None:
    reset_token = "fixed-reset-token-value"
    monkeypatch.setattr(auth_api, "create_reset_token", lambda: reset_token)
    client.post("/api/v1/auth/register", json={"email": "reset@viru.dev", "password": "Pass1234"})
    login = client.post("/api/v1/auth/login", json={"email": "reset@viru.dev", "password": "Pass1234"})
    refresh_token = login.json()["refresh_token"]

    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "reset@viru.dev"})
    assert forgot.status_code == 200

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "Pass5678"},
    )
    assert reset.status_code == 200

    old_password_login = client.post("/api/v1/auth/login", json={"email": "reset@viru.dev", "password": "Pass1234"})
    assert old_password_login.status_code == 401
    assert old_password_login.json()["code"] == "invalid_auth"

    new_password_login = client.post("/api/v1/auth/login", json={"email": "reset@viru.dev", "password": "Pass5678"})
    assert new_password_login.status_code == 200
    assert "refresh_token" in new_password_login.json()

    refresh_after_reset = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_after_reset.status_code == 401
    assert refresh_after_reset.json()["code"] == "invalid_auth"


def test_reset_password_token_cannot_be_reused(client: TestClient, monkeypatch) -> None:
    reset_token = "one-use-reset-token"
    monkeypatch.setattr(auth_api, "create_reset_token", lambda: reset_token)
    client.post("/api/v1/auth/register", json={"email": "reuse@viru.dev", "password": "Pass1234"})
    client.post("/api/v1/auth/forgot-password", json={"email": "reuse@viru.dev"})

    first = client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": "Pass5678"})
    second = client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": "Pass9999"})
    assert first.status_code == 200
    assert second.status_code == 401
    assert second.json()["code"] == "invalid_auth"


def test_reset_password_with_expired_token_fails(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(auth_api, "RESET_TOKEN_MINUTES", -1)
    reset_token = "expired-reset-token"
    monkeypatch.setattr(auth_api, "create_reset_token", lambda: reset_token)
    client.post("/api/v1/auth/register", json={"email": "expired-reset@viru.dev", "password": "Pass1234"})
    client.post("/api/v1/auth/forgot-password", json={"email": "expired-reset@viru.dev"})
    reset = client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": "Pass5678"})
    assert reset.status_code == 401
    assert reset.json()["code"] == "invalid_auth"
