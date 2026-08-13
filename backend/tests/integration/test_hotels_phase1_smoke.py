from __future__ import annotations

from fastapi.testclient import TestClient

from app.infrastructure.db.models import HotelProviderRun, User
from app.infrastructure.db.session import get_db
from app.main import app
from app.services.hotels_service import (
    evaluate_hotel_alerts,
    materialize_hotel_delivery_intents,
    sweep_tracked_offers,
)
from tests.helpers import register_and_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _open_overridden_db():
    generator = app.dependency_overrides[get_db]()
    return next(generator), generator


def _close_overridden_db(generator) -> None:
    try:
        next(generator)
    except StopIteration:
        pass


def test_h44_smoke_search_tracking_alert_inbox_and_ownership(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")

    token_a = register_and_token(client, email="h44-smoke-a@viru.dev")
    token_b = register_and_token(client, email="h44-smoke-b@viru.dev")
    headers_a = _auth(token_a)
    headers_b = _auth(token_b)

    ingest = client.post("/api/v1/hotels/ingest/mock", headers=headers_a)
    assert ingest.status_code == 200
    assert ingest.json()["provider_id"] == "mock"
    assert ingest.json()["provider_run_id"]

    search = client.get(
        "/api/v1/hotels/search",
        headers=headers_a,
        params={"city": "Madrid", "q": "Hotel Sol Madrid"},
    )
    assert search.status_code == 200
    hotel_id = search.json()[0]["id"]

    detail = client.get(f"/api/v1/hotels/{hotel_id}", headers=headers_a)
    rates = client.get(
        f"/api/v1/hotels/{hotel_id}/rates",
        headers=headers_a,
        params={"check_in": "2026-07-10", "check_out": "2026-07-12"},
    )
    assert detail.status_code == 200
    assert rates.status_code == 200
    assert rates.json()

    tracked = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers_a,
        json={
            "hotel_id": hotel_id,
            "check_in": "2026-07-10",
            "check_out": "2026-07-12",
            "guests": 2,
            "provider": "mock",
            "initial_price": 250,
            "currency": "EUR",
        },
    )
    assert tracked.status_code == 201
    tracked_id = tracked.json()["id"]

    rule = client.post(
        "/api/v1/hotels/alert-rules",
        headers=headers_a,
        json={
            "hotel_id": hotel_id,
            "tracked_offer_id": tracked_id,
            "rule_type": "price_below",
            "threshold_amount": 220,
            "is_active": True,
        },
    )
    assert rule.status_code == 200

    db, generator = _open_overridden_db()
    try:
        provider_run = HotelProviderRun(provider="mock", status="completed")
        db.add(provider_run)
        db.flush()
        sweep_outcomes = sweep_tracked_offers(db, provider_run_id=provider_run.id)
        assert sweep_outcomes["snapshots_created"] >= 1
        evaluate_hotel_alerts(db, provider_run_id=provider_run.id)
        materialize_hotel_delivery_intents(db, provider_run_id=provider_run.id)
        db.commit()
    finally:
        _close_overridden_db(generator)

    events_a = client.get("/api/v1/hotels/alert-events", headers=headers_a)
    assert events_a.status_code == 200
    assert events_a.json()
    assert all(item["hotel_id"] == hotel_id for item in events_a.json())

    inbox_a = client.get("/api/v1/notifications", headers=headers_a)
    inbox_b = client.get("/api/v1/notifications", headers=headers_b)
    assert inbox_a.status_code == 200
    assert inbox_b.status_code == 200
    assert inbox_a.json()["items"]
    assert any(item["source_type"] == "hotel_alert_event" for item in inbox_a.json()["items"])
    event_ids_a = {item["id"] for item in events_a.json()}
    inbox_a_hotel_ids = {
        item["source_id"]
        for item in inbox_a.json()["items"]
        if item["source_type"] == "hotel_alert_event"
    }
    inbox_b_hotel_ids = {
        item["source_id"]
        for item in inbox_b.json()["items"]
        if item["source_type"] == "hotel_alert_event"
    }
    assert inbox_a_hotel_ids
    assert inbox_a_hotel_ids.issubset(event_ids_a)
    assert inbox_a_hotel_ids.isdisjoint(inbox_b_hotel_ids)

    foreign_offer = client.get(f"/api/v1/hotels/tracked-offers/{tracked_id}", headers=headers_b)
    foreign_events = client.get("/api/v1/hotels/alert-events", headers=headers_b)
    assert foreign_offer.status_code == 403
    assert foreign_events.json() == []

    db, generator = _open_overridden_db()
    try:
        user_a = db.query(User).filter_by(email="h44-smoke-a@viru.dev").one()
        user_b = db.query(User).filter_by(email="h44-smoke-b@viru.dev").one()
        assert user_a.id != user_b.id
    finally:
        _close_overridden_db(generator)
