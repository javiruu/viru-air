
from fastapi.testclient import TestClient
from tests.helpers import register_and_token


def test_decommissioned_legacy_endpoints(client: TestClient) -> None:
    # Registration is managed by Supabase Auth
    resp = client.post("/api/v1/auth/register", json={"email": "qa@viru.dev", "password": "password123"})
    assert resp.status_code == 410
    assert resp.json()["code"] == "auth_managed_by_supabase"

    # Login is managed by Supabase Auth
    resp = client.post("/api/v1/auth/login", json={"email": "qa@viru.dev", "password": "password123"})
    assert resp.status_code == 410
    assert resp.json()["code"] == "auth_managed_by_supabase"

    # Refresh is managed by Supabase Auth
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "legacy-token"})
    assert resp.status_code == 410
    assert resp.json()["code"] == "auth_managed_by_supabase"

    # Forgot password is managed by Supabase Auth
    resp = client.post("/api/v1/auth/forgot-password", json={"email": "qa@viru.dev"})
    assert resp.status_code == 410
    assert resp.json()["code"] == "auth_managed_by_supabase"

    # Reset password is managed by Supabase Auth
    resp = client.post("/api/v1/auth/reset-password", json={"token": "1234567890123456", "new_password": "Password123"})
    assert resp.status_code == 410
    assert resp.json()["code"] == "auth_managed_by_supabase"


def test_me_without_token_returns_standardized_auth_error(client: TestClient) -> None:
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401
    assert me.json()["code"] == "invalid_auth"
    assert me.json()["status"] == 401


def test_me_with_supabase_token(client: TestClient) -> None:
    token = register_and_token(client, email="qa-supabase@viru.dev")
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "qa-supabase@viru.dev"


def test_logout(client: TestClient) -> None:
    token = register_and_token(client, email="logout-supabase@viru.dev")
    resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
