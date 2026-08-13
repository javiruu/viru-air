from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_db
from app.infrastructure.db.models import (
    AlertRule,
    FlightWatch,
    HotelAlertEvent,
    HotelAlertRule,
    HotelProperty,
    HotelProviderRun,
    NotificationEvent,
    SecurityActivity,
    User,
    UserNotificationState,
)
from app.main import app
from app.services.hotels_service import get_hotel_alert_trace
from tests.helpers import register_and_token


def _open_test_db_session():
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    return db, generator


def _close_test_db_session(generator) -> None:
    try:
        next(generator)
    except StopIteration:
        pass


def test_notifications_hotel_events_are_isolated_in_inbox_summary_and_read_state(client: TestClient) -> None:
    token_a = register_and_token(client, email="inbox-hotel-owner-a@viru.dev")
    token_b = register_and_token(client, email="inbox-hotel-owner-b@viru.dev")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    db, generator = _open_test_db_session()
    try:
        user_a = db.scalar(select(User).where(User.email == "inbox-hotel-owner-a@viru.dev"))
        user_b = db.scalar(select(User).where(User.email == "inbox-hotel-owner-b@viru.dev"))
        assert user_a is not None and user_b is not None
        hotel = HotelProperty(
            canonical_name="Hotel Inbox Compartido",
            normalized_name="hotel inbox compartido",
            city="Madrid",
            normalized_city="madrid",
            country_code="ES",
        )
        db.add(hotel)
        db.flush()
        rule_a = HotelAlertRule(
            user_id=user_a.id,
            hotel_id=hotel.id,
            rule_type="price_below",
            threshold_amount=100,
            is_active=True,
        )
        rule_b = HotelAlertRule(
            user_id=user_b.id,
            hotel_id=hotel.id,
            rule_type="price_below",
            threshold_amount=100,
            is_active=True,
        )
        db.add_all([rule_a, rule_b])
        db.flush()
        event_a = HotelAlertEvent(
            rule_id=rule_a.id,
            hotel_id=hotel.id,
            event_type="price_below",
            message="Evento legacy A",
            trigger_value=90,
        )
        event_b = HotelAlertEvent(
            rule_id=rule_b.id,
            hotel_id=hotel.id,
            event_type="price_below",
            message="Evento legacy B",
            trigger_value=80,
        )
        db.add_all([event_a, event_b])
        db.commit()
        event_a_id = event_a.id
        event_b_id = event_b.id
    finally:
        _close_test_db_session(generator)

    inbox_a = client.get("/api/v1/notifications", headers=headers_a)
    inbox_b = client.get("/api/v1/notifications", headers=headers_b)
    assert inbox_a.status_code == 200
    assert inbox_b.status_code == 200
    ids_a = {item["source_id"] for item in inbox_a.json()["items"]}
    ids_b = {item["source_id"] for item in inbox_b.json()["items"]}
    assert event_a_id in ids_a
    assert event_b_id not in ids_a
    assert event_b_id in ids_b
    assert event_a_id not in ids_b

    summary_a = client.get("/api/v1/notifications/summary", headers=headers_a)
    summary_b = client.get("/api/v1/notifications/summary", headers=headers_b)
    assert summary_a.status_code == 200
    assert summary_b.status_code == 200
    assert summary_a.json()["price"] == 1
    assert summary_b.json()["price"] == 1
    unread_a_before = summary_a.json()["unread"]
    unread_b_before = summary_b.json()["unread"]
    assert unread_a_before >= 1
    assert unread_b_before >= 1

    forbidden_mark = client.post(
        f"/api/v1/notifications/hotel_alert_event/{event_b_id}/read",
        headers=headers_a,
    )
    assert forbidden_mark.status_code == 404

    marked = client.post(
        f"/api/v1/notifications/hotel_alert_event/{event_a_id}/read",
        headers=headers_a,
    )
    assert marked.status_code == 200
    assert client.get("/api/v1/notifications/summary", headers=headers_a).json()["unread"] == unread_a_before - 1
    assert client.get("/api/v1/notifications/summary", headers=headers_b).json()["unread"] == unread_b_before


