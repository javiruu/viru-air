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
    NotificationEvent,
    SecurityActivity,
    User,
    UserNotificationState,
)
from app.main import app
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
