import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.models import AlertRule, Base, FlightWatch, PriceSnapshot, RevalidationJob, User
from app.services.fare_memory_warmup import build_boot_warmup_candidate_report
from app.services.watchlist_revalidation import enqueue_startup_refresh_jobs


def _db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
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
    origin: str,
    destination: str,
    travel_date: dt.date,
) -> FlightWatch:
    watch = FlightWatch(
        user_id=user_id,
        origin_iata=origin,
        destination_iata=destination,
        travel_date_local=travel_date,
        status="active",
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


def _seed_alert(db: Session, *, watch_id: str, threshold_value: float) -> None:
    db.add(
        AlertRule(
            watch_id=watch_id,
            rule_type="threshold_low",
            threshold_value=threshold_value,
            cooldown_minutes=60,
            enabled=True,
        )
    )
    db.commit()


def _seed_snapshot(db: Session, *, watch_id: str, captured_at: dt.datetime, price: float) -> None:
    db.add(
        PriceSnapshot(
            watch_id=watch_id,
            captured_at_utc=captured_at,
            departure_time_local="09:30",
            raw_price=price,
            raw_currency="EUR",
            provider="seed-provider",
        )
    )
    db.commit()


def test_boot_warmup_candidates_skip_past_active_watches() -> None:
    db = _db()
    try:
        # Given
        reference_now = dt.datetime(2026, 6, 16, 10, 0)
        user = _seed_user(db, "warmup-priority@example.com")
        past_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="MAD",
            destination="DUB",
            travel_date=reference_now.date() - dt.timedelta(days=1),
        )
        future_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="LEI",
            destination="FCO",
            travel_date=reference_now.date() + dt.timedelta(days=1),
        )
        _seed_alert(db, watch_id=past_watch.id, threshold_value=90.0)
        _seed_alert(db, watch_id=future_watch.id, threshold_value=90.0)

        # When
        report = build_boot_warmup_candidate_report(db, now=reference_now, limit=10)

        # Then
        candidates = report["candidates"]
        assert report["total_candidate_count"] == 1
        assert len(candidates) == 1
        assert candidates[0]["watch_id"] == future_watch.id
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_startup_refresh_jobs_skip_past_active_watches() -> None:
    db = _db()
    try:
        # Given
        reference_now = dt.datetime(2026, 6, 16, 10, 0)
        user = _seed_user(db, "startup-priority@example.com")
        past_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="MAD",
            destination="DUB",
            travel_date=reference_now.date() - dt.timedelta(days=1),
        )
        future_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="LEI",
            destination="FCO",
            travel_date=reference_now.date() + dt.timedelta(days=1),
        )
        _seed_snapshot(
            db,
            watch_id=past_watch.id,
            captured_at=reference_now - dt.timedelta(days=3),
            price=88.0,
        )
        _seed_snapshot(
            db,
            watch_id=future_watch.id,
            captured_at=reference_now - dt.timedelta(days=3),
            price=88.0,
        )

        # When
        report = enqueue_startup_refresh_jobs(db, now=reference_now)

        # Then
        jobs = db.execute(select(RevalidationJob)).scalars().all()
        assert report["evaluated_route_count"] == 1
        assert report["stale_route_count"] == 1
        assert report["enqueued_job_count"] == 1
        assert len(jobs) == 1
        assert jobs[0].target_fingerprint == "route:LEI:FCO:2026-06-17"
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
