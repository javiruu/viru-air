import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities import ProviderFlight
from app.infrastructure.db.models import Base, FlightOfferCacheEntry, FlightPriceObservation
from app.services.fare_memory_provider_observations import (
    ObservationPersistenceContext,
    ProviderFlightRow,
    persist_provider_flight_observations,
)


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


def test_provider_observations_persist_all_raw_results_before_visible_limit(db: Session) -> None:
    travel_date = dt.date(2026, 7, 20)
    provider_rows = [
        _provider_row(travel_date=travel_date, departure_time_local=f"0{hour}:15", price=40.0 + hour)
        for hour in range(5)
    ]
    visible_results = provider_rows[:2]

    summary = persist_provider_flight_observations(
        db,
        provider_flights=provider_rows,
        context=_context(),
    )

    offers = db.scalars(select(FlightOfferCacheEntry)).all()
    observations = db.scalars(select(FlightPriceObservation)).all()
    assert len(visible_results) == 2
    assert summary["offers_created"] == 5
    assert summary["observations_created"] == 5
    assert len(offers) == 5
    assert len(observations) == 5
    flight_instance_fingerprints = {offer.flight_instance_fingerprint for offer in offers}
    assert None not in flight_instance_fingerprints
    assert len(flight_instance_fingerprints) == 5


def test_provider_observations_skip_incomplete_provider_rows(db: Session) -> None:
    travel_date = dt.date(2026, 7, 20)
    rows = [
        _provider_row(travel_date=travel_date, source=""),
        ("LE", "FCO", travel_date, _flight(source="ryanair")),
        _provider_row(travel_date=travel_date, source="ryanair"),
    ]

    summary = persist_provider_flight_observations(
        db,
        provider_flights=rows,
        context=_context(),
    )

    assert summary["offers_created"] == 1
    assert summary["observations_created"] == 1
    assert summary["skipped_incomplete"] == 2
    price_amount = db.scalar(select(FlightPriceObservation.price_amount))
    assert price_amount is not None
    assert float(price_amount) == pytest.approx(49.99)


def test_provider_observations_skip_same_price_seen_again_within_short_window(db: Session) -> None:
    travel_date = dt.date(2026, 7, 20)
    row = _provider_row(travel_date=travel_date)
    first_summary = persist_provider_flight_observations(
        db,
        provider_flights=[row],
        context=_context(observed_at=dt.datetime(2026, 7, 20, 8, 0, 0)),
    )
    second_summary = persist_provider_flight_observations(
        db,
        provider_flights=[row],
        context=_context(observed_at=dt.datetime(2026, 7, 20, 8, 1, 0)),
    )

    observations = db.scalars(select(FlightPriceObservation)).all()
    assert first_summary["observations_created"] == 1
    assert second_summary["observations_created"] == 0
    assert second_summary["skipped_recent_duplicates"] == 1
    assert len(observations) == 1


def test_provider_observations_append_same_price_after_six_hours(db: Session) -> None:
    travel_date = dt.date(2026, 7, 20)
    row = _provider_row(travel_date=travel_date)
    persist_provider_flight_observations(
        db,
        provider_flights=[row],
        context=_context(observed_at=dt.datetime(2026, 7, 20, 8, 0, 0)),
    )
    second_summary = persist_provider_flight_observations(
        db,
        provider_flights=[row],
        context=_context(observed_at=dt.datetime(2026, 7, 20, 14, 0, 0)),
    )

    observations = db.scalars(select(FlightPriceObservation)).all()
    assert second_summary["observations_created"] == 1
    assert second_summary["skipped_recent_duplicates"] == 0
    assert len(observations) == 2


def test_provider_observations_append_changed_price_inside_dedupe_window(db: Session) -> None:
    travel_date = dt.date(2026, 7, 20)
    first_row = _provider_row(travel_date=travel_date, price=49.99)
    second_row = _provider_row(travel_date=travel_date, price=59.99)
    persist_provider_flight_observations(
        db,
        provider_flights=[first_row],
        context=_context(observed_at=dt.datetime(2026, 7, 20, 8, 0, 0)),
    )
    second_summary = persist_provider_flight_observations(
        db,
        provider_flights=[second_row],
        context=_context(observed_at=dt.datetime(2026, 7, 20, 8, 1, 0)),
    )

    observations = db.scalars(
        select(FlightPriceObservation).order_by(FlightPriceObservation.observed_at.asc())
    ).all()
    assert second_summary["observations_created"] == 1
    assert second_summary["skipped_recent_duplicates"] == 0
    assert len(observations) == 2
    assert observations[1].price_changed_since_last_seen is True


@pytest.mark.parametrize(
    ("source", "expected_carrier_code"),
    [
        ("ryanair-public-fares", "FR"),
        ("vueling-public-availability", "VY"),
        ("mystery-provider", "MYSTERY-PROVIDER"),
    ],
)
def test_provider_observations_derives_stable_carrier_code(
    db: Session,
    source: str,
    expected_carrier_code: str,
) -> None:
    travel_date = dt.date(2026, 7, 20)

    persist_provider_flight_observations(
        db,
        provider_flights=[_provider_row(travel_date=travel_date, source=source)],
        context=_context(),
    )

    carrier_code = db.scalar(select(FlightOfferCacheEntry.carrier_code))
    assert carrier_code == expected_carrier_code


def _context(*, observed_at: dt.datetime | None = None) -> ObservationPersistenceContext:
    observed_at_value = observed_at or dt.datetime(2026, 7, 20, 8, 0)
    return ObservationPersistenceContext(
        search_cache_entry_id=None,
        observed_at=observed_at_value,
        expires_at=dt.datetime(2026, 7, 20, 12, 0),
        freshness_status="fresh",
        confidence_score=0.95,
        validation_status="revalidated",
    )


def _provider_row(
    *,
    travel_date: dt.date,
    departure_time_local: str = "10:15",
    price: float = 49.99,
    source: str = "ryanair",
) -> ProviderFlightRow:
    return ("LEI", "FCO", travel_date, _flight(departure_time_local=departure_time_local, price=price, source=source))


def _flight(
    *,
    departure_time_local: str = "10:15",
    price: float = 49.99,
    source: str = "ryanair",
) -> ProviderFlight:
    return ProviderFlight(
        price=price,
        currency="EUR",
        departure_time_local=departure_time_local,
        captured_at=dt.datetime(2026, 7, 20, 8, 0),
        source=source,
    )
