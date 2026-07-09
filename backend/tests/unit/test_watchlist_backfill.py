import datetime as dt

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, FlightOfferCacheEntry, FlightPriceObservation, FlightWatch, PriceSnapshot, User
from app.services.watchlist_backfill import find_backfill_observations_for_watch, persist_backfill_snapshots_for_watch


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def _seed_user(db: Session) -> User:
    user = User(email="backfill@viru.dev", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_watch(
    db: Session,
    *,
    user_id: str,
    origin: str = "LEI",
    destination: str = "DUB",
    travel_date: dt.date = dt.date(2026, 7, 20),
) -> FlightWatch:
    watch = FlightWatch(
        user_id=user_id,
        origin_iata=origin,
        destination_iata=destination,
        travel_date_local=travel_date,
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


def _seed_offer(
    db: Session,
    *,
    origin: str = "LEI",
    destination: str = "DUB",
    departure_at: dt.datetime = dt.datetime(2026, 7, 20, 10, 15),
    departure_time_local: str | None = "10:15",
) -> FlightOfferCacheEntry:
    offer = FlightOfferCacheEntry(
        offer_fingerprint=f"fsm_offer_{origin}_{destination}_{departure_at.isoformat()}",
        flight_instance_fingerprint=f"fsm_flight_{origin}_{destination}_{departure_at.isoformat()}",
        provider="ryanair-public-fares",
        carrier_code="FR",
        origin_airport=origin,
        destination_airport=destination,
        departure_at=departure_at,
        departure_time_local=departure_time_local,
        source_kind="provider",
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def _seed_observation(
    db: Session,
    *,
    offer_id: str,
    observed_at: dt.datetime,
    price: float | None = 49.99,
    provider: str = "ryanair-public-fares",
) -> FlightPriceObservation:
    observation = FlightPriceObservation(
        offer_id=offer_id,
        provider=provider,
        price_amount=price,
        currency="EUR",
        observed_at=observed_at,
        freshness_status="fresh",
        validation_status="observed",
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


def test_find_backfill_observations_returns_route_matches_in_observed_order() -> None:
    db = _db()
    try:
        user = _seed_user(db)
        watch = _seed_watch(db, user_id=user.id)
        offer = _seed_offer(db)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 7, 19, 9, 0), price=59.99)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 7, 19, 8, 0), price=49.99)

        result = find_backfill_observations_for_watch(
            db,
            watch,
            now=dt.datetime(2026, 7, 19, 12, 0),
        )

        assert [item.price_amount for item in result] == [49.99, 59.99]
        assert [item.departure_time_local for item in result] == ["10:15", "10:15"]
    finally:
        db.close()


def test_find_backfill_observations_does_not_write_database() -> None:
    db = _db()
    try:
        user = _seed_user(db)
        watch = _seed_watch(db, user_id=user.id)
        offer = _seed_offer(db)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 7, 19, 8, 0))
        before_count = db.scalar(select(func.count(FlightPriceObservation.id)))

        find_backfill_observations_for_watch(db, watch, now=dt.datetime(2026, 7, 19, 12, 0))

        after_count = db.scalar(select(func.count(FlightPriceObservation.id)))
        assert after_count == before_count
    finally:
        db.close()


def test_find_backfill_observations_excludes_other_routes_and_past_departures() -> None:
    db = _db()
    try:
        user = _seed_user(db)
        watch = _seed_watch(db, user_id=user.id)
        other_route = _seed_offer(db, destination="FCO")
        past_offer = _seed_offer(db, departure_at=dt.datetime(2026, 7, 18, 10, 15))
        _seed_observation(db, offer_id=other_route.id, observed_at=dt.datetime(2026, 7, 19, 8, 0))
        _seed_observation(db, offer_id=past_offer.id, observed_at=dt.datetime(2026, 7, 17, 8, 0))

        result = find_backfill_observations_for_watch(
            db,
            watch,
            now=dt.datetime(2026, 7, 19, 12, 0),
        )

        assert result == []
    finally:
        db.close()


def test_find_backfill_observations_excludes_future_observed_and_null_price() -> None:
    db = _db()
    try:
        user = _seed_user(db)
        watch = _seed_watch(db, user_id=user.id)
        offer = _seed_offer(db)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 7, 19, 13, 0), price=49.99)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 7, 19, 8, 0), price=None)

        result = find_backfill_observations_for_watch(
            db,
            watch,
            now=dt.datetime(2026, 7, 19, 12, 0),
        )

        assert result == []
    finally:
        db.close()


def test_persist_backfill_snapshots_for_watch_writes_stale_historical_snapshots() -> None:
    db = _db()
    try:
        user = _seed_user(db)
        watch = _seed_watch(db, user_id=user.id)
        offer = _seed_offer(db)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 7, 19, 8, 0), price=49.99)
        observations = find_backfill_observations_for_watch(
            db,
            watch,
            now=dt.datetime(2026, 7, 19, 12, 0),
        )

        inserted = persist_backfill_snapshots_for_watch(db, watch, observations)

        snapshots = db.scalars(select(PriceSnapshot)).all()
        assert inserted == 1
        assert len(snapshots) == 1
        assert snapshots[0].watch_id == watch.id
        assert snapshots[0].captured_at_utc == dt.datetime(2026, 7, 19, 8, 0)
        assert float(snapshots[0].raw_price) == 49.99
        assert snapshots[0].raw_currency == "EUR"
        assert snapshots[0].provider == "historical_backfill"
        assert snapshots[0].departure_time_local == "10:15"
        assert snapshots[0].is_stale is True
    finally:
        db.close()


def test_persist_backfill_snapshots_for_watch_is_idempotent() -> None:
    db = _db()
    try:
        user = _seed_user(db)
        watch = _seed_watch(db, user_id=user.id)
        offer = _seed_offer(db)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 7, 19, 8, 0), price=49.99)
        observations = find_backfill_observations_for_watch(
            db,
            watch,
            now=dt.datetime(2026, 7, 19, 12, 0),
        )

        first_inserted = persist_backfill_snapshots_for_watch(db, watch, observations)
        second_inserted = persist_backfill_snapshots_for_watch(db, watch, observations)

        snapshot_count = db.scalar(select(func.count(PriceSnapshot.id)))
        assert first_inserted == 1
        assert second_inserted == 0
        assert snapshot_count == 1
    finally:
        db.close()
