from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import register_and_token


def test_account_profile_sessions_and_security_activity(client: TestClient) -> None:
    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # /auth/login decommissioned in favor of Supabase Auth

    profile = client.get("/api/v1/account/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == "qa@viru.dev"

    sessions = client.get("/api/v1/account/sessions", headers=headers)
    assert sessions.status_code == 200
    assert len(sessions.json()["items"]) >= 1

    close_all = client.post("/api/v1/account/sessions/close_all", headers=headers)
    assert close_all.status_code == 200
    assert close_all.json()["status"] == "ok"

    activity = client.get("/api/v1/account/security/activity", headers=headers)
    assert activity.status_code == 200
    assert len(activity.json()["items"]) >= 1
