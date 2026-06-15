import datetime as dt
import json
import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.vocabulary import WATCH_STATUS_PAUSED
from app.infrastructure.db.models import AlertRule, Base, FlightWatch, PriceSnapshot, RevalidationJob, User
from app.services.fare_memory_warmup import (
    build_boot_warmup_candidate_report,
    log_boot_warmup_dry_run,
    log_scheduled_boot_warmup_jobs,
    schedule_boot_warmup_jobs,
)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
    status: str = "active",
) -> FlightWatch:
    watch = FlightWatch(
        user_id=user_id,
        origin_iata=origin,
        destination_iata=destination,
        travel_date_local=travel_date,
        status=status,
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


def _seed_alert(db: Session, *, watch_id: str, threshold_value: float, enabled: bool = True) -> AlertRule:
    alert = AlertRule(
        watch_id=watch_id,
        rule_type="threshold_low",
        threshold_value=threshold_value,
        cooldown_minutes=60,
        enabled=enabled,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def _seed_snapshot(
    db: Session,
    *,
    watch_id: str,
    captured_at: dt.datetime,
    price: float,
    is_stale: bool,
) -> PriceSnapshot:
    snapshot = PriceSnapshot(
        watch_id=watch_id,
        captured_at_utc=captured_at,
        departure_time_local="09:30",
        raw_price=price,
        raw_currency="EUR",
        provider="seed-provider",
        is_stale=is_stale,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _seed_route_history(
    db: Session,
    *,
    watch_id: str,
    prices: list[tuple[dt.datetime, float]],
) -> None:
    for captured_at, price in prices:
        _seed_snapshot(db, watch_id=watch_id, captured_at=captured_at, price=price, is_stale=False)


def test_build_boot_warmup_candidate_report_prioritizes_active_alert_threshold_routes() -> None:
    db = _db()
    try:
        user = _seed_user(db, "warmup@example.com")
        top_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="LEI",
            destination="DUB",
            travel_date=dt.date(2026, 6, 20),
        )
        medium_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="AGP",
            destination="MXP",
            travel_date=dt.date(2026, 7, 15),
        )
        low_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="BCN",
            destination="LIS",
            travel_date=dt.date(2026, 8, 10),
        )
        _seed_watch(
            db,
            user_id=user.id,
            origin="MAD",
            destination="OPO",
            travel_date=dt.date(2026, 6, 18),
            status=WATCH_STATUS_PAUSED,
        )

        _seed_alert(db, watch_id=top_watch.id, threshold_value=100.0)
        _seed_alert(db, watch_id=medium_watch.id, threshold_value=80.0)
        _seed_snapshot(
            db,
            watch_id=top_watch.id,
            captured_at=dt.datetime(2026, 6, 16, 8, 0),
            price=102.0,
            is_stale=True,
        )
        _seed_snapshot(
            db,
            watch_id=medium_watch.id,
            captured_at=dt.datetime(2026, 6, 16, 9, 0),
            price=130.0,
            is_stale=False,
        )

        report = build_boot_warmup_candidate_report(
            db,
            now=dt.datetime(2026, 6, 16, 10, 0),
            limit=2,
        )

        candidates = report["candidates"]
        assert report["total_candidate_count"] == 3
        assert report["candidate_count"] == 2
        assert report["skipped_candidate_count"] == 1
        assert [candidate["watch_id"] for candidate in candidates] == [top_watch.id, medium_watch.id]
        assert "active_alert_enabled" in candidates[0]["reasons"]
        assert "stale_snapshot" in candidates[0]["reasons"]
        assert "near_alert_threshold" in candidates[0]["reasons"]
        assert candidates[0]["near_threshold"] is True
        assert candidates[1]["near_threshold"] is False
        assert low_watch.id not in [candidate["watch_id"] for candidate in candidates]
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_log_boot_warmup_dry_run_emits_report_without_creating_jobs(caplog) -> None:
    db = _db()
    try:
        user = _seed_user(db, "warmup-log@example.com")
        watch = _seed_watch(
            db,
            user_id=user.id,
            origin="SVQ",
            destination="FCO",
            travel_date=dt.date(2026, 6, 24),
        )
        _seed_alert(db, watch_id=watch.id, threshold_value=95.0)
        _seed_snapshot(
            db,
            watch_id=watch.id,
            captured_at=dt.datetime(2026, 6, 16, 9, 30),
            price=94.0,
            is_stale=False,
        )

        with caplog.at_level(logging.INFO, logger="app.fare_memory.warmup"):
            report = log_boot_warmup_dry_run(
                db,
                now=dt.datetime(2026, 6, 16, 10, 0),
                limit=5,
            )

        jobs = db.execute(select(RevalidationJob)).scalars().all()
        payload = json.loads(caplog.records[-1].message)

        assert jobs == []
        assert report["event"] == "fare_memory_boot_warmup_dry_run"
        assert payload["event"] == "fare_memory_boot_warmup_dry_run"
        assert payload["candidate_count"] == 1
        assert payload["candidates"][0]["watch_id"] == watch.id
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