def test_hotel_alert_trace_resolves_provider_run_intent_without_cross_user_fallback(client: TestClient) -> None:
    token_a = register_and_token(client, email="inbox-trace-owner-a@viru.dev")
    register_and_token(client, email="inbox-trace-owner-b@viru.dev")

    db, generator = _open_test_db_session()
    try:
        user_a = db.scalar(select(User).where(User.email == "inbox-trace-owner-a@viru.dev"))
        user_b = db.scalar(select(User).where(User.email == "inbox-trace-owner-b@viru.dev"))
        assert user_a is not None and user_b is not None
        hotel = HotelProperty(
            canonical_name="Hotel Trace Compartido",
            normalized_name="hotel trace compartido",
            city="Madrid",
            normalized_city="madrid",
            country_code="ES",
        )
        db.add(hotel)
        db.flush()
        rule_a = HotelAlertRule(user_id=user_a.id, hotel_id=hotel.id, rule_type="price_below", is_active=True)
        rule_b = HotelAlertRule(user_id=user_b.id, hotel_id=hotel.id, rule_type="price_below", is_active=True)
        run_a = HotelProviderRun(
            provider="mock",
            correlation_id="corr-trace-owner-a",
            client_event_id="intent-trace-owner-a",
            status="completed",
        )
        run_b = HotelProviderRun(
            provider="mock",
            correlation_id="corr-trace-owner-b",
            client_event_id="intent-trace-owner-b",
            status="completed",
        )
        db.add_all([rule_a, rule_b, run_a, run_b])
        db.flush()
        owned_event = HotelAlertEvent(
            user_id=user_a.id,
            rule_id=rule_a.id,
            hotel_id=hotel.id,
            provider_run_id=run_a.id,
            event_type="price_below",
            message="owned event",
        )
        legacy_event = HotelAlertEvent(
            user_id=None,
            rule_id=rule_b.id,
            hotel_id=hotel.id,
            provider_run_id=run_b.id,
            event_type="price_below",
            message="legacy event",
        )
        db.add_all([owned_event, legacy_event])
        db.commit()
        owned_event_id = owned_event.id
        legacy_event_id = legacy_event.id
        run_a_id = run_a.id
        run_b_id = run_b.id
        user_a_id = user_a.id
        user_b_id = user_b.id
    finally:
        _close_test_db_session(generator)

    db, generator = _open_test_db_session()
    try:
        trace = get_hotel_alert_trace(db, user_id=user_a_id, event_id=owned_event_id)
        assert trace is not None
        assert trace.event_id == owned_event_id
        assert trace.provider_run_id == run_a_id
        assert trace.correlation_id == "corr-trace-owner-a"
        assert trace.client_event_id == "intent-trace-owner-a"

        legacy_trace = get_hotel_alert_trace(db, user_id=user_b_id, event_id=legacy_event_id)
        assert legacy_trace is not None
        assert legacy_trace.provider_run_id == run_b_id
        assert legacy_trace.correlation_id == "corr-trace-owner-b"
        assert legacy_trace.client_event_id == "intent-trace-owner-b"
        assert get_hotel_alert_trace(db, user_id=user_b_id, event_id=owned_event_id) is None
    finally:
        _close_test_db_session(generator)

    headers_a = {"Authorization": f"Bearer {token_a}"}
    # Public inbox items remain intentionally free of internal trace identifiers.
    inbox = client.get("/api/v1/notifications", headers=headers_a)
    assert inbox.status_code == 200
    assert all("correlation_id" not in item and "client_event_id" not in item for item in inbox.json()["items"])


