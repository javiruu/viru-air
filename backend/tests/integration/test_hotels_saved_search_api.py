from fastapi.testclient import TestClient

from tests.helpers import register_and_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_saved_search_crud_is_idempotent_and_private(client: TestClient) -> None:
    token_a = register_and_token(client, email="saved-search-api-a@viru.dev")
    token_b = register_and_token(client, email="saved-search-api-b@viru.dev")
    headers_a = _auth(token_a)
    headers_b = _auth(token_b)
    query = {
        "schema": "hotel-search-v1",
        "params": {
            "mode": "area",
            "area": "Madrid Centro",
            "area_lat": "40.4168",
            "area_lng": "-3.7038",
            "area_country": "ES",
            "check_in": "2026-09-12",
            "check_out": "2026-09-15",
            "guests": "2",
        },
    }

    created = client.post(
        "/api/v1/hotels/saved-searches",
        headers=headers_a,
        json={"schema_version": "hotel-search-v1", "query": query, "label": "Madrid"},
    )
    assert created.status_code == 201
    saved = created.json()
    saved_id = saved["id"]
    assert saved["fingerprint"]
    assert saved["query"] == {
        "schema": "hotel-search-v1",
        "params": {
            "mode": "area",
            "area": "Madrid Centro",
            "area_lat": "40.4168",
            "area_lng": "-3.7038",
            "area_country": "ES",
            "check_in": "2026-09-12",
            "check_out": "2026-09-15",
        },
    }

    duplicate = client.post(
        "/api/v1/hotels/saved-searches",
        headers=headers_a,
        json={"schema_version": "hotel-search-v1", "query": query, "label": "Otro nombre"},
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == saved_id
    assert duplicate.json()["label"] == "Madrid"

    listed_a = client.get("/api/v1/hotels/saved-searches", headers=headers_a)
    listed_b = client.get("/api/v1/hotels/saved-searches", headers=headers_b)
    assert listed_a.status_code == 200
    assert len(listed_a.json()) == 1
    assert listed_b.status_code == 200
    assert listed_b.json() == []

    foreign = client.get(f"/api/v1/hotels/saved-searches/{saved_id}", headers=headers_b)
    assert foreign.status_code == 403

    patched = client.patch(
        f"/api/v1/hotels/saved-searches/{saved_id}",
        headers=headers_a,
        json={"label": "Pausada", "status": "paused"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "paused"
    assert patched.json()["label"] == "Pausada"

    deleted = client.delete(f"/api/v1/hotels/saved-searches/{saved_id}", headers=headers_a)
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "ok"}
    missing = client.get(f"/api/v1/hotels/saved-searches/{saved_id}", headers=headers_a)
    assert missing.status_code == 404


def test_saved_search_rejects_private_fields_and_unknown_version(client: TestClient) -> None:
    token = register_and_token(client, email="saved-search-api-validation@viru.dev")
    headers = _auth(token)

    private = client.post(
        "/api/v1/hotels/saved-searches",
        headers=headers,
        json={
            "schema_version": "hotel-search-v1",
            "query": {"params": {"mode": "name", "email": "secret@example.com"}},
        },
    )
    assert private.status_code == 422

    unknown = client.post(
        "/api/v1/hotels/saved-searches",
        headers=headers,
        json={"schema_version": "hotel-search-v2", "query": {"params": {"mode": "name"}}},
    )
    assert unknown.status_code == 422
