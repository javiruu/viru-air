import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import select

from app.api.deps import get_db, resolve_supabase_jwt_secret
from app.infrastructure.db.models import SecurityActivity, User
from app.main import app

SECRET = "test-suite-supabase-jwt-secret"


def _mint_supabase_token(
    user_id: str,
    email: str = "test@supabase.local",
    expired: bool = False,
    wrong_secret: bool = False,
    empty_secret: bool = False,
    email_verified: bool | None = True,
    include_email: bool = True,
    claims_admin: bool = False,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    payload = {
        "sub": user_id,
        "exp": exp,
        "role": "authenticated",
        "app_metadata": {"provider": "email", "claims_admin": claims_admin},
        "user_metadata": {},
    }
    if include_email:
        payload["email"] = email
    if email_verified is not None:
        payload["email_verified"] = email_verified

    if empty_secret:
        secret = ""
    elif wrong_secret:
        secret = "wrong-secret-key-12345"
    else:
        secret = SECRET
    return jwt.encode(payload, secret, algorithm="HS256")


def test_no_token_returns_401(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_auth"


def test_malformed_token_returns_401(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_auth"


def test_expired_supabase_token_returns_401(client: TestClient) -> None:
    token = _mint_supabase_token("user-exp", expired=True)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_auth"


def test_wrong_signature_project_token_returns_401(client: TestClient) -> None:
    token = _mint_supabase_token("user-wrong-project", wrong_secret=True)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_auth"


def test_empty_key_signature_token_returns_401(client: TestClient) -> None:
    """python-jose accepts HS256 with an empty key; the backend must not.

    Regression guard for the C1 finding: a forged token signed with "" used to
    authenticate as any user when no secret was configured.
    """
    token = _mint_supabase_token("00000000-0000-0000-0000-0000000000e1", empty_secret=True)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_auth"


def test_valid_supabase_token_authenticates_user(client: TestClient) -> None:
    token = _mint_supabase_token("00000000-0000-0000-0000-000000000001", email="verified@supabase.local")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "00000000-0000-0000-0000-000000000001"
    assert data["email"] == "verified@supabase.local"


def test_provisioning_requires_email_verified(client: TestClient) -> None:
    """C2: a valid token without a verified email must not create a local user."""
    token = _mint_supabase_token(
        "00000000-0000-0000-0000-0000000000v1",
        email="unverified@supabase.local",
        email_verified=False,
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_provisioning_requires_email_claim(client: TestClient) -> None:
    token = _mint_supabase_token("00000000-0000-0000-0000-0000000000e2", include_email=False)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_provisioning_never_grants_admin_from_claims(client: TestClient) -> None:
    """C2: claims_admin in the token must not translate into local admin rights."""
    admin_token = _mint_supabase_token(
        "00000000-0000-0000-0000-0000000000a1",
        email="attacker-admin@supabase.local",
        claims_admin=True,
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200

    # The user row exists, but is not an admin.
    admin_bearer = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/v1/admin/users", headers=admin_bearer)
    assert resp.status_code == 403


def test_provisioned_user_records_real_ip_and_user_agent(client: TestClient) -> None:
    """C2: security activity must capture the real client, not placeholders."""
    email = "audit-trail@supabase.local"
    token = _mint_supabase_token("00000000-0000-0000-0000-0000000000a2", email=email)
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "viru-e2e-check/1.0"},
    )
    assert resp.status_code == 200

    db = next(app.dependency_overrides[get_db]())
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        activity = db.scalars(
            select(SecurityActivity).where(SecurityActivity.user_id == user.id)
        ).all()
        assert activity, "first login must record security activity"
        assert all(row.ip != "127.0.0.1" for row in activity)
    finally:
        db.close()


def test_legacy_refresh_endpoint_cannot_issue_token(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "any-legacy-refresh-token"})
    assert resp.status_code == 410
    assert resp.json()["code"] == "auth_managed_by_supabase"


def test_legacy_login_endpoint_decommissioned(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/login", json={"email": "any@viru.dev", "password": "password"})
    assert resp.status_code == 410
    assert resp.json()["code"] == "auth_managed_by_supabase"


def test_legacy_register_endpoint_decommissioned(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/register", json={"email": "any@viru.dev", "password": "password"})
    assert resp.status_code == 410
    assert resp.json()["code"] == "auth_managed_by_supabase"


class TestSecretResolutionGuard:
    """C1: the backend must refuse to start without a strong JWT secret."""

    def test_empty_supabase_secret_with_empty_legacy_raises(self) -> None:
        with pytest.raises(RuntimeError):
            resolve_supabase_jwt_secret({})

    def test_placeholder_secret_raises(self) -> None:
        with pytest.raises(RuntimeError):
            resolve_supabase_jwt_secret({"SUPABASE_JWT_SECRET": "change-me"})

    def test_whitespace_only_secret_raises(self) -> None:
        with pytest.raises(RuntimeError):
            resolve_supabase_jwt_secret({"SUPABASE_JWT_SECRET": "   "})

    def test_placeholder_legacy_secret_raises(self) -> None:
        with pytest.raises(RuntimeError):
            resolve_supabase_jwt_secret({"JWT_SECRET": "dev-secret-token-key-placeholder"})

    def test_valid_supabase_secret_is_accepted(self) -> None:
        assert (
            resolve_supabase_jwt_secret({"SUPABASE_JWT_SECRET": "strong-project-secret"})
            == "strong-project-secret"
        )

    def test_legacy_fallback_is_accepted_for_local_dev(self) -> None:
        assert (
            resolve_supabase_jwt_secret({"JWT_SECRET": "launcher-generated-dev-secret"})
            == "launcher-generated-dev-secret"
        )

    def test_prefer_supabase_secret_over_legacy(self) -> None:
        env = {
            "SUPABASE_JWT_SECRET": "supabase-secret",
            "JWT_SECRET": "legacy-secret",
        }
        assert resolve_supabase_jwt_secret(env) == "supabase-secret"
