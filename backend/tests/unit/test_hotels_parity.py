from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.hotels.parity import HotelParityService, ParitySignal
from app.infrastructure.db.models import Base, HotelRateSnapshot


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def _close(db: Session) -> None:
    engine = db._test_engine  # type: ignore[attr-defined]
    db.close()
    engine.dispose()


def _rate(
    provider: str,
    amount: float,
    check_in: datetime.date | None = None,
    check_out: datetime.date | None = None,
    guests: int = 2,
    currency: str = "EUR",
) -> HotelRateSnapshot:
    return HotelRateSnapshot(
        hotel_id="h1",
        provider=provider,
        check_in=check_in or datetime.date(2026, 7, 10),
        check_out=check_out or datetime.date(2026, 7, 12),
        guests=guests,
        currency=currency,
        amount=amount,
    )


def test_parity_single_provider_returns_limited() -> None:
    db = _db()
    try:
        signals = HotelParityService.compute_parity([
            _rate("mock", 100),
            _rate("mock", 110),
        ])
        assert len(signals) == 1
        assert signals[0].provider_count == 1
        assert signals[0].status == "info"
        assert signals[0].label == "limited"
        assert signals[0].is_parity_broken is False
        assert signals[0].lowest_price is None
        assert signals[0].spread_amount is None
    finally:
        _close(db)


def test_parity_two_providers_stable_spread_below_10_pct() -> None:
    db = _db()
    try:
        signals = HotelParityService.compute_parity([
            _rate("mock", 100),
            _rate("mock2", 105),
        ])
        assert len(signals) == 1
        assert signals[0].provider_count == 2
        assert signals[0].status == "success"
        assert signals[0].label == "stable"
        assert signals[0].is_parity_broken is False
        assert signals[0].lowest_price == 100
        assert signals[0].highest_price == 105
        assert signals[0].spread_amount == 5
        assert signals[0].spread_percent == 5.0
    finally:
        _close(db)


def test_parity_spread_between_10_and_20_pct_returns_warning() -> None:
    db = _db()
    try:
        signals = HotelParityService.compute_parity([
            _rate("m1", 100),
            _rate("m2", 115),
        ])
        assert signals[0].status == "warning"
        assert signals[0].label == "tensioned"
        assert signals[0].is_parity_broken is True
        assert signals[0].spread_percent == 15.0
    finally:
        _close(db)


def test_parity_spread_above_20_pct_returns_error() -> None:
    db = _db()
    try:
        signals = HotelParityService.compute_parity([
            _rate("m1", 100),
            _rate("m2", 125),
        ])
        assert signals[0].status == "error"
        assert signals[0].label == "breach"
        assert signals[0].is_parity_broken is True
        assert signals[0].spread_percent == 25.0
    finally:
        _close(db)


def test_parity_groups_rates_by_stay_parameters() -> None:
    db = _db()
    try:
        signals = HotelParityService.compute_parity([
            _rate("m1", 100, check_in=datetime.date(2026, 7, 10), guests=2),
            _rate("m2", 120, check_in=datetime.date(2026, 7, 10), guests=2),
            _rate("m1", 200, check_in=datetime.date(2026, 8, 1), guests=2),
            _rate("m2", 210, check_in=datetime.date(2026, 8, 1), guests=2),
        ])
        # Two separate groups: one for July stay, one for August stay
        assert len(signals) == 2
        july = next(s for s in signals if s.check_in == datetime.date(2026, 7, 10))
        august = next(s for s in signals if s.check_in == datetime.date(2026, 8, 1))
        assert july.provider_count == 2
        assert august.provider_count == 2
        assert july.spread_percent is not None
        assert august.spread_percent is not None
    finally:
        _close(db)


def test_parity_different_guests_are_separate_groups() -> None:
    db = _db()
    try:
        signals = HotelParityService.compute_parity([
            _rate("m1", 100, guests=1),
            _rate("m2", 110, guests=1),
            _rate("m1", 150, guests=2),
            _rate("m2", 160, guests=2),
        ])
        assert len(signals) == 2
    finally:
        _close(db)


def test_parity_empty_rates_returns_empty() -> None:
    db = _db()
    try:
        signals = HotelParityService.compute_parity([])
        assert signals == []
    finally:
        _close(db)


def test_latest_parity_returns_most_recent() -> None:
    db = _db()
    try:
        signal = HotelParityService.latest_parity([
            _rate("m1", 80, check_in=datetime.date(2026, 6, 1)),
            _rate("m2", 85, check_in=datetime.date(2026, 6, 1)),
            _rate("m1", 100, check_in=datetime.date(2026, 7, 10)),
            _rate("m2", 105, check_in=datetime.date(2026, 7, 10)),
        ])
        assert signal is not None
        assert signal.check_in == datetime.date(2026, 7, 10)
        assert signal.lowest_price == 100
        assert signal.spread_percent == 5.0
    finally:
        _close(db)


def test_latest_parity_empty_returns_none() -> None:
    db = _db()
    try:
        assert HotelParityService.latest_parity([]) is None
    finally:
        _close(db)
