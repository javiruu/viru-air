from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelAlertEvent,
    HotelAlertRule,
    HotelNotificationDelivery,
    HotelProperty,
    HotelProviderRun,
    HotelRateSnapshot,
    HotelTrackedOffer,
    HotelTrackedOfferLifecycleEvent,
    User,
)
from app.services.hotels_service import (
    create_hotel_delivery_intent,
    evaluate_hotel_alerts,
    expire_due_tracked_offers,
    materialize_hotel_delivery_intents,
    transition_tracked_offer_lifecycle,
)


def _db() -> tuple[Session, Engine]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)(), engine


def _seed_tracking(db: Session) -> tuple[User, HotelProperty, HotelTrackedOffer]:
    user = User(email="tracking-lifecycle@viru.dev", password_hash="hash")
    hotel = HotelProperty(
        canonical_name="Hotel Lifecycle",
        normalized_name="hotel lifecycle",
        city="Madrid",
        normalized_city="madrid",
        country_code="ES",
    )
    db.add_all([user, hotel])
    db.flush()
    offer = HotelTrackedOffer(
        user_id=user.id,
        hotel_id=hotel.id,
        provider="mock",
        check_in=date(2026, 8, 20),
        check_out=date(2026, 8, 22),
        guests=2,
        currency="EUR",
        is_active=True,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return user, hotel, offer


def test_lifecycle_records_owned_versioned_transitions_and_expires_due_tracking() -> None:
    db, engine = _db()
    try:
        user, _, offer = _seed_tracking(db)
        paused = transition_tracked_offer_lifecycle(
            db,
            user_id=user.id,
            tracked_offer_id=offer.id,
            action="pause",
            expected_state_version=1,
            today=date(2026, 8, 1),
        )
        assert paused.offer.lifecycle_state == "paused"
        assert paused.offer.lifecycle_version == 2
        assert paused.offer.is_active is False
        event = db.scalar(select(HotelTrackedOfferLifecycleEvent))
        assert event is not None
        assert (event.from_state, event.to_state, event.action, event.state_version) == ("active", "paused", "pause", 2)

        resumed = transition_tracked_offer_lifecycle(
            db,
            user_id=user.id,
            tracked_offer_id=offer.id,
            action="resume",
            expected_state_version=2,
            today=date(2026, 8, 1),
        )
        assert resumed.offer.lifecycle_state == "active"
        assert resumed.offer.lifecycle_version == 3
        assert expire_due_tracked_offers(db, today=date(2026, 8, 23)) == 1
        expired = db.get(HotelTrackedOffer, offer.id)
        assert expired is not None
        assert (expired.lifecycle_state, expired.lifecycle_version, expired.is_active) == ("expired", 4, False)
    finally:
        db.close()
        engine.dispose()


def test_paused_tracking_suppresses_pending_delivery_and_new_alert_work() -> None:
    db, engine = _db()
    try:
        user, hotel, offer = _seed_tracking(db)
        rule = HotelAlertRule(
            user_id=user.id,
            hotel_id=hotel.id,
            tracked_offer_id=offer.id,
            rule_type="price_below",
            threshold_amount=200,
            is_active=True,
        )
        run = HotelProviderRun(provider="mock", status="completed")
        db.add_all([rule, run])
        db.flush()
        snapshot = HotelRateSnapshot(
            hotel_id=hotel.id,
            tracked_offer_id=offer.id,
            provider="mock",
            check_in=offer.check_in,
            check_out=offer.check_out,
            guests=2,
            currency="EUR",
            amount=150,
        )
        event = HotelAlertEvent(
            user_id=user.id,
            rule_id=rule.id,
            hotel_id=hotel.id,
            provider_run_id=run.id,
            event_type="price_below",
            message="Hotel Lifecycle: bajó",
        )
        db.add_all([snapshot, event])
        db.flush()
        delivery = create_hotel_delivery_intent(db, event_id=event.id, user_id=user.id)
        assert delivery is not None
        db.commit()

        transition_tracked_offer_lifecycle(
            db,
            user_id=user.id,
            tracked_offer_id=offer.id,
            action="pause",
            expected_state_version=1,
            today=date(2026, 8, 1),
        )
        suppressed = db.get(HotelNotificationDelivery, delivery.id)
        assert suppressed is not None
        assert suppressed.status == "suppressed"
        assert evaluate_hotel_alerts(db, provider_run_id=run.id) == []

        later_event = HotelAlertEvent(
            user_id=user.id,
            rule_id=rule.id,
            hotel_id=hotel.id,
            provider_run_id=run.id,
            event_type="price_below",
            message="Hotel Lifecycle: sigue bajo",
        )
        db.add(later_event)
        db.flush()
        assert materialize_hotel_delivery_intents(db, provider_run_id=run.id) == 0
    finally:
        db.close()
        engine.dispose()


def test_archived_tracking_is_not_reactivated_by_expiration_reconciliation() -> None:
    db, engine = _db()
    try:
        user, _, offer = _seed_tracking(db)
        archived = transition_tracked_offer_lifecycle(
            db,
            user_id=user.id,
            tracked_offer_id=offer.id,
            action="archive",
            expected_state_version=1,
            today=date(2026, 8, 1),
        )
        assert archived.offer.lifecycle_state == "archived"
        assert archived.offer.is_active is False
        assert expire_due_tracked_offers(db, today=date(2026, 8, 23)) == 0
        persisted = db.get(HotelTrackedOffer, offer.id)
        assert persisted is not None
        assert (persisted.lifecycle_state, persisted.lifecycle_version) == ("archived", 2)
    finally:
        db.close()
        engine.dispose()
