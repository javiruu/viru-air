from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db.models import HotelCompSet, HotelProperty, HotelRateSnapshot
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


def test_hotels_read_endpoints_do_not_depend_on_feature_flag_when_data_exists(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = register_and_token(client, email="hotels-read-feature-flag-off@viru.dev")
    headers = _auth(token)
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "false")

    db, generator = _open_overridden_db()
    try:
        hotel = HotelProperty(
            canonical_name="Hotel Lectura Persistida",
            normalized_name="hotel lectura persistida",
            city="Madrid",
            country_code="ES",
            stars=4,
        )
        db.add(hotel)
        db.flush()
        db.add(
            HotelRateSnapshot(
                hotel_id=hotel.id,
                provider="mock",
                check_in=date(2026, 7, 1),
                check_out=date(2026, 7, 3),
                guests=2,
                currency="EUR",
                amount=120,
            )
        )
        db.commit()
        hotel_id = hotel.id
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    search = client.get("/api/v1/hotels/search", headers=headers)
    assert search.status_code == 200
    assert any(item["id"] == hotel_id for item in search.json())

    detail = client.get(f"/api/v1/hotels/{hotel_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == hotel_id

    rates = client.get(f"/api/v1/hotels/{hotel_id}/rates", headers=headers)
    assert rates.status_code == 200
    assert len(rates.json()) == 1


def test_hotels_ingest_mock_fails_cleanly_when_feature_flag_is_disabled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = register_and_token(client, email="hotels-ingest-feature-flag-off@viru.dev")
    headers = _auth(token)
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "false")

    response = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert response.status_code == 422
    assert "HOTEL_FEATURE_ENABLED" in _error_code(response.json())


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


# ── Tracked Offers ──────────────────────────────────────────────────