class _DeterministicRandom:
    def __init__(self, values: list[int]) -> None:
        self._values = list(values)

    def randint(self, minimum: int, maximum: int) -> int:
        value = self._values.pop(0)
        assert minimum <= value <= maximum
        return value


def test_schedule_boot_warmup_jobs_respects_rate_limit_and_jitter() -> None:
    db = _db()
    try:
        user = _seed_user(db, "warmup-schedule@example.com")
        watch_a = _seed_watch(
            db,
            user_id=user.id,
            origin="LEI",
            destination="DUB",
            travel_date=dt.date(2026, 6, 21),
        )
        watch_b = _seed_watch(
            db,
            user_id=user.id,
            origin="AGP",
            destination="FCO",
            travel_date=dt.date(2026, 6, 22),
        )
        _seed_watch(
            db,
            user_id=user.id,
            origin="BCN",
            destination="LIS",
            travel_date=dt.date(2026, 6, 23),
        )
        _seed_alert(db, watch_id=watch_a.id, threshold_value=95.0)
        _seed_alert(db, watch_id=watch_b.id, threshold_value=80.0)
        _seed_snapshot(
            db,
            watch_id=watch_a.id,
            captured_at=dt.datetime(2026, 6, 16, 9, 0),
            price=94.0,
            is_stale=True,
        )
        _seed_snapshot(
            db,
            watch_id=watch_b.id,
            captured_at=dt.datetime(2026, 6, 16, 9, 10),
            price=79.0,
            is_stale=False,
        )

        report = schedule_boot_warmup_jobs(
            db,
            now=dt.datetime(2026, 6, 16, 10, 0),
            limit=3,
            provider_rate_limit_per_minute=2,
            jitter_seconds=30,
            rng=_DeterministicRandom([7, 19]),
        )

        jobs = db.execute(select(RevalidationJob).order_by(RevalidationJob.priority.asc(), RevalidationJob.id.asc())).scalars().all()

        assert report["event"] == "fare_memory_boot_warmup_scheduled"
        assert report["candidate_count"] == 2
        assert report["total_candidate_count"] == 3
        assert report["warmup_jobs_skipped_due_rate_limit"] == 1
        assert report["enqueued_job_count"] == 2
        assert len(jobs) == 2
        assert {job.job_type for job in jobs} == {"boot_warmup"}
        assert min(job.scheduled_at for job in jobs) >= dt.datetime(2026, 6, 16, 10, 0)
        assert max(job.scheduled_at for job in jobs) <= dt.datetime(2026, 6, 16, 10, 0, 30)
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_schedule_boot_warmup_jobs_skips_existing_active_route_lock(caplog) -> None:
    db = _db()
    try:
        user = _seed_user(db, "warmup-lock@example.com")
        watch = _seed_watch(
            db,
            user_id=user.id,
            origin="SVQ",
            destination="FCO",
            travel_date=dt.date(2026, 6, 24),
        )
        _seed_alert(db, watch_id=watch.id, threshold_value=90.0)
        _seed_snapshot(
            db,
            watch_id=watch.id,
            captured_at=dt.datetime(2026, 6, 16, 9, 30),
            price=88.0,
            is_stale=True,
        )
        existing_job = RevalidationJob(
            job_type="manual",
            target_type="route",
            target_fingerprint="route:SVQ:FCO:2026-06-24",
            provider="multi",
            priority=10,
            status="queued",
            scheduled_at=dt.datetime(2026, 6, 16, 10, 5),
        )
        db.add(existing_job)
        db.commit()
        db.refresh(existing_job)

        with caplog.at_level(logging.INFO, logger="app.fare_memory.warmup"):
            report = log_scheduled_boot_warmup_jobs(
                db,
                now=dt.datetime(2026, 6, 16, 10, 0),
                limit=5,
                provider_rate_limit_per_minute=5,
                jitter_seconds=30,
                rng=_DeterministicRandom([0]),
            )

        jobs = db.execute(select(RevalidationJob)).scalars().all()
        payload = json.loads(caplog.records[-1].message)

        assert len(jobs) == 1
        assert report["enqueued_job_count"] == 0
        assert report["skipped_due_lock_count"] == 1
        assert payload["skipped_due_lock_count"] == 1
        assert payload["jobs"][0]["job_id"] == existing_job.id
        assert payload["jobs"][0]["status"] == "duplicate_locked"
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_boot_warmup_candidates_prioritize_recently_volatile_routes() -> None:
    db = _db()
    try:
        user = _seed_user(db, "warmup-volatility@example.com")
        volatile_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="LEI",
            destination="DUB",
            travel_date=dt.date(2026, 6, 25),
        )
        stable_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="AGP",
            destination="FCO",
            travel_date=dt.date(2026, 6, 25),
        )
        _seed_alert(db, watch_id=volatile_watch.id, threshold_value=300.0)
        _seed_alert(db, watch_id=stable_watch.id, threshold_value=300.0)
        _seed_route_history(
            db,
            watch_id=volatile_watch.id,
            prices=[
                (dt.datetime(2026, 6, 16, 8, 0), 100.0),
                (dt.datetime(2026, 6, 16, 12, 0), 135.0),
                (dt.datetime(2026, 6, 16, 16, 0), 105.0),
                (dt.datetime(2026, 6, 17, 8, 0), 150.0),
            ],
        )
        _seed_route_history(
            db,
            watch_id=stable_watch.id,
            prices=[
                (dt.datetime(2026, 6, 16, 8, 0), 119.0),
                (dt.datetime(2026, 6, 17, 8, 0), 120.0),
                (dt.datetime(2026, 6, 18, 8, 0), 119.0),
            ],
        )

        report = build_boot_warmup_candidate_report(
            db,
            now=dt.datetime(2026, 6, 18, 10, 0),
            limit=5,
        )
        candidates = report["candidates"]

        assert [candidate["watch_id"] for candidate in candidates][:2] == [volatile_watch.id, stable_watch.id]
        assert candidates[0]["priority"] < candidates[1]["priority"]
        assert candidates[0]["volatility_score"] is not None
        assert candidates[0]["volatility_score"] > candidates[1]["volatility_score"]
        assert "recently_volatile_route" in candidates[0]["reasons"]
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_boot_warmup_candidates_keep_uncertain_routes_honest() -> None:
    db = _db()
    try:
        user = _seed_user(db, "warmup-volatility-insufficient@example.com")
        sparse_watch = _seed_watch(
            db,
            user_id=user.id,
            origin="SVQ",
            destination="LIS",
            travel_date=dt.date(2026, 6, 26),
        )
        _seed_alert(db, watch_id=sparse_watch.id, threshold_value=90.0)
        _seed_route_history(
            db,
            watch_id=sparse_watch.id,
            prices=[
                (dt.datetime(2026, 6, 16, 8, 0), 88.0),
                (dt.datetime(2026, 6, 17, 8, 0), 92.0),
            ],
        )

        report = build_boot_warmup_candidate_report(
            db,
            now=dt.datetime(2026, 6, 18, 10, 0),
            limit=5,
        )
        candidate = report["candidates"][0]

        assert candidate["watch_id"] == sparse_watch.id
        assert candidate["volatility_status"] == "insufficient_data"
        assert candidate["volatility_score"] is None
        assert "recently_volatile_route" not in candidate["reasons"]
        assert "volatility_insufficient_data" in candidate["reasons"]
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
