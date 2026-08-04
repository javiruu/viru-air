import datetime as dt
from dataclasses import dataclass
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.search import QuickSearchSaveResultIn, save_result
from app.infrastructure.db.models import (
    Base,
    FlightOfferCacheEntry,
    FlightPriceObservation,
    PriceSnapshot,
    RevalidationJob,
)


@dataclass(frozen=True, slots=True)
class _BackfillSeed:
    origin: str
    destination: str
    travel_date: dt.date
    observed_at: dt.datetime
    price: float


@dataclass(frozen=True, slots=True)
class _CurrentUser:
    id: str


def _db_session() -> tuple[Engine, Session]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, testing_session_local()


def _seed_backfill_observation(db: Session, seed: _BackfillSeed) -> None:
    offer = FlightOfferCacheEntry(
        offer_fingerprint=(
            f"quick_save_backfill_{seed.origin}_{seed.destination}_{seed.travel_date.isoformat()}_"
            f"{seed.price}_{int(seed.observed_at.timestamp())}"
        ),
        flight_instance_fingerprint=f"quick_save_flight_{seed.origin}_{seed.destination}_{seed.travel_date.isoformat()}",
        provider="ryanair-public-fares",
        carrier_code="FR",
        origin_airport=seed.origin,
        destination_airport=seed.destination,
        departure_at=dt.datetime.combine(seed.travel_date, dt.time(hour=10, minute=15)),
        departure_time_local="10:15",
        source_kind="provider",
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    db.add(
        FlightPriceObservation(
            offer_id=offer.id,
            provider="ryanair-public-fares",
            price_amount=seed.price,
            currency="EUR",
            observed_at=seed.observed_at,
            freshness_status="fresh",
            validation_status="observed",
        )
    )
    db.commit()


def test_save_result_fresh_backfills_historical_watch_snapshots() -> None:
    engine, db = _db_session()
    travel_date = dt.date.today() + dt.timedelta(days=42)
    observed_at = dt.datetime.now(dt.UTC).replace(tzinfo=None, microsecond=0) - dt.timedelta(hours=2)
    _seed_backfill_observation(
        db,
        _BackfillSeed(
            origin="LEI",
            destination="DUB",
            travel_date=travel_date,
            observed_at=observed_at,
            price=44.5,
        ),
    )
    payload = QuickSearchSaveResultIn(
        origin_iata="LEI",
        destination_iata="DUB",
        travel_date=travel_date,
        price_total=52.5,
        currency="EUR",
        freshness_status="fresh",
        requires_revalidation=False,
        validation_status="revalidated",
    )

    try:
        with patch("app.services.quick_search_save_result_observation.FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED", True):
            created = save_result(
                payload=payload,
                idempotency_key=None,
                db=db,
                current_user=_CurrentUser(id="user-quick-save-backfill-fresh"),
            )

        snapshots = db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.watch_id == created["watch_id"])
            .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
        ).all()

        assert len(snapshots) == 2
        assert snapshots[0].provider == "historical_backfill"
        assert float(snapshots[0].raw_price) == 44.5
        assert snapshots[0].captured_at_utc == observed_at
        assert snapshots[0].is_stale is True
        assert snapshots[1].provider == "quick-search"
        assert float(snapshots[1].raw_price) == 52.5
        assert snapshots[1].is_stale is False
    finally:
        db.close()
        engine.dispose()


