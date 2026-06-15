import datetime as dt
import json
import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.vocabulary import WATCH_STATUS_PAUSED
from app.infrastructure.db.models import AlertRule, Base, FlightWatch, PriceSnapshot, RevalidationJob, User
from app.services.fare_memory_warmup import build_boot_warmup_candidate_report, log_boot_warmup_dry_run


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
