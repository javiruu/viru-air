"""Unit tests for hotel alert evaluation logic."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelAlertRule,
    HotelProperty,
    HotelRateSnapshot,
    HotelTrackedOffer,
    HotelAlertEvent,
)
from app.services.hotels_service import evaluate_hotel_alerts, run_hotel_sweep


@pytest.fixture(autouse=True)
def _enable_hotels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_hotel(db: Session, **kwargs) -> HotelProperty:
    hotel = HotelProperty(
        canonical_name=kwargs.get("canonical_name", "Test Hotel"),
        normalized_name=kwargs.get("normalized_name", "test hotel"),
        city=kwargs.get("city", "Madrid"),
        country_code=kwargs.get("country_code", "ES"),
        stars=kwargs.get("stars", 4),
    )
    db.add(hotel)
    db.flush()
    return hotel


def _make_rule(
    db: Session,
    *,
    user_id: str,
    hotel_id: str,
    rule_type: str,
    threshold_amount=None,
    threshold_percent=None,
    tracked_offer_id: str | None = None,
    compare_against: str = "snapshot_previous",
) -> HotelAlertRule:
    rule = HotelAlertRule(
        user_id=user_id,
        hotel_id=hotel_id,
        rule_type=rule_type,
        threshold_amount=threshold_amount,
        threshold_percent=threshold_percent,
        tracked_offer_id=tracked_offer_id,
        compare_against=compare_against,
        is_active=True,
    )
    db.add(rule)
    db.flush()
    return rule


def _make_rate(db: Session, *, hotel_id: str, provider: str, amount: float, currency: str = "EUR", check_in=None, check_out=None, guests=2) -> HotelRateSnapshot:
    rate = HotelRateSnapshot(
        hotel_id=hotel_id,
        provider=provider,
        check_in=check_in or date(2026, 7, 1),
        check_out=check_out or date(2026, 7, 3),
        guests=guests,
        currency=currency,
        amount=amount,
    )
    db.add(rate)
    db.flush()
    return rate


class TestEvaluateHotelAlerts:
    def test_percentage_drop_can_compare_against_initial_price(self, db: Session):
        hotel = _make_hotel(db)
        offer = HotelTrackedOffer(
            user_id="u-initial",
            hotel_id=hotel.id,
            provider="mock",
            initial_price=200,
            current_price=150,
            currency="EUR",
            is_active=True,
        )
        db.add(offer)
        db.flush()
        rule = _make_rule(
            db,
            user_id="u-initial",
            hotel_id=hotel.id,
            rule_type="percentage_drop",
            threshold_percent=20,
            tracked_offer_id=offer.id,
            compare_against="initial_price",
        )
        _make_rate(db, hotel_id=hotel.id, provider="mock", amount=190)
        latest = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=150)
        latest.tracked_offer_id = offer.id
        previous = db.query(HotelRateSnapshot).filter(HotelRateSnapshot.id != latest.id).one()
        previous.tracked_offer_id = offer.id
        db.flush()

        events = evaluate_hotel_alerts(db, provider_run_id="run-initial-price")

        matching = [event for event in events if event.rule_id == rule.id and event.event_type == "percentage_drop"]
        assert len(matching) == 1
        assert matching[0].trigger_value == pytest.approx(25.0)

    def test_tracked_price_below_percent_uses_snapshot_baseline(self, db: Session):
        hotel = _make_hotel(db)
        offer = HotelTrackedOffer(
            user_id="u-price-below-percent",
            hotel_id=hotel.id,
            provider="mock",
            initial_price=200,
            current_price=150,
            currency="EUR",
            is_active=True,
        )
        db.add(offer)
        db.flush()
        rule = _make_rule(
            db,
            user_id="u-price-below-percent",
            hotel_id=hotel.id,
            rule_type="price_below",
            threshold_percent=20,
            tracked_offer_id=offer.id,
            compare_against="initial_price",
        )
        previous = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=190)
        previous.tracked_offer_id = offer.id
        previous.collected_at = datetime(2026, 7, 1, 12, 0, 0)
        latest = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=150)
        latest.tracked_offer_id = offer.id
        latest.collected_at = previous.collected_at + timedelta(minutes=1)
        db.flush()

        events = evaluate_hotel_alerts(db, provider_run_id="run-price-below-percent")

        matching = [event for event in events if event.rule_id == rule.id and event.event_type == "price_below"]
        assert len(matching) == 1
        assert matching[0].trigger_value == 150

    def test_tracked_price_above_percent_uses_snapshot_baseline(self, db: Session):
        hotel = _make_hotel(db)
        offer = HotelTrackedOffer(
            user_id="u-price-above-percent",
            hotel_id=hotel.id,
            provider="mock",
            initial_price=100,
            current_price=125,
            currency="EUR",
            is_active=True,
        )
        db.add(offer)
        db.flush()
        rule = _make_rule(
            db,
            user_id="u-price-above-percent",
            hotel_id=hotel.id,
            rule_type="price_above",
            threshold_percent=20,
            tracked_offer_id=offer.id,
            compare_against="initial_price",
        )
        previous = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=110)
        previous.tracked_offer_id = offer.id
        previous.collected_at = datetime(2026, 7, 1, 12, 0, 0)
        latest = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=125)
        latest.tracked_offer_id = offer.id
        latest.collected_at = previous.collected_at + timedelta(minutes=1)
        db.flush()

        events = evaluate_hotel_alerts(db, provider_run_id="run-price-above-percent")

        matching = [event for event in events if event.rule_id == rule.id and event.event_type == "price_above"]
        assert len(matching) == 1
        assert matching[0].trigger_value == 125

    def test_tracked_price_below_percent_uses_previous_snapshot_by_default(self, db: Session):
        hotel = _make_hotel(db)
        offer = HotelTrackedOffer(
            user_id="u-price-below-previous",
            hotel_id=hotel.id,
            provider="mock",
            initial_price=300,
            current_price=150,
            currency="EUR",
            is_active=True,
        )
        db.add(offer)
        db.flush()
        rule = _make_rule(
            db,
            user_id="u-price-below-previous",
            hotel_id=hotel.id,
            rule_type="price_below",
            threshold_percent=20,
            tracked_offer_id=offer.id,
        )
        previous = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=200)
        previous.tracked_offer_id = offer.id
        previous.collected_at = datetime(2026, 7, 1, 12, 0, 0)
        latest = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=150)
        latest.tracked_offer_id = offer.id
        latest.collected_at = previous.collected_at + timedelta(minutes=1)
        db.flush()

        events = evaluate_hotel_alerts(db, provider_run_id="run-price-below-previous")

        matching = [event for event in events if event.rule_id == rule.id and event.event_type == "price_below"]
        assert len(matching) == 1
        assert matching[0].trigger_value == 150

    def test_condition_held_is_suppressed_and_rearms_after_clear(self, db: Session):
        hotel = _make_hotel(db)
        rule = _make_rule(db, user_id="u-dedupe", hotel_id=hotel.id, rule_type="price_below", threshold_amount=100)
        first_rate = _make_rate(db, hotel_id=hotel.id, provider="p1", amount=80)
        first_rate.collected_at = datetime(2026, 7, 1, 12, 0, 0)
        db.flush()

        first = evaluate_hotel_alerts(db, provider_run_id="run-dedupe-1")
        assert len([event for event in first if event.rule_id == rule.id]) == 1
        assert rule.evaluation_state == "fired"
        assert first[0].event_fingerprint

        second = evaluate_hotel_alerts(db, provider_run_id="run-dedupe-2")
        assert len([event for event in second if event.rule_id == rule.id]) == 0
        assert rule.evaluation_state == "suppressed"

        # The legacy hotel-scope evaluator only knows current eligible rates;
        # expire the previous observation before introducing the clear state.
        first_rate.availability_status = "stale"
        clear_rate = _make_rate(db, hotel_id=hotel.id, provider="p1", amount=120)
        clear_rate.collected_at = datetime(2026, 7, 1, 12, 1, 0)
        db.flush()
        evaluate_hotel_alerts(db, provider_run_id="run-dedupe-clear")
        assert rule.evaluation_state == "rearmed"

        rearmed_rate = _make_rate(db, hotel_id=hotel.id, provider="p1", amount=75)
        rearmed_rate.collected_at = datetime(2026, 7, 1, 12, 2, 0)
        db.flush()
        third = evaluate_hotel_alerts(db, provider_run_id="run-dedupe-3")
        assert len([event for event in third if event.rule_id == rule.id]) == 1
        assert db.query(HotelAlertEvent).filter(HotelAlertEvent.rule_id == rule.id).count() == 2

    def test_initial_price_metadata_uses_offer_baseline_without_snapshot_identity(self, db: Session):
        hotel = _make_hotel(db)
        offer = HotelTrackedOffer(
            user_id="u-baseline-meta",
            hotel_id=hotel.id,
            provider="mock",
            initial_price=200,
            current_price=150,
            currency="EUR",
            is_active=True,
        )
        db.add(offer)
        db.flush()
        rule = _make_rule(
            db,
            user_id="u-baseline-meta",
            hotel_id=hotel.id,
            rule_type="percentage_drop",
            threshold_percent=20,
            tracked_offer_id=offer.id,
            compare_against="initial_price",
        )
        latest = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=150)
        latest.tracked_offer_id = offer.id
        latest.collected_at = datetime(2026, 7, 1, 12, 1, 0)
        db.flush()

        events = evaluate_hotel_alerts(db, provider_run_id="run-baseline-meta")
        event = next(event for event in events if event.rule_id == rule.id)
        assert event.baseline_snapshot_id is None
        assert event.baseline_source == "initial_price"
        assert event.baseline_amount == pytest.approx(200)
        assert event.baseline_currency == "EUR"

    def test_stale_tracked_snapshot_is_not_a_comparable_baseline(self, db: Session):
        hotel = _make_hotel(db)
        offer = HotelTrackedOffer(
            user_id="u-stale",
            hotel_id=hotel.id,
            provider="mock",
            initial_price=200,
            current_price=100,
            currency="EUR",
            is_active=True,
        )
        db.add(offer)
        db.flush()
        rule = _make_rule(
            db,
            user_id="u-stale",
            hotel_id=hotel.id,
            rule_type="percentage_drop",
            threshold_percent=20,
            tracked_offer_id=offer.id,
        )
        stale = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=200)
        stale.tracked_offer_id = offer.id
        stale.availability_status = "stale"
        stale.collected_at = datetime(2026, 7, 1, 12, 0, 0)
        latest = _make_rate(db, hotel_id=hotel.id, provider="mock", amount=100)
        latest.tracked_offer_id = offer.id
        latest.collected_at = datetime(2026, 7, 1, 12, 1, 0)
        db.flush()

        events = evaluate_hotel_alerts(db, provider_run_id="run-stale")
        assert [event for event in events if event.rule_id == rule.id] == []

    def test_price_below_threshold_amount_triggers(self, db: Session):
        hotel = _make_hotel(db)
        rule = _make_rule(db, user_id="u1", hotel_id=hotel.id, rule_type="price_below", threshold_amount=100)
        _make_rate(db, hotel_id=hotel.id, provider="p1", amount=80)

        events = evaluate_hotel_alerts(db, provider_run_id="run-1")
        assert len(events) >= 1
        price_below_events = [e for e in events if e.rule_id == rule.id and e.event_type == "price_below"]
        assert len(price_below_events) == 1
        assert price_below_events[0].trigger_value == 80

    def test_price_below_not_triggered_if_above_threshold(self, db: Session):
        hotel = _make_hotel(db)
        _make_rule(db, user_id="u1", hotel_id=hotel.id, rule_type="price_below", threshold_amount=100)
        _make_rate(db, hotel_id=hotel.id, provider="p1", amount=120)

        events = evaluate_hotel_alerts(db, provider_run_id="run-2")
        price_below_events = [e for e in events if e.event_type == "price_below"]
        assert len(price_below_events) == 0

    def test_price_above_threshold_amount_triggers(self, db: Session):
        hotel = _make_hotel(db)
        rule = _make_rule(db, user_id="u1", hotel_id=hotel.id, rule_type="price_above", threshold_amount=150)
        _make_rate(db, hotel_id=hotel.id, provider="p1", amount=200)

        events = evaluate_hotel_alerts(db, provider_run_id="run-3")
        price_above_events = [e for e in events if e.rule_id == rule.id and e.event_type == "price_above"]
        assert len(price_above_events) == 1
        assert price_above_events[0].trigger_value == 200

    def test_price_above_not_triggered_if_below_threshold(self, db: Session):
        hotel = _make_hotel(db)
        _make_rule(db, user_id="u1", hotel_id=hotel.id, rule_type="price_above", threshold_amount=150)
        _make_rate(db, hotel_id=hotel.id, provider="p1", amount=100)

        events = evaluate_hotel_alerts(db, provider_run_id="run-4")
        price_above_events = [e for e in events if e.event_type == "price_above"]
        assert len(price_above_events) == 0

    def test_price_below_threshold_percent_triggers(self, db: Session):
        hotel = _make_hotel(db)
        rule = _make_rule(db, user_id="u1", hotel_id=hotel.id, rule_type="price_below", threshold_percent=20)
        _make_rate(db, hotel_id=hotel.id, provider="p1", amount=200)
        _make_rate(db, hotel_id=hotel.id, provider="p2", amount=50)

        events = evaluate_hotel_alerts(db, provider_run_id="run-5")
        price_below_events = [e for e in events if e.rule_id == rule.id]
        assert len(price_below_events) == 1
        assert price_below_events[0].trigger_value == 50

    def test_parity_break_triggers_with_spread(self, db: Session):
        hotel = _make_hotel(db)
        rule = _make_rule(db, user_id="u1", hotel_id=hotel.id, rule_type="parity_break", threshold_percent=10)
        _make_rate(db, hotel_id=hotel.id, provider="p1", amount=100, check_in=date(2026, 7, 1))
        _make_rate(db, hotel_id=hotel.id, provider="p2", amount=130, check_in=date(2026, 7, 1))

        events = evaluate_hotel_alerts(db, provider_run_id="run-6")
        parity_events = [e for e in events if e.rule_id == rule.id and e.event_type == "parity_break"]
        assert len(parity_events) == 1
        assert parity_events[0].trigger_value >= 10

    def test_parity_break_not_triggered_if_under_threshold(self, db: Session):
        hotel = _make_hotel(db)
        _make_rule(db, user_id="u1", hotel_id=hotel.id, rule_type="parity_break", threshold_percent=90)
        _make_rate(db, hotel_id=hotel.id, provider="p1", amount=100, check_in=date(2026, 7, 1))
        _make_rate(db, hotel_id=hotel.id, provider="p2", amount=105, check_in=date(2026, 7, 1))

        events = evaluate_hotel_alerts(db, provider_run_id="run-7")
        parity_events = [e for e in events if e.event_type == "parity_break"]
        assert len(parity_events) == 0

    def test_inactive_rule_is_skipped(self, db: Session):
        hotel = _make_hotel(db)
        rule = _make_rule(db, user_id="u1", hotel_id=hotel.id, rule_type="price_below", threshold_amount=100)
        rule.is_active = False
        db.flush()
        _make_rate(db, hotel_id=hotel.id, provider="p1", amount=80)

        events = evaluate_hotel_alerts(db, provider_run_id="run-8")
        price_below_events = [e for e in events if e.rule_id == rule.id]
        assert len(price_below_events) == 0

    def test_no_rates_produces_no_events(self, db: Session):
        hotel = _make_hotel(db)
        _make_rule(db, user_id="u1", hotel_id=hotel.id, rule_type="price_below", threshold_amount=100)

        events = evaluate_hotel_alerts(db, provider_run_id="run-9")
        assert len(events) == 0


class TestRunHotelSweep:
    def test_sweep_creates_provider_run_and_completes(self, db: Session):
        provider_run = run_hotel_sweep(db, provider="mock")

        assert provider_run.id is not None
        assert provider_run.provider == "mock"
        assert provider_run.status == "completed"
        assert provider_run.finished_at is not None
        assert provider_run.tracked_outcomes is not None
        assert provider_run.tracked_outcomes["offers_scanned"] == 0
        assert provider_run.tracked_outcomes["snapshots_created"] == 0
        assert provider_run.status == "completed"

    def test_sweep_is_idempotent(self, db: Session):
        first = run_hotel_sweep(db, provider="mock")
        second = run_hotel_sweep(db, provider="mock")

        assert first.status == "completed"
        assert second.status == "completed"
        assert first.tracked_outcomes is not None
        assert second.tracked_outcomes is not None
        assert first.tracked_outcomes["provider_fetch_attempted"] == 0
        assert second.tracked_outcomes["provider_fetch_attempted"] == 0
