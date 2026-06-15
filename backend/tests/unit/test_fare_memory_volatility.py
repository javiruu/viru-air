import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, FlightOfferCacheEntry, FlightPriceObservation, FlightWatch, PriceSnapshot, User
from app.services.fare_memory_volatility import build_offer_volatility_report, build_route_volatility_report


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def _seed_user(db: Session, email: str) -> User:
    user = User(email=email, password_hash="x")
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


def _seed_snapshot(
    db: Session,
    *,
    watch_id: str,
    captured_at: dt.datetime,
    price: float,
) -> PriceSnapshot:
    snapshot = PriceSnapshot(
        watch_id=watch_id,
        captured_at_utc=captured_at,
        departure_time_local="10:00",
        raw_price=price,
        raw_currency="EUR",
        provider="multi",
        is_stale=False,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _seed_offer(db: Session) -> FlightOfferCacheEntry:
    offer = FlightOfferCacheEntry(
        offer_fingerprint="fsm_offer_volatility_1",
        provider="ryanair",
        carrier="FR",
        flight_number="FR100",
        origin_airport="LEI",
        destination_airport="DUB",
        departure_at=dt.datetime(2026, 7, 20, 10, 0),
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
    price: float,
) -> FlightPriceObservation:
    observation = FlightPriceObservation(
        offer_id=offer_id,
        provider="ryanair",
        price_amount=price,
        currency="EUR",
        observed_at=observed_at,
        freshness_status="fresh",
        confidence_score=0.9,
        validation_status="observed",
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


def test_offer_volatility_report_calculates_delta_frequency_and_score() -> None:
    db = _db()
    try:
        offer = _seed_offer(db)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 6, 16, 8, 0), price=100.0)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 6, 16, 12, 0), price=130.0)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 6, 16, 16, 0), price=110.0)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 6, 17, 8, 0), price=150.0)

        report = build_offer_volatility_report(db, offer_id=offer.id)

        assert report["subject_type"] == "offer"
        assert report["observation_count"] == 4
        assert report["sufficient_observations"] is True
        assert report["changes_count"] == 3
        assert report["changes_per_day"] == 3.0
        assert report["average_delta_abs"] == 30.0
        assert report["max_delta_abs"] == 40.0
        assert report["average_time_between_changes_seconds"] == 36000
        assert report["dominant_direction_recent"] == "up"
        assert report["volatility_score"] is not None
        assert report["volatility_score"] > 0.5
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_route_volatility_report_aggregates_snapshots_by_route() -> None:
    db = _db()
    try:
        first_user = _seed_user(db, "route-volatility@example.com")
        second_user = _seed_user(db, "route-volatility-2@example.com")
        first_watch = _seed_watch(db, user_id=first_user.id)
        second_watch = _seed_watch(
            db,
            user_id=second_user.id,
            origin="LEI",
            destination="DUB",
            travel_date=dt.date(2026, 7, 20),
        )
        _seed_snapshot(db, watch_id=first_watch.id, captured_at=dt.datetime(2026, 6, 16, 8, 0), price=90.0)
        _seed_snapshot(db, watch_id=second_watch.id, captured_at=dt.datetime(2026, 6, 16, 14, 0), price=95.0)
        _seed_snapshot(db, watch_id=first_watch.id, captured_at=dt.datetime(2026, 6, 17, 8, 0), price=80.0)

        report = build_route_volatility_report(
            db,
            origin_iata="lei",
            destination_iata="dub",
            travel_date_local=dt.date(2026, 7, 20),
        )

        assert report["subject_type"] == "route"
        assert report["subject_key"] == "route:LEI:DUB:2026-07-20"
        assert report["observation_count"] == 3
        assert report["sufficient_observations"] is True
        assert report["changes_count"] == 2
        assert report["changes_per_day"] == 2.0
        assert report["average_delta_abs"] == 10.0
        assert report["max_delta_abs"] == 15.0
        assert report["dominant_direction_recent"] == "mixed"
        assert report["watch_count"] == 2
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_volatility_report_marks_insufficient_data_when_history_is_short() -> None:
    db = _db()
    try:
        offer = _seed_offer(db)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 6, 16, 8, 0), price=100.0)
        _seed_observation(db, offer_id=offer.id, observed_at=dt.datetime(2026, 6, 16, 12, 0), price=101.0)

        report = build_offer_volatility_report(db, offer_id=offer.id)

        assert report["observation_count"] == 2
        assert report["sufficient_observations"] is False
        assert report["status"] == "insufficient_data"
        assert report["dominant_direction_recent"] == "insufficient_data"
        assert report["volatility_score"] is None
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
