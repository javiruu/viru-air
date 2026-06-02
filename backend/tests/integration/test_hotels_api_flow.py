import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db.models import HotelCompSet, HotelProperty
from app.infrastructure.db.session import get_db
from app.main import app
from app.services.hotels_service import run_hotel_sweep
from tests.helpers import register_and_token


@pytest.fixture(autouse=True)
def _enable_hotels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _error_code(payload: dict) -> str | None:
    return payload.get("detail") or payload.get("code")


def _open_overridden_db():
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    return db, generator


def test_hotels_search_without_results_returns_empty_list(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-search-empty@viru.dev")
    response = client.get(
        "/api/v1/hotels/search",
        params={"q": "hotel-inexistente-zz"},
        headers=_auth(token),
    )
    assert response.status_code == 200
    assert response.json() == []


def test_hotels_search_rejects_invalid_country_code(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-search-invalid-country@viru.dev")
    response = client.get(
        "/api/v1/hotels/search",
        params={"country_code": "E1"},
        headers=_auth(token),
    )
    assert response.status_code == 422
    assert _error_code(response.json()) == "invalid_country_code"


def test_hotels_collections_start_empty(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-empty-collections@viru.dev")
    headers = _auth(token)

    watchlist = client.get("/api/v1/hotels/watchlist", headers=headers)
    assert watchlist.status_code == 200
    assert watchlist.json() == []

    comp_sets = client.get("/api/v1/hotels/comp-sets", headers=headers)
    assert comp_sets.status_code == 200
    assert comp_sets.json() == []

    alert_rules = client.get("/api/v1/hotels/alert-rules", headers=headers)
    assert alert_rules.status_code == 200
    assert alert_rules.json() == []

    alert_events = client.get("/api/v1/hotels/alert-events", headers=headers)
    assert alert_events.status_code == 200
    assert alert_events.json() == []


def test_hotels_ingest_mock_and_basic_flow(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-flow@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    ingest_payload = ingest.json()
    assert ingest_payload["provider_id"] == "mock"
    assert ingest_payload["hotels_processed"] >= 1

    search = client.get("/api/v1/hotels/search", headers=headers)
    assert search.status_code == 200
    hotels = search.json()
    assert len(hotels) >= 1
    hotel_id = hotels[0]["id"]

    detail = client.get(f"/api/v1/hotels/{hotel_id}", headers=headers)
    assert detail.status_code == 200

    rates = client.get(f"/api/v1/hotels/{hotel_id}/rates", headers=headers)
    assert rates.status_code == 200

    watch_create = client.post("/api/v1/hotels/watchlist", headers=headers, json={"hotel_id": hotel_id, "label": "Seguimiento"})
    assert watch_create.status_code == 200
    watch_id = watch_create.json()["id"]

    watch_list = client.get("/api/v1/hotels/watchlist", headers=headers)
    assert watch_list.status_code == 200
    assert any(item["id"] == watch_id for item in watch_list.json())

    watch_delete = client.delete(f"/api/v1/hotels/watchlist/{watch_id}", headers=headers)
    assert watch_delete.status_code == 200


def test_hotels_comp_set_create_member_and_detail(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-comp-set@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200

    hotels = client.get("/api/v1/hotels/search", headers=headers).json()
    assert len(hotels) >= 1
    anchor_hotel_id = hotels[0]["id"]
    member_hotel_id = hotels[-1]["id"]

    comp_create = client.post(
        "/api/v1/hotels/comp-sets",
        headers=headers,
        json={"name": "Comp Madrid", "anchor_hotel_id": anchor_hotel_id},
    )
    assert comp_create.status_code == 200
    comp_set_id = comp_create.json()["id"]

    add_member = client.post(
        f"/api/v1/hotels/comp-sets/{comp_set_id}/members",
        headers=headers,
        json={"hotel_id": member_hotel_id},
    )
    assert add_member.status_code == 200

    detail = client.get(f"/api/v1/hotels/comp-sets/{comp_set_id}", headers=headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["id"] == comp_set_id
    assert len(payload["members"]) >= 1
    member_id = payload["members"][0]["id"]

    deleted = client.delete(f"/api/v1/hotels/comp-sets/{comp_set_id}/members/{member_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "ok"


def test_hotels_comp_set_nearby_suggestions_returns_candidates(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-nearby@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotels = client.get("/api/v1/hotels/search", headers=headers).json()
    anchor_hotel_id = hotels[0]["id"]

    comp_create = client.post(
        "/api/v1/hotels/comp-sets",
        headers=headers,
        json={"name": "Geo Madrid", "anchor_hotel_id": anchor_hotel_id},
    )
    assert comp_create.status_code == 200
    comp_set_id = comp_create.json()["id"]

    response = client.get(
        f"/api/v1/hotels/comp-sets/{comp_set_id}/nearby-suggestions",
        headers=headers,
        params={"radius_km": 5, "limit": 6},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert all(item["hotel_id"] != anchor_hotel_id for item in payload)
    assert all(item["distance_km"] <= 5 for item in payload)


def test_hotels_comp_set_nearby_suggestions_enforce_ownership(client: TestClient) -> None:
    token_a = register_and_token(client, email="hotels-nearby-owner-a@viru.dev")
    token_b = register_and_token(client, email="hotels-nearby-owner-b@viru.dev")
    headers_a = _auth(token_a)
    headers_b = _auth(token_b)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers_a)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers_a).json()[0]["id"]

    comp_create = client.post(
        "/api/v1/hotels/comp-sets",
        headers=headers_a,
        json={"name": "Owner A geo", "anchor_hotel_id": hotel_id},
    )
    assert comp_create.status_code == 200
    comp_set_id = comp_create.json()["id"]

    response = client.get(f"/api/v1/hotels/comp-sets/{comp_set_id}/nearby-suggestions", headers=headers_b)
    assert response.status_code == 403


def test_hotels_comp_set_nearby_suggestions_not_found_returns_404(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-nearby-404@viru.dev")
    headers = _auth(token)
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(f"/api/v1/hotels/comp-sets/{fake_id}/nearby-suggestions", headers=headers)
    assert response.status_code == 404
    assert _error_code(response.json()) == "hotel_comp_set_not_found"


def test_hotels_comp_set_nearby_suggestions_require_anchor_coordinates(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-nearby-missing-coords@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    comp_create = client.post(
        "/api/v1/hotels/comp-sets",
        headers=headers,
        json={"name": "Geo missing coords", "anchor_hotel_id": hotel_id},
    )
    assert comp_create.status_code == 200
    comp_set_id = comp_create.json()["id"]

    db, generator = _open_overridden_db()
    try:
        comp_set = db.get(HotelCompSet, comp_set_id)
        anchor = db.get(HotelProperty, comp_set.anchor_hotel_id)
        anchor.latitude = None
        anchor.longitude = None
        db.add(anchor)
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(f"/api/v1/hotels/comp-sets/{comp_set_id}/nearby-suggestions", headers=headers)
    assert response.status_code == 422
    assert _error_code(response.json()) == "hotel_comp_set_anchor_missing_coordinates"


def test_hotels_comp_set_rejects_anchor_as_member(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-comp-set-anchor-member@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    anchor_hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    comp_create = client.post(
        "/api/v1/hotels/comp-sets",
        headers=headers,
        json={"name": "Anchor guard", "anchor_hotel_id": anchor_hotel_id},
    )
    assert comp_create.status_code == 200
    comp_set_id = comp_create.json()["id"]

    response = client.post(
        f"/api/v1/hotels/comp-sets/{comp_set_id}/members",
        headers=headers,
        json={"hotel_id": anchor_hotel_id},
    )
    assert response.status_code == 409
    assert _error_code(response.json()) == "hotel_comp_set_anchor_cannot_be_member"


def test_hotels_ownership_enforced_between_users(client: TestClient) -> None:
    token_a = register_and_token(client, email="hotels-owner-a@viru.dev")
    token_b = register_and_token(client, email="hotels-owner-b@viru.dev")
    headers_a = _auth(token_a)
    headers_b = _auth(token_b)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers_a)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers_a).json()[0]["id"]

    watch = client.post("/api/v1/hotels/watchlist", headers=headers_a, json={"hotel_id": hotel_id})
    assert watch.status_code == 200
    watch_id = watch.json()["id"]

    forbidden_watch_delete = client.delete(f"/api/v1/hotels/watchlist/{watch_id}", headers=headers_b)
    assert forbidden_watch_delete.status_code == 403

    comp = client.post(
        "/api/v1/hotels/comp-sets",
        headers=headers_a,
        json={"name": "Owner A", "anchor_hotel_id": hotel_id},
    )
    assert comp.status_code == 200
    comp_set_id = comp.json()["id"]

    forbidden_comp_read = client.get(f"/api/v1/hotels/comp-sets/{comp_set_id}", headers=headers_b)
    assert forbidden_comp_read.status_code == 403


def test_hotels_alert_rule_patch_can_clear_thresholds_with_null(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-alert-patch-null@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    created = client.post(
        "/api/v1/hotels/alert-rules",
        headers=headers,
        json={
            "hotel_id": hotel_id,
            "rule_type": "price_below",
            "threshold_amount": 150,
            "threshold_percent": 10,
            "is_active": True,
        },
    )
    assert created.status_code == 200
    rule_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/hotels/alert-rules/{rule_id}",
        headers=headers,
        json={"threshold_amount": None, "threshold_percent": None},
    )
    assert patched.status_code == 200
    payload = patched.json()
    assert payload["threshold_amount"] is None
    assert payload["threshold_percent"] is None


def test_hotels_watchlist_duplicate_returns_409_and_stable_detail(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-watchlist-duplicate@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    first = client.post("/api/v1/hotels/watchlist", headers=headers, json={"hotel_id": hotel_id})
    assert first.status_code == 200

    duplicate = client.post("/api/v1/hotels/watchlist", headers=headers, json={"hotel_id": hotel_id})
    assert duplicate.status_code == 409
    assert _error_code(duplicate.json()) == "hotel_watchlist_item_already_exists"


def test_hotels_not_found_endpoints_return_404_with_consistent_detail(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-not-found@viru.dev")
    headers = _auth(token)
    fake_id = "00000000-0000-0000-0000-000000000000"

    detail = client.get(f"/api/v1/hotels/{fake_id}", headers=headers)
    assert detail.status_code == 404
    assert _error_code(detail.json()) == "hotel_not_found"

    rates = client.get(f"/api/v1/hotels/{fake_id}/rates", headers=headers)
    assert rates.status_code == 404
    assert _error_code(rates.json()) == "hotel_not_found"

    comp_set = client.get(f"/api/v1/hotels/comp-sets/{fake_id}", headers=headers)
    assert comp_set.status_code == 404
    assert _error_code(comp_set.json()) == "hotel_comp_set_not_found"

    rule_delete = client.delete(f"/api/v1/hotels/alert-rules/{fake_id}", headers=headers)
    assert rule_delete.status_code == 404
    assert _error_code(rule_delete.json()) == "hotel_alert_rule_not_found"


def test_hotels_rates_invalid_date_range_returns_422_with_semantic_detail(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-rates-invalid-range@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    response = client.get(
        f"/api/v1/hotels/{hotel_id}/rates",
        headers=headers,
        params={"check_in": "2026-07-12", "check_out": "2026-07-10"},
    )
    assert response.status_code == 422
    assert _error_code(response.json()) == "invalid_date_range"


def test_hotels_alert_rule_invalid_threshold_combination_returns_422(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-alert-invalid-combination@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    response = client.post(
        "/api/v1/hotels/alert-rules",
        headers=headers,
        json={
            "hotel_id": hotel_id,
            "rule_type": "parity_break",
            "threshold_amount": 25,
            "is_active": True,
        },
    )
    assert response.status_code == 422
    assert _error_code(response.json()) == "threshold_percent_required_for_parity_break"


def test_hotels_parity_returns_signal_after_ingest(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-parity@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    parity = client.get(f"/api/v1/hotels/{hotel_id}/parity", headers=headers)
    assert parity.status_code == 200
    signals = parity.json()
    assert isinstance(signals, list)
    assert len(signals) >= 1
    assert signals[0]["provider_count"] >= 1
    assert signals[0]["status"] in {"info", "success", "warning", "error"}
    assert signals[0]["label"] in {"limited", "stable", "tensioned", "breach"}


def test_hotels_parity_not_found_returns_404(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-parity-404@viru.dev")
    headers = _auth(token)
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(f"/api/v1/hotels/{fake_id}/parity", headers=headers)
    assert response.status_code == 404
    assert _error_code(response.json()) == "hotel_not_found"


def test_hotels_alert_rule_delete_returns_ok(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-alert-delete@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    created = client.post(
        "/api/v1/hotels/alert-rules",
        headers=headers,
        json={
            "hotel_id": hotel_id,
            "rule_type": "price_above",
            "threshold_amount": 220,
            "is_active": True,
        },
    )
    assert created.status_code == 200
    rule_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/hotels/alert-rules/{rule_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "ok"


def test_hotels_alert_events_route_is_not_captured_by_hotel_detail(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-alert-events-empty@viru.dev")
    headers = _auth(token)

    response = client.get("/api/v1/hotels/alert-events", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_hotels_alert_events_lists_triggered_events_after_sweep(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-alert-events-populated@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    created = client.post(
        "/api/v1/hotels/alert-rules",
        headers=headers,
        json={
            "hotel_id": hotel_id,
            "rule_type": "price_below",
            "threshold_amount": 500,
            "is_active": True,
        },
    )
    assert created.status_code == 200

    db, generator = _open_overridden_db()
    try:
        provider_run = run_hotel_sweep(db, provider="mock")
        assert provider_run.status == "completed"
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get("/api/v1/hotels/alert-events", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert any(item["hotel_id"] == hotel_id for item in payload)
    assert any(item["event_type"] == "price_below" for item in payload)
