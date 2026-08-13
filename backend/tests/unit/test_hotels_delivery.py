from __future__ import annotations

from datetime import timedelta

from sqlalchemy import create_engine, select

from app.infrastructure.db.models import HotelDailyMetric
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelAlertEvent,
    HotelAlertRule,
    HotelNotificationDelivery,
    HotelProperty,
    HotelProviderRun,
    User,
)
from app.services.hotels_service import (
    create_hotel_delivery_intent,
    materialize_hotel_delivery_intents,
)
from app.services.notification_service import (
    HotelDeliveryAdapter,
    dispatch_pending_hotel_deliveries,
)
from app.core.time import utc_now_naive


class _FailingHotelAdapter(HotelDeliveryAdapter):
    def send(self, delivery: HotelNotificationDelivery) -> tuple[bool, str | None, str | None]:
        return False, "provider_timeout", "retryable"


class _PermanentHotelAdapter(HotelDeliveryAdapter):
    def send(self, delivery: HotelNotificationDelivery) -> tuple[bool, str | None, str | None]:
        return False, "user_opted_out", "permanent"


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    db._test_engine = engine  # type: ignore[attr-defined]
    return db


def _close(db: Session) -> None:
    engine = db._test_engine  # type: ignore[attr-defined]
    db.close()
    engine.dispose()


def _fixture(db: Session) -> tuple[User, User, HotelAlertEvent, HotelAlertEvent, HotelAlertEvent]:
    user_a = User(email="delivery-a@viru.dev", password_hash="-")
    user_b = User(email="delivery-b@viru.dev", password_hash="-")
    hotel = HotelProperty(
        canonical_name="Hotel Delivery",
        normalized_name="hotel delivery",
        city="Madrid",
        normalized_city="madrid",
        country_code="ES",
    )
    db.add_all([user_a, user_b, hotel])
    db.flush()
    rule_a = HotelAlertRule(user_id=user_a.id, hotel_id=hotel.id, rule_type="price_below", is_active=True)
    rule_b = HotelAlertRule(user_id=user_b.id, hotel_id=hotel.id, rule_type="price_below", is_active=True)
    run = HotelProviderRun(provider="mock", status="completed")
    db.add_all([rule_a, rule_b, run])
    db.flush()
    owned = HotelAlertEvent(
        user_id=user_a.id,
        rule_id=rule_a.id,
        hotel_id=hotel.id,
        provider_run_id=run.id,
        event_type="price_below",
        message="bajó",
    )
    foreign = HotelAlertEvent(
        user_id=user_b.id,
        rule_id=rule_b.id,
        hotel_id=hotel.id,
        provider_run_id=run.id,
        event_type="price_below",
        message="bajó",
    )
    orphan = HotelAlertEvent(
        user_id=None,
        rule_id=None,
        hotel_id=hotel.id,
        provider_run_id=run.id,
        event_type="price_below",
        message="huérfano",
    )
    db.add_all([owned, foreign, orphan])
    db.commit()
    return user_a, user_b, owned, foreign, orphan


def test_create_hotel_delivery_intent_requires_event_ownership() -> None:
    db = _db()
    try:
        user_a, user_b, owned, foreign, orphan = _fixture(db)
        delivery = create_hotel_delivery_intent(db, event_id=owned.id, user_id=user_a.id)
        assert delivery.recipient_user_id == user_a.id
        assert delivery.source_event_id == owned.id
        assert delivery.channel == "in_app"
        assert delivery.status == "queued"

        assert create_hotel_delivery_intent(db, event_id=foreign.id, user_id=user_a.id) is None
        assert create_hotel_delivery_intent(db, event_id=orphan.id, user_id=user_a.id) is None

        tracking_event = HotelAlertEvent(
            user_id=user_a.id,
            rule_id=None,
            hotel_id=owned.hotel_id,
            provider_run_id=owned.provider_run_id,
            event_type="price_below",
            message="tracking event",
        )
        db.add(tracking_event)
        db.flush()
        tracking_delivery = create_hotel_delivery_intent(
            db,
            event_id=tracking_event.id,
            user_id=user_a.id,
        )
        assert tracking_delivery is not None
    finally:
        _close(db)


