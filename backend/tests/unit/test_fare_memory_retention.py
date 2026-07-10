import datetime as dt

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    FlightOfferCacheEntry,
    FlightPriceObservation,
    QuickSearchCacheEntry,
    QuickSearchNegativeCacheEntry,
)
from app.services.fare_memory_retention import FareMemoryRetentionOptions, run_fare_memory_retention


def _db_session() -> tuple[Engine, Session]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, testing_session_local()


def _seed_fare_memory_rows(db: Session, *, now_utc: dt.datetime, today: dt.date) -> None:
    expired_cache = QuickSearchCacheEntry(
        origin_iata="LEI",
        destination_iata="DUB",
        travel_date=today - dt.timedelta(days=1),
        provider="test-provider",
        expires_at_utc=now_utc - dt.timedelta(hours=1),
        payload_json='{"result":"expired"}',
        source_hash="expired",
    )
    live_cache = QuickSearchCacheEntry(
        origin_iata="LEI",
        destination_iata="DUB",
        travel_date=today + dt.timedelta(days=10),
        provider="test-provider",
        expires_at_utc=now_utc + dt.timedelta(hours=1),
        payload_json='{"result":"live"}',
        source_hash="live",
    )
    expired_negative = QuickSearchNegativeCacheEntry(
        negative_fingerprint="negative-expired",
        scope="route_date_provider",
        reason="no_results",
        provider="test-provider",
        canonical_request_json='{"route":"expired"}',
        expires_at=now_utc - dt.timedelta(minutes=5),
        retry_after_at=None,
    )
    live_negative = QuickSearchNegativeCacheEntry(
        negative_fingerprint="negative-live",
        scope="route_date_provider",
        reason="no_results",
        provider="test-provider",
        canonical_request_json='{"route":"live"}',
        expires_at=now_utc + dt.timedelta(minutes=30),
        retry_after_at=None,
    )
    past_offer = FlightOfferCacheEntry(
        offer_fingerprint="offer-past",
        provider="test-provider",
        carrier_code="FR",
        origin_airport="LEI",
        destination_airport="DUB",
        departure_at=now_utc - dt.timedelta(days=1),
        departure_time_local="10:15",
        source_kind="provider",
    )
    future_offer = FlightOfferCacheEntry(
        offer_fingerprint="offer-future",
        provider="test-provider",
        carrier_code="FR",
        origin_airport="LEI",
        destination_airport="DUB",
        departure_at=now_utc + dt.timedelta(days=10),
        departure_time_local="10:15",
        source_kind="provider",
    )
    db.add_all([expired_cache, live_cache, expired_negative, live_negative, past_offer, future_offer])
    db.commit()
    db.refresh(past_offer)
    db.refresh(future_offer)
    db.add_all(
        [
            FlightPriceObservation(
                offer_id=past_offer.id,
                provider="test-provider",
                price_amount=41.0,
                currency="EUR",
                observed_at=now_utc - dt.timedelta(days=2),
                expires_at=now_utc - dt.timedelta(days=1),
                freshness_status="expired",
            ),
            FlightPriceObservation(
                offer_id=future_offer.id,
                provider="test-provider",
                price_amount=51.0,
                currency="EUR",
                observed_at=now_utc,
                expires_at=now_utc + dt.timedelta(hours=1),
                freshness_status="fresh",
            ),
        ]
    )
    db.commit()


def test_fare_memory_retention_dry_run_does_not_delete_candidates() -> None:
    engine, db = _db_session()
    now_utc = dt.datetime(2026, 8, 20, 12, 0)
    today = now_utc.date()
    _seed_fare_memory_rows(db, now_utc=now_utc, today=today)

    try:
        result = run_fare_memory_retention(
            db,
            FareMemoryRetentionOptions(dry_run=True, batch_size=25, today=today, now_utc=now_utc),
        )

        assert result.candidates_total == 4
        assert result.deleted_total == 0
        assert db.scalar(select(func.count(QuickSearchCacheEntry.id))) == 2
        assert db.scalar(select(func.count(QuickSearchNegativeCacheEntry.id))) == 2
        assert db.scalar(select(func.count(FlightPriceObservation.id))) == 2
        assert db.scalar(select(func.count(FlightOfferCacheEntry.id))) == 2
    finally:
        db.close()
        engine.dispose()


def test_fare_memory_retention_apply_deletes_only_expired_fixtures() -> None:
    engine, db = _db_session()
    now_utc = dt.datetime(2026, 8, 20, 12, 0)
    today = now_utc.date()
    _seed_fare_memory_rows(db, now_utc=now_utc, today=today)

    try:
        result = run_fare_memory_retention(
            db,
            FareMemoryRetentionOptions(dry_run=False, batch_size=1, today=today, now_utc=now_utc),
        )

        assert result.candidates_total == 4
        assert result.deleted_total == 4
        assert db.scalar(select(func.count(QuickSearchCacheEntry.id))) == 1
        assert db.scalar(select(func.count(QuickSearchNegativeCacheEntry.id))) == 1
        assert db.scalar(select(func.count(FlightPriceObservation.id))) == 1
        assert db.scalar(select(func.count(FlightOfferCacheEntry.id))) == 1
        live_cache = db.scalar(select(QuickSearchCacheEntry).where(QuickSearchCacheEntry.source_hash == "live"))
        assert live_cache is not None
    finally:
        db.close()
        engine.dispose()
