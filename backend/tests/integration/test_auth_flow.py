from fastapi.testclient import TestClient

from tests.helpers import register_and_token


def test_register_login_and_me(client: TestClient) -> None:
    token = register_and_token(client)
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
