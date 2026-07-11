import datetime as dt
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.models import Base, FlightOfferCacheEntry, FlightPriceObservation
from app.services.fare_memory_historical_aggregates import build_historical_daily_aggregates
from app.services.fare_memory_observability import build_fare_memory_health_snapshot


@dataclass(frozen=True, slots=True)
class OfferSeed:
    offer_fingerprint: str
    origin_airport: str
    destination_airport: str
    departure_at: dt.datetime


@dataclass(frozen=True, slots=True)
class ObservationSeed:
    price_amount: float
    observed_at: dt.datetime


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_historical_daily_aggregates_report_min_max_latest_and_count(db: Session) -> None:
    now = dt.datetime(2026, 7, 21, 12, 0)
    offer = _seed_offer(
        db,
        OfferSeed(
            offer_fingerprint="past-offer",
            origin_airport="LEI",
            destination_airport="DUB",
            departure_at=dt.datetime(2026, 7, 20, 10, 0),
        ),
    )
    _seed_observation(db, offer, ObservationSeed(price_amount=120, observed_at=dt.datetime(2026, 7, 1, 8, 0)))
    _seed_observation(db, offer, ObservationSeed(price_amount=80, observed_at=dt.datetime(2026, 7, 2, 8, 0)))
    _seed_observation(db, offer, ObservationSeed(price_amount=95, observed_at=dt.datetime(2026, 7, 3, 8, 0)))
    db.commit()

    aggregates = build_historical_daily_aggregates(db, now=now, limit=10)

    assert len(aggregates) == 1
    aggregate = aggregates[0]
    assert aggregate.route == "LEI-DUB"
    assert aggregate.departure_date == dt.date(2026, 7, 20)
    assert aggregate.observation_count == 3
    assert aggregate.min_price == 80.0
    assert aggregate.max_price == 120.0
    assert aggregate.latest_price == 95.0
    assert aggregate.latest_observed_at == dt.datetime(2026, 7, 3, 8, 0)
    assert aggregate.compaction_candidate is True


def test_health_snapshot_exposes_dynamic_historical_aggregates(db: Session) -> None:
    now = dt.datetime(2026, 7, 10, 12, 0)
    offer = _seed_offer(
        db,
        OfferSeed(
            offer_fingerprint="future-offer",
            origin_airport="AGP",
            destination_airport="FCO",
            departure_at=dt.datetime(2026, 7, 30, 9, 30),
        ),
    )
    _seed_observation(db, offer, ObservationSeed(price_amount=51, observed_at=dt.datetime(2026, 7, 1, 9, 0)))
    _seed_observation(db, offer, ObservationSeed(price_amount=61, observed_at=dt.datetime(2026, 7, 2, 9, 0)))
    db.commit()

    snapshot = build_fare_memory_health_snapshot(db, now=now)

    top_route = snapshot["historical_aggregates"]["top_routes"][0]
    assert top_route["route"] == "AGP-FCO"
    assert top_route["departure_date"] == "2026-07-30"
    assert top_route["observation_count"] == 2
    assert top_route["min_price"] == 51.0
    assert top_route["max_price"] == 61.0
    assert top_route["latest_price"] == 61.0
    assert top_route["compaction_candidate"] is False
    assert snapshot["historical_aggregates"]["mode"] == "dynamic_read_only"
    assert "user_id" not in str(snapshot)


def _seed_offer(
    db: Session,
    seed: OfferSeed,
) -> FlightOfferCacheEntry:
    offer = FlightOfferCacheEntry(
        offer_fingerprint=seed.offer_fingerprint,
        flight_instance_fingerprint=f"flight-{seed.offer_fingerprint}",
        provider="test-provider",
        carrier_code="FR",
        origin_airport=seed.origin_airport,
        destination_airport=seed.destination_airport,
        departure_at=seed.departure_at,
        source_kind="provider",
    )
    db.add(offer)
    db.flush()
    return offer


def _seed_observation(
    db: Session,
    offer: FlightOfferCacheEntry,
    seed: ObservationSeed,
) -> None:
    db.add(
        FlightPriceObservation(
            offer_id=offer.id,
            provider="test-provider",
            price_amount=seed.price_amount,
            currency="EUR",
            observed_at=seed.observed_at,
            expires_at=seed.observed_at + dt.timedelta(hours=1),
            freshness_status="fresh",
            validation_status="revalidated",
        )
    )