def test_hotels_tracked_offers_start_empty(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-tracked-empty@viru.dev")
    headers = _auth(token)

    response = client.get("/api/v1/hotels/tracked-offers", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_hotels_tracked_offers_crud_flow(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-tracked-crud@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    # Create
    created = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers,
        json={
            "hotel_id": hotel_id,
            "area_label": "Madrid Centro",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
            "guests": 2,
            "provider": "booking",
            "initial_price": 120.50,
            "target_price": 100.00,
            "currency": "EUR",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    offer_id = payload["id"]
    assert payload["hotel_id"] == hotel_id
    assert payload["initial_price"] == 120.50
    assert payload["is_active"] is True

    # List
    listed = client.get("/api/v1/hotels/tracked-offers", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == offer_id

    # Get single
    detail = client.get(f"/api/v1/hotels/tracked-offers/{offer_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == offer_id
    assert detail.json()["provider"] == "booking"

    # Update
    patched = client.patch(
        f"/api/v1/hotels/tracked-offers/{offer_id}",
        headers=headers,
        json={"current_price": 110.00, "target_price": 95.00},
    )
    assert patched.status_code == 200
    assert patched.json()["current_price"] == 110.00
    assert patched.json()["target_price"] == 95.00
    assert patched.json()["initial_price"] == 120.50

    # Delete
    deleted = client.delete(f"/api/v1/hotels/tracked-offers/{offer_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "ok"

    # Verify deleted
    listed_after = client.get("/api/v1/hotels/tracked-offers", headers=headers)
    assert listed_after.status_code == 200
    assert listed_after.json() == []


def test_hotels_tracked_offers_ownership_enforced(client: TestClient) -> None:
    token_a = register_and_token(client, email="hotels-tracked-owner-a@viru.dev")
    token_b = register_and_token(client, email="hotels-tracked-owner-b@viru.dev")
    headers_a = _auth(token_a)
    headers_b = _auth(token_b)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers_a)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers_a).json()[0]["id"]

    created = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers_a,
        json={
            "hotel_id": hotel_id,
            "provider": "mock",
            "initial_price": 100.00,
            "currency": "EUR",
        },
    )
    assert created.status_code == 201
    offer_id = created.json()["id"]

    # User B cannot see user A's tracked offer
    detail_b = client.get(f"/api/v1/hotels/tracked-offers/{offer_id}", headers=headers_b)
    assert detail_b.status_code == 403

    # User B cannot update user A's tracked offer
    patch_b = client.patch(
        f"/api/v1/hotels/tracked-offers/{offer_id}",
        headers=headers_b,
        json={"current_price": 50.00},
    )
    assert patch_b.status_code == 403

    # User B cannot delete user A's tracked offer
    delete_b = client.delete(f"/api/v1/hotels/tracked-offers/{offer_id}", headers=headers_b)
    assert delete_b.status_code == 403

    # User B's list is empty
    list_b = client.get("/api/v1/hotels/tracked-offers", headers=headers_b)
    assert list_b.status_code == 200
    assert list_b.json() == []


def test_hotels_tracked_offers_not_found_returns_404(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-tracked-404@viru.dev")
    headers = _auth(token)
    fake_id = "00000000-0000-0000-0000-000000000000"

    detail = client.get(f"/api/v1/hotels/tracked-offers/{fake_id}", headers=headers)
    assert detail.status_code == 404
    assert _error_code(detail.json()) == "tracked_offer_not_found"

    patch = client.patch(f"/api/v1/hotels/tracked-offers/{fake_id}", headers=headers, json={"current_price": 50.00})
    assert patch.status_code == 404
    assert _error_code(patch.json()) == "tracked_offer_not_found"

    delete = client.delete(f"/api/v1/hotels/tracked-offers/{fake_id}", headers=headers)
    assert delete.status_code == 404
    assert _error_code(delete.json()) == "tracked_offer_not_found"


def test_hotels_tracked_offers_filter_active(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-tracked-filter@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    offer1 = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers,
        json={"hotel_id": hotel_id, "provider": "mock", "initial_price": 100.00, "currency": "EUR"},
    )
    assert offer1.status_code == 201
    offer1_id = offer1.json()["id"]

    offer2 = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers,
        json={"hotel_id": hotel_id, "provider": "booking", "initial_price": 120.00, "currency": "EUR"},
    )
    assert offer2.status_code == 201
    offer2_id = offer2.json()["id"]

    # Deactivate first offer
    client.patch(f"/api/v1/hotels/tracked-offers/{offer1_id}", headers=headers, json={"is_active": False})

    active = client.get("/api/v1/hotels/tracked-offers?is_active=true", headers=headers)
    assert active.status_code == 200
    assert len(active.json()) == 1
    assert active.json()[0]["id"] == offer2_id

    inactive = client.get("/api/v1/hotels/tracked-offers?is_active=false", headers=headers)
    assert inactive.status_code == 200
    assert len(inactive.json()) == 1
    assert inactive.json()[0]["id"] == offer1_id


# ── Tracked Offer Snapshots ─────────────────────────────────────────


def test_hotels_tracked_offer_snapshots_endpoint(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-snapshots@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    # Create a tracked offer
    created = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers,
        json={
            "hotel_id": hotel_id,
            "area_label": "Madrid Centro",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
            "guests": 2,
            "provider": "mock",
            "initial_price": 120.00,
            "currency": "EUR",
        },
    )
    assert created.status_code == 201
    offer_id = created.json()["id"]

    # An initial snapshot is created automatically when dates+price are provided
    snapshots = client.get(f"/api/v1/hotels/tracked-offers/{offer_id}/snapshots", headers=headers)
    assert snapshots.status_code == 200
    results = snapshots.json()
    assert len(results) == 1
    assert results[0]["tracked_offer_id"] == offer_id
    assert results[0]["amount"] == 120.00
    assert results[0]["availability_status"] == "available"
    assert results[0]["hotel_id"] == hotel_id
    assert results[0]["check_in"] == "2026-08-01"
    assert results[0]["check_out"] == "2026-08-03"
    assert results[0]["provider"] == "mock"


def test_hotels_tracked_offer_snapshots_enforces_ownership(client: TestClient) -> None:
    token_a = register_and_token(client, email="hotels-snapshots-owner-a@viru.dev")
    token_b = register_and_token(client, email="hotels-snapshots-owner-b@viru.dev")
    headers_a = _auth(token_a)
    headers_b = _auth(token_b)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers_a)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers_a).json()[0]["id"]

    created = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers_a,
        json={"hotel_id": hotel_id, "provider": "mock", "initial_price": 100.00, "currency": "EUR"},
    )
    assert created.status_code == 201
    offer_id = created.json()["id"]

    # User B cannot access snapshots of user A's tracked offer
    response = client.get(f"/api/v1/hotels/tracked-offers/{offer_id}/snapshots", headers=headers_b)
    assert response.status_code == 403


def test_hotels_tracked_offer_snapshots_not_found_returns_404(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-snapshots-404@viru.dev")
    headers = _auth(token)
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(f"/api/v1/hotels/tracked-offers/{fake_id}/snapshots", headers=headers)
    assert response.status_code == 404
    assert _error_code(response.json()) == "tracked_offer_not_found"


def test_hotels_tracked_offers_rejects_invalid_hotel(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-tracked-invalid-hotel@viru.dev")
    headers = _auth(token)
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers,
        json={"hotel_id": fake_id, "provider": "mock", "currency": "EUR"},
    )
    assert response.status_code == 404
    assert _error_code(response.json()) == "hotel_not_found"


# ── Area Resolve ──────────────────────────────────────────────────


def test_hotels_area_resolve_madrid_after_ingest(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-resolve-madrid@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200

    response = client.get("/api/v1/hotels/area-resolve", headers=headers, params={"q": "Madrid"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["area_label"] == "Madrid"
    assert 40.4 <= payload["latitude"] <= 40.5
    assert -3.8 <= payload["longitude"] <= -3.6
    assert payload["country_code"] == "ES"
    assert payload["confidence"] in {"low", "medium", "high"}
    assert payload["source"] == "internal"


def test_hotels_area_resolve_malaga_after_ingest(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-resolve-malaga@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200

    response = client.get("/api/v1/hotels/area-resolve", headers=headers, params={"q": "Malaga"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["area_label"] == "Malaga"
    assert 36.7 <= payload["latitude"] <= 36.8
    assert -4.5 <= payload["longitude"] <= -4.3
    assert payload["country_code"] == "ES"


def test_hotels_area_resolve_not_found_returns_404(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-resolve-404@viru.dev")
    headers = _auth(token)

    response = client.get("/api/v1/hotels/area-resolve", headers=headers, params={"q": "Tokyo"})
    assert response.status_code == 404
    assert _error_code(response.json()) == "area_not_found"


def test_hotels_area_resolve_empty_query_returns_422(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-resolve-empty@viru.dev")
    headers = _auth(token)

    response = client.get("/api/v1/hotels/area-resolve", headers=headers, params={"q": ""})
    assert response.status_code == 422


# ── Area Search ────────────────────────────────────────────────────


def test_hotels_area_search_requires_coordinates(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-missing-coords@viru.dev")
    headers = _auth(token)

    # Missing latitude
    response = client.get(
        "/api/v1/hotels/area-search",
        headers=headers,
        params={
            "longitude": -3.7038,
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        },
    )
    assert response.status_code == 422


def test_hotels_area_search_returns_results_after_ingest(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-search@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200

    response = client.get(
        "/api/v1/hotels/area-search",
        headers=headers,
        params={
            "latitude": 40.4168,
            "longitude": -3.7038,
            "radius_km": 50,
            "check_in": "2026-07-01",
            "check_out": "2026-07-03",
            "guests": 2,
            "currency": "EUR",
        },
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    for item in results:
        assert "hotel_id" in item
        assert "canonical_name" in item
        assert "distance_km" in item
        assert "lowest_price" in item or item["lowest_price"] is None
        assert "has_tracking" in item


def test_hotels_area_search_supports_sort_by_distance(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-sort-distance@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200

    response = client.get(
        "/api/v1/hotels/area-search",
        headers=headers,
        params={
            "latitude": 40.4168,
            "longitude": -3.7038,
            "radius_km": 50,
            "check_in": "2026-07-01",
            "check_out": "2026-07-03",
            "guests": 2,
            "currency": "EUR",
            "sort": "distance",
        },
    )
    assert response.status_code == 200
    results = response.json()
    if len(results) >= 2:
        for i in range(len(results) - 1):
            assert results[i]["distance_km"] <= results[i + 1]["distance_km"]


def test_hotels_area_search_filters_by_stars(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-stars@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200

    response = client.get(
        "/api/v1/hotels/area-search",
        headers=headers,
        params={
            "latitude": 40.4168,
            "longitude": -3.7038,
            "radius_km": 50,
            "check_in": "2026-07-01",
            "check_out": "2026-07-03",
            "guests": 2,
            "currency": "EUR",
            "min_stars": 5,
        },
    )
    assert response.status_code == 200
    results = response.json()
    for item in results:
        if item["stars"] is not None:
            assert item["stars"] >= 5


def test_hotels_area_search_rejects_invalid_sort(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-invalid-sort@viru.dev")
    headers = _auth(token)

    response = client.get(
        "/api/v1/hotels/area-search",
        headers=headers,
        params={
            "latitude": 40.4168,
            "longitude": -3.7038,
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
            "sort": "invalid",
        },
    )
    assert response.status_code == 422
    assert _error_code(response.json()) == "invalid_sort_value"


def test_hotels_area_search_rejects_invalid_date_range(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-area-invalid-dates@viru.dev")
    headers = _auth(token)

    response = client.get(
        "/api/v1/hotels/area-search",
        headers=headers,
        params={
            "latitude": 40.4168,
            "longitude": -3.7038,
            "check_in": "2026-08-05",
            "check_out": "2026-08-03",
        },
    )
    assert response.status_code == 422
    assert _error_code(response.json()) == "invalid_date_range"


def test_hotels_alert_events_can_be_filtered_by_hotel_id(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-alert-events-filtered@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200

    hotels = client.get("/api/v1/hotels/search", headers=headers).json()
    assert len(hotels) >= 2
    target_hotel_id = hotels[0]["id"]
    other_hotel_id = hotels[1]["id"]

    target_rule = client.post(
        "/api/v1/hotels/alert-rules",
        headers=headers,
        json={
            "hotel_id": target_hotel_id,
            "rule_type": "price_below",
            "threshold_amount": 500,
            "is_active": True,
        },
    )
    assert target_rule.status_code == 200

    other_rule = client.post(
        "/api/v1/hotels/alert-rules",
        headers=headers,
        json={
            "hotel_id": other_hotel_id,
            "rule_type": "price_below",
            "threshold_amount": 500,
            "is_active": True,
        },
    )
    assert other_rule.status_code == 200

    db, generator = _open_overridden_db()
    try:
        provider_run = run_hotel_sweep(db, provider="mock")
        assert provider_run.status == "completed"
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(f"/api/v1/hotels/alert-events?hotel_id={target_hotel_id}", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert all(item["hotel_id"] == target_hotel_id for item in payload)
    assert all(item["event_type"] == "price_below" for item in payload)


# ── Comp Set Delete ─────────────────────────────────────────────────


def test_hotels_comp_set_delete_returns_ok(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-comp-set-delete@viru.dev")
    headers = _auth(token)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers)
    assert ingest.status_code == 200
    hotels = client.get("/api/v1/hotels/search", headers=headers).json()
    hotel_id = hotels[0]["id"]

    created = client.post(
        "/api/v1/hotels/comp-sets",
        headers=headers,
        json={"name": "To delete", "anchor_hotel_id": hotel_id},
    )
    assert created.status_code == 200
    comp_set_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/hotels/comp-sets/{comp_set_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "ok"

    # Verify it's gone from the list
    listed = client.get("/api/v1/hotels/comp-sets", headers=headers)
    assert listed.status_code == 200
    assert comp_set_id not in [cs["id"] for cs in listed.json()]

    # Second delete returns 404
    second_delete = client.delete(f"/api/v1/hotels/comp-sets/{comp_set_id}", headers=headers)
    assert second_delete.status_code == 404
    assert _error_code(second_delete.json()) == "hotel_comp_set_not_found"


def test_hotels_comp_set_delete_ownership_enforced(client: TestClient) -> None:
    token_a = register_and_token(client, email="hotels-cs-delete-owner-a@viru.dev")
    token_b = register_and_token(client, email="hotels-cs-delete-owner-b@viru.dev")
    headers_a = _auth(token_a)
    headers_b = _auth(token_b)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers_a)
    assert ingest.status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers_a).json()[0]["id"]

    created = client.post(
        "/api/v1/hotels/comp-sets",
        headers=headers_a,
        json={"name": "Mine", "anchor_hotel_id": hotel_id},
    )
    assert created.status_code == 200
    comp_set_id = created.json()["id"]

    # User B tries to delete user A's comp set
    forbidden = client.delete(f"/api/v1/hotels/comp-sets/{comp_set_id}", headers=headers_b)
    assert forbidden.status_code == 403

    # Verify it still exists for user A
    detail = client.get(f"/api/v1/hotels/comp-sets/{comp_set_id}", headers=headers_a)
    assert detail.status_code == 200
    assert detail.json()["id"] == comp_set_id