def test_save_result_stale_backfills_history_while_enqueuing_revalidation() -> None:
    engine, db = _db_session()
    travel_date = dt.date.today() + dt.timedelta(days=43)
    observed_at = dt.datetime.now(dt.UTC).replace(tzinfo=None, microsecond=0) - dt.timedelta(hours=3)
    _seed_backfill_observation(
        db,
        _BackfillSeed(
            origin="GRX",
            destination="DUB",
            travel_date=travel_date,
            observed_at=observed_at,
            price=39.25,
        ),
    )
    payload = QuickSearchSaveResultIn(
        origin_iata="GRX",
        destination_iata="DUB",
        travel_date=travel_date,
        price_total=41.0,
        currency="EUR",
        freshness_status="warm",
        requires_revalidation=False,
        validation_status="seen",
    )

    try:
        with patch("app.services.quick_search_save_result_observation.FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED", True):
            created = save_result(
                payload=payload,
                idempotency_key=None,
                db=db,
                current_user=_CurrentUser(id="user-quick-save-backfill-stale"),
            )
            existing = save_result(
                payload=payload,
                idempotency_key=None,
                db=db,
                current_user=_CurrentUser(id="user-quick-save-backfill-stale"),
            )

        snapshots = db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.watch_id == created["watch_id"])
            .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
        ).all()
        jobs = db.scalars(
            select(RevalidationJob).where(
                RevalidationJob.target_fingerprint == f"route:GRX:DUB:{travel_date.isoformat()}",
            )
        ).all()

        assert existing["watch_id"] == created["watch_id"]
        assert len(snapshots) == 3
        assert snapshots[0].provider == "historical_backfill"
        assert float(snapshots[0].raw_price) == 39.25
        assert snapshots[0].captured_at_utc == observed_at
        assert snapshots[0].is_stale is True
        assert snapshots[1].provider == "quick-search"
        assert float(snapshots[1].raw_price) == 41.0
        assert snapshots[1].is_stale is True
        assert snapshots[2].provider == "quick-search"
        assert float(snapshots[2].raw_price) == 41.0
        assert snapshots[2].is_stale is True
        assert len(jobs) == 1
        assert jobs[0].status == "queued"
    finally:
        db.close()
        engine.dispose()


def test_save_result_with_backfill_enabled_and_no_history_keeps_current_snapshot_only() -> None:
    engine, db = _db_session()
    travel_date = dt.date.today() + dt.timedelta(days=44)
    payload = QuickSearchSaveResultIn(
        origin_iata="VLC",
        destination_iata="DUB",
        travel_date=travel_date,
        price_total=67.0,
        currency="EUR",
        freshness_status="fresh",
        requires_revalidation=False,
        validation_status="revalidated",
    )

    try:
        with patch("app.services.quick_search_save_result_observation.FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED", True):
            created = save_result(
                payload=payload,
                idempotency_key=None,
                db=db,
                current_user=_CurrentUser(id="user-quick-save-backfill-empty"),
            )

        snapshots = db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.watch_id == created["watch_id"])
            .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
        ).all()

        assert len(snapshots) == 1
        assert snapshots[0].provider == "quick-search"
        assert float(snapshots[0].raw_price) == 67.0
        assert snapshots[0].is_stale is False
    finally:
        db.close()
        engine.dispose()


def test_save_result_backfill_flag_off_ignores_available_history() -> None:
    engine, db = _db_session()
    travel_date = dt.date.today() + dt.timedelta(days=45)
    observed_at = dt.datetime.now(dt.UTC).replace(tzinfo=None, microsecond=0) - dt.timedelta(hours=4)
    _seed_backfill_observation(
        db,
        _BackfillSeed(
            origin="SVQ",
            destination="DUB",
            travel_date=travel_date,
            observed_at=observed_at,
            price=38.75,
        ),
    )
    payload = QuickSearchSaveResultIn(
        origin_iata="SVQ",
        destination_iata="DUB",
        travel_date=travel_date,
        price_total=46.0,
        currency="EUR",
        freshness_status="fresh",
        requires_revalidation=False,
        validation_status="revalidated",
    )

    try:
        with patch("app.services.quick_search_save_result_observation.FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED", False):
            created = save_result(
                payload=payload,
                idempotency_key=None,
                db=db,
                current_user=_CurrentUser(id="user-quick-save-backfill-disabled"),
            )

        snapshots = db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.watch_id == created["watch_id"])
            .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
        ).all()

        assert len(snapshots) == 1
        assert snapshots[0].provider == "quick-search"
        assert float(snapshots[0].raw_price) == 46.0
        assert snapshots[0].is_stale is False
    finally:
        db.close()
        engine.dispose()
