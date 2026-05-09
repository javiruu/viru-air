from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.helpers import register_and_token


def _make_watch(client: TestClient, headers: dict) -> str:
    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=22)),
            "target_price": 35,
        },
    )
    assert create.status_code == 200
    return create.json()["id"]


def test_error_envelope_shape_is_consistent(client: TestClient) -> None:
    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    bad_watch = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "MAD",
            "travel_date_local": str(date.today() + timedelta(days=8)),
        },
    )
    assert bad_watch.status_code == 400
    payload = bad_watch.json()
    assert set(payload.keys()) >= {"status", "code", "message", "details"}
    assert payload["status"] == 400
    assert payload["code"] == "origin_equals_destination"

    bad_search = client.post("/api/v1/search/quick", json={})
    assert bad_search.status_code == 422
    payload_search = bad_search.json()
    assert payload_search["code"] == "quick_search_invalid_request"
    assert isinstance(payload_search["details"], list)


def test_idempotency_create_watch_and_rule(client: TestClient) -> None:
    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "idem-watch-1"}

    watch_payload = {
        "origin_iata": "MAD",
        "destination_iata": "DUB",
        "travel_date_local": str(date.today() + timedelta(days=14)),
        "target_price": 40,
    }
    first = client.post("/api/v1/watchlist", headers=headers, json=watch_payload)
    second = client.post("/api/v1/watchlist", headers=headers, json=watch_payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.headers.get("x-idempotency-replayed") == "true"

    mismatch = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={**watch_payload, "destination_iata": "BCN"},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["code"] == "idempotency_mismatch"

    watch_id = first.json()["id"]
    rule_headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "idem-rule-1"}
    rule_payload = {
        "watch_id": watch_id,
        "rule_type": "threshold_below",
        "threshold_value": 30,
        "notify_on_every_change": False,
        "cooldown_minutes": 60,
    }
    rule_first = client.post("/api/v1/alerts/rules", headers=rule_headers, json=rule_payload)
    rule_second = client.post("/api/v1/alerts/rules", headers=rule_headers, json=rule_payload)
    assert rule_first.status_code == 200
    assert rule_first.json()["rule_type"] == "threshold_low"
    assert rule_second.json()["id"] == rule_first.json()["id"]
    assert rule_second.headers.get("x-idempotency-replayed") == "true"


def test_idempotency_refresh_and_rule_type_validation(client: TestClient) -> None:
    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    watch_id = _make_watch(client, headers)

    refresh_headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "idem-refresh-1"}
    first = client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=refresh_headers)
    second = client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=refresh_headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers.get("x-idempotency-replayed") == "true"

    invalid_rule = client.post(
        "/api/v1/alerts/rules",
        headers=headers,
        json={
            "watch_id": watch_id,
            "rule_type": "not-real",
            "threshold_value": 10,
            "cooldown_minutes": 60,
        },
    )
    assert invalid_rule.status_code == 422
    body = invalid_rule.json()
    assert body["code"] == "validation_error"
    assert any("invalid_rule_type" in (detail.get("msg") or "") for detail in body["details"])


def test_correlation_id_is_normalized_in_response(client: TestClient) -> None:
    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}", "x-correlation-id": "bad value with spaces"}
    response = client.get("/api/v1/watchlist", headers=headers)
    assert response.status_code == 200
    normalized = response.headers.get("x-correlation-id")
    assert normalized
    assert " " not in normalized
