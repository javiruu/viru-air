"""Unit tests for hotel alert evaluation logic."""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelAlertEvent,
    HotelAlertRule,
    HotelProperty,
    HotelProviderRun,
    HotelRateSnapshot,
)
from app.services.hotels_service import evaluate_hotel_alerts, run_hotel_sweep


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


def _make_rule(db: Session, *, user_id: str, hotel_id: str, rule_type: str, threshold_amount=None, threshold_percent=None) -> HotelAlertRule:
    rule = HotelAlertRule(
        user_id=user_id,
        hotel_id=hotel_id,
        rule_type=rule_type,
        threshold_amount=threshold_amount,
        threshold_percent=threshold_percent,
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

    def test_sweep_is_idempotent(self, db: Session):
        first = run_hotel_sweep(db, provider="mock")
        second = run_hotel_sweep(db, provider="mock")

        assert first.status == "completed"
        assert second.status == "completed"
