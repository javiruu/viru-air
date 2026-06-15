import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities import ProviderFlight
from app.infrastructure.db.models import (
    Base,
    FlightOfferCacheEntry,
    FlightPriceObservation,
    QuickSearchCacheEntry,
    QuickSearchNegativeCacheEntry,
)
from app.services.fare_memory import persist_ranked_result_observations
from app.services.quick_search_ranking import RankedResult


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


def _seed_search_cache(db: Session) -> QuickSearchCacheEntry:
    entry = QuickSearchCacheEntry(
        origin_iata="LEI",
        destination_iata="FCO",
        travel_date=dt.date(2026, 7, 20),
        provider="multi",
        search_fingerprint="fsm_search_abc123",
        canonical_request_json='{"origin":"LEI"}',
        provider_set_json='["multi"]',
        status="ready",
        freshness_status="fresh",
        ttl_seconds=3600,
        expires_at_utc=dt.datetime(2026, 7, 20, 12, 0),
        payload_json='{"flights":[]}',
        warnings_json="[]",
        source_hash="qs_abc123",
        result_count=2,
        confidence_score=0.95,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _ranked_result(*, price: float, source: str = "ryanair", departure_time_local: str = "10:15") -> RankedResult:
    return RankedResult(
        origin="LEI",
        destination="FCO",
        travel_date=dt.date(2026, 7, 20),
        flight=ProviderFlight(
            price=price,
            currency="EUR",
            departure_time_local=departure_time_local,
            captured_at=dt.datetime(2026, 7, 20, 8, 0),
            source=source,
        ),
        final_score=0.0,
        score_breakdown={"distance_penalty_total": 0.0},
        origin_seed_iata="LEI",
        destination_seed_iata="FCO",
        origin_is_seed=True,
        destination_is_seed=True,
        origin_distance_from_seed_km=0.0,
        destination_distance_from_seed_km=0.0,
        pair_category="seed-seed",
        discovery_explanation="direct_seed",
    )


def test_quick_search_cache_entry_persists_fare_memory_columns(db: Session) -> None:
    entry = _seed_search_cache(db)

    persisted = db.get(QuickSearchCacheEntry, entry.id)
    assert persisted is not None
    assert persisted.search_fingerprint == "fsm_search_abc123"
    assert persisted.freshness_status == "fresh"
    assert persisted.result_count == 2
    assert float(persisted.confidence_score) == pytest.approx(0.95)


def test_flight_offer_cache_entry_requires_unique_fingerprint(db: Session) -> None:
    first = FlightOfferCacheEntry(
        offer_fingerprint="fsm_offer_abc123",
        provider="ryanair",
        carrier="FR",
        flight_number="FR1234",
        origin_airport="LEI",
        destination_airport="FCO",
        departure_at=dt.datetime(2026, 7, 20, 10, 15),
        arrival_at=dt.datetime(2026, 7, 20, 12, 45),
        duration_minutes=150,
        stops_count=0,
        source_kind="provider",
    )
    db.add(first)
    db.commit()

    duplicate = FlightOfferCacheEntry(
        offer_fingerprint="fsm_offer_abc123",
        provider="duffel",
        origin_airport="LEI",
        destination_airport="FCO",
        departure_at=dt.datetime(2026, 7, 20, 10, 15),
        source_kind="provider",
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_flight_price_observation_can_link_offer_and_search_cache(db: Session) -> None:
    search_cache = _seed_search_cache(db)
    offer = FlightOfferCacheEntry(
        offer_fingerprint="fsm_offer_linked",
        provider="ryanair",
        carrier="FR",
        origin_airport="LEI",
        destination_airport="FCO",
        departure_at=dt.datetime(2026, 7, 20, 10, 15),
        source_kind="provider",
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    observation = FlightPriceObservation(
        offer_id=offer.id,
        search_cache_entry_id=search_cache.id,
        provider="ryanair",
        price_amount=49.99,
        currency="EUR",
        observed_at=dt.datetime(2026, 7, 20, 8, 0),
        expires_at=dt.datetime(2026, 7, 20, 12, 0),
        freshness_status="warm",
        confidence_score=0.74,
        validation_status="observed",
        price_changed_since_last_seen=True,
        delta_abs=-10.00,
        delta_pct=-0.1667,
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)

    persisted = db.get(FlightPriceObservation, observation.id)
    assert persisted is not None
    assert persisted.offer_id == offer.id
    assert persisted.search_cache_entry_id == search_cache.id
    assert float(persisted.price_amount) == pytest.approx(49.99)
    assert persisted.freshness_status == "warm"
    assert float(persisted.delta_pct) == pytest.approx(-0.1667)


def test_negative_cache_entry_requires_unique_fingerprint_and_defaults_hit_count(db: Session) -> None:
    first = QuickSearchNegativeCacheEntry(
        negative_fingerprint="neg_lei_fco_2026_07_20",
        scope="search_request",
        reason="no_availability",
        provider="multi",
        canonical_request_json='{"origin":"LEI","destination":"FCO"}',
        observed_at=dt.datetime(2026, 7, 20, 8, 0),
        expires_at=dt.datetime(2026, 7, 20, 9, 0),
    )
    db.add(first)
    db.commit()
    db.refresh(first)

    assert first.hit_count == 0
    assert first.freshness_status == "negative_fresh"

    duplicate = QuickSearchNegativeCacheEntry(
        negative_fingerprint="neg_lei_fco_2026_07_20",
        scope="search_request",
        reason="provider_timeout",
        provider="multi",
        canonical_request_json='{"origin":"LEI","destination":"FCO"}',
        observed_at=dt.datetime(2026, 7, 20, 8, 30),
        expires_at=dt.datetime(2026, 7, 20, 8, 45),
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_offer_observations_reuse_offer_and_append_history_per_search(db: Session) -> None:
    search_cache = _seed_search_cache(db)

    first_summary = persist_ranked_result_observations(
        db,
        ranked_results=[_ranked_result(price=49.99)],
        search_cache_entry_id=search_cache.id,
        observed_at=dt.datetime(2026, 7, 20, 8, 0),
        expires_at=dt.datetime(2026, 7, 20, 12, 0),
        freshness_status="fresh",
        confidence_score=0.95,
        validation_status="revalidated",
    )
    second_summary = persist_ranked_result_observations(
        db,
        ranked_results=[_ranked_result(price=49.99)],
        search_cache_entry_id=search_cache.id,
        observed_at=dt.datetime(2026, 7, 20, 9, 0),
        expires_at=dt.datetime(2026, 7, 20, 13, 0),
        freshness_status="fresh",
        confidence_score=0.95,
        validation_status="revalidated",
    )

    offers = db.execute(select(FlightOfferCacheEntry)).scalars().all()
    observations = (
        db.execute(
            select(FlightPriceObservation).order_by(FlightPriceObservation.observed_at.asc(), FlightPriceObservation.id.asc())
        )
        .scalars()
        .all()
    )

    assert first_summary == {"offers_created": 1, "observations_created": 1}
    assert second_summary == {"offers_created": 0, "observations_created": 1}
    assert len(offers) == 1
    assert len(observations) == 2
    assert all(observation.offer_id == offers[0].id for observation in observations)
    assert observations[1].price_changed_since_last_seen is False
    assert float(observations[1].delta_abs) == pytest.approx(0.0)
    assert float(observations[1].delta_pct) == pytest.approx(0.0)


def test_offer_observations_mark_price_change_since_last_seen(db: Session) -> None:
    persist_ranked_result_observations(
        db,
        ranked_results=[_ranked_result(price=49.99)],
        search_cache_entry_id=None,
        observed_at=dt.datetime(2026, 7, 20, 8, 0),
        expires_at=dt.datetime(2026, 7, 20, 12, 0),
        freshness_status="fresh",
        confidence_score=0.95,
        validation_status="revalidated",
    )
    persist_ranked_result_observations(
        db,
        ranked_results=[_ranked_result(price=59.99)],
        search_cache_entry_id=None,
        observed_at=dt.datetime(2026, 7, 20, 9, 0),
        expires_at=dt.datetime(2026, 7, 20, 13, 0),
        freshness_status="warm",
        confidence_score=0.4,
        validation_status="provider_partial",
    )

    observations = (
        db.execute(
            select(FlightPriceObservation).order_by(FlightPriceObservation.observed_at.asc(), FlightPriceObservation.id.asc())
        )
        .scalars()
        .all()
    )

    assert len(observations) == 2
    assert observations[0].price_changed_since_last_seen is False
    assert observations[1].price_changed_since_last_seen is True
    assert float(observations[1].delta_abs) == pytest.approx(10.0)
    assert float(observations[1].delta_pct) == pytest.approx(0.2)
    assert observations[1].validation_status == "provider_partial"