def test_notifications_inbox_lists_and_marks_persistent_signals(client: TestClient) -> None:
    email = "inbox@viru.dev"
    token = register_and_token(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}

    db, generator = _open_test_db_session()
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        watch = FlightWatch(
            user_id=user.id,
            origin_iata="MAD",
            destination_iata="DUB",
            travel_date_local=date.today() + timedelta(days=20),
            target_price=45,
        )
        db.add(watch)
        db.flush()
        rule = AlertRule(
            watch_id=watch.id,
            rule_type="threshold_low",
            threshold_value=45,
            cooldown_minutes=60,
        )
        db.add(rule)
        db.flush()
        hotel = HotelProperty(
            canonical_name="Hotel Terminal Norte",
            normalized_name="hotel terminal norte",
            city="Madrid",
            normalized_city="madrid",
            country_code="ES",
        )
        db.add(hotel)
        db.flush()
        hotel_rule = HotelAlertRule(
            user_id=user.id,
            hotel_id=hotel.id,
            rule_type="price_below",
            threshold_amount=120,
            is_active=True,
        )
        db.add(hotel_rule)
        db.flush()
        event = NotificationEvent(
            rule_id=rule.id,
            channel="in_app",
            delivery_status="delivered",
            message="Precio bajo: 39.00 EUR (umbral 45.00).",
            attempts=1,
            group_reason="threshold_low",
        )
        security = SecurityActivity(
            user_id=user.id,
            event_type="login",
            ip="127.0.0.1",
        )
        hotel_event = HotelAlertEvent(
            user_id=user.id,
            rule_id=hotel_rule.id,
            hotel_id=hotel.id,
            event_type="price_below",
            message="Hotel Terminal Norte: bajó a EUR 99.00",
            trigger_value=99,
        )
        db.add_all([event, hotel_event, security])
        db.commit()
        user_id = user.id
        alert_source_id = event.id
        hotel_source_id = hotel_event.id
    finally:
        _close_test_db_session(generator)

    summary = client.get("/api/v1/notifications/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["unread"] >= 3

    inbox = client.get("/api/v1/notifications", headers=headers)
    assert inbox.status_code == 200
    body = inbox.json()
    assert body["summary"]["total"] >= 3
    assert body["summary"]["price"] == 2
    assert body["summary"]["security"] >= 1
    assert body["summary"]["unread"] >= 3
    alert_item = next(item for item in body["items"] if item["source_id"] == alert_source_id)
    assert alert_item["category"] == "price"
    assert alert_item["route_label"] == "MAD -> DUB"
    assert alert_item["action_href"].startswith("/notifications?view=rules&watch_id=")
    assert alert_item["is_read"] is False
    hotel_item = next(item for item in body["items"] if item["source_id"] == hotel_source_id)
    assert hotel_item["source_type"] == "hotel_alert_event"
    assert hotel_item["category"] == "price"
    assert hotel_item["route_label"] == "Madrid, ES"

    mark = client.post(f"/api/v1/notifications/alert_event/{alert_source_id}/read", headers=headers)
    assert mark.status_code == 200
    mark_hotel = client.post(f"/api/v1/notifications/hotel_alert_event/{hotel_source_id}/read", headers=headers)
    assert mark_hotel.status_code == 200

    updated = client.get("/api/v1/notifications", headers=headers).json()
    updated_alert = next(item for item in updated["items"] if item["source_id"] == alert_source_id)
    assert updated_alert["is_read"] is True
    assert updated_alert["read_at"] is not None

    read_all = client.post("/api/v1/notifications/read-all", headers=headers)
    assert read_all.status_code == 200
    assert read_all.json()["updated"] >= 1
    final = client.get("/api/v1/notifications", headers=headers).json()
    assert final["summary"]["unread"] == 0

    delete_account = client.delete("/api/v1/account", headers=headers)
    assert delete_account.status_code == 200
    db, generator = _open_test_db_session()
    try:
        states = db.scalars(select(UserNotificationState).where(UserNotificationState.user_id == user_id)).all()
        assert states == []
    finally:
        _close_test_db_session(generator)