def test_hotel_delivery_retry_then_terminal_failure() -> None:
    db = _db()
    try:
        user_a, _, owned, _, _ = _fixture(db)
        delivery = create_hotel_delivery_intent(db, event_id=owned.id, user_id=user_a.id)
        assert delivery is not None
        db.commit()

        first = dispatch_pending_hotel_deliveries(
            db,
            limit=10,
            adapter=_FailingHotelAdapter(),
        )
        assert first.hotel_processed == 1
        assert first.hotel_retried == 1
        assert first.hotel_failed == 0
        db.refresh(delivery)
        assert delivery.status == "queued"
        assert delivery.attempts == 1
        assert delivery.next_attempt_at is not None
        assert delivery.last_error == "provider_timeout"
        metric = db.scalar(
            select(HotelDailyMetric).where(
                HotelDailyMetric.metric_name == "hotel_delivery",
                HotelDailyMetric.outcome == "retried",
            )
        )
        assert metric is not None and metric.count == 1

        # Simulate the backoff window elapsing for the next two attempts.
        delivery.next_attempt_at = None
        db.commit()
        second = dispatch_pending_hotel_deliveries(
            db,
            limit=10,
            adapter=_FailingHotelAdapter(),
        )
        assert second.hotel_retried == 1
        db.refresh(delivery)
        assert delivery.attempts == 2

        delivery.next_attempt_at = None
        db.commit()
        third = dispatch_pending_hotel_deliveries(
            db,
            limit=10,
            adapter=_FailingHotelAdapter(),
        )
        assert third.hotel_failed == 1
        db.refresh(delivery)
        assert delivery.status == "failed"
        assert delivery.attempts == 3
        assert delivery.next_attempt_at is None
    finally:
        _close(db)


def test_materialize_hotel_delivery_intents_is_idempotent_and_counts_only_new_rows() -> None:
    db = _db()
    try:
        user_a, _, owned, foreign, orphan = _fixture(db)
        assert materialize_hotel_delivery_intents(db, provider_run_id=owned.provider_run_id) == 2
        assert materialize_hotel_delivery_intents(db, provider_run_id=owned.provider_run_id) == 0
        rows = list(db.scalars(select(HotelNotificationDelivery)))
        assert {row.source_event_id for row in rows} == {owned.id, foreign.id}
        assert orphan.id not in {row.source_event_id for row in rows}
    finally:
        _close(db)


def test_hotel_delivery_permanent_failure_is_not_retried() -> None:
    db = _db()
    try:
        user_a, _, owned, _, _ = _fixture(db)
        delivery = create_hotel_delivery_intent(db, event_id=owned.id, user_id=user_a.id)
        assert delivery is not None
        db.commit()

        result = dispatch_pending_hotel_deliveries(
            db,
            limit=10,
            adapter=_PermanentHotelAdapter(),
        )
        assert result.hotel_processed == 1
        assert result.hotel_failed == 1
        assert result.hotel_retried == 0
        db.refresh(delivery)
        assert delivery.status == "failed"
        assert delivery.attempts == 1
        assert delivery.next_attempt_at is None
        assert delivery.error_class == "permanent"
        assert delivery.last_error == "user_opted_out"
        metric = db.scalar(
            select(HotelDailyMetric).where(
                HotelDailyMetric.metric_name == "hotel_delivery",
                HotelDailyMetric.outcome == "failed",
            )
        )
        assert metric is not None and metric.count == 1
    finally:
        _close(db)


def test_hotel_delivery_waits_until_its_persisted_next_attempt() -> None:
    db = _db()
    try:
        user_a, _, owned, _, _ = _fixture(db)
        delivery = create_hotel_delivery_intent(db, event_id=owned.id, user_id=user_a.id)
        assert delivery is not None
        delivery.next_attempt_at = utc_now_naive() + timedelta(minutes=5)
        db.commit()

        result = dispatch_pending_hotel_deliveries(db, limit=10)

        assert result.hotel_processed == 0
        db.refresh(delivery)
        assert delivery.status == "queued"
        assert delivery.attempts == 0
    finally:
        _close(db)


def test_create_hotel_delivery_intent_is_idempotent() -> None:
    db = _db()
    try:
        user_a, _, owned, _, _ = _fixture(db)
        first = create_hotel_delivery_intent(db, event_id=owned.id, user_id=user_a.id)
        second = create_hotel_delivery_intent(db, event_id=owned.id, user_id=user_a.id)
        assert first is not None and second is not None
        assert first.id == second.id
        assert db.scalar(select(HotelNotificationDelivery.id)) == first.id
    finally:
        _close(db)
