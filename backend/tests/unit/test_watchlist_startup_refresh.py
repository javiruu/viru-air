import datetime as dt
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
import app.services.watchlist_revalidation as watchlist_revalidation
from app.core.time import utc_now_naive
from app.infrastructure.db.models import Base, FlightWatch, PriceSnapshot, RevalidationJob, User
from app.main import app
from app.services.watchlist_revalidation import (
    enqueue_startup_refresh_jobs,
    process_due_route_revalidation_jobs,
)


class _FakeProvider:
    def get_flights(self, origin: str, destination: str, travel_date: str):
        return [
            type(
                "ProviderFlightStub",
                (),
                {
                    "price": 61.0,
                    "currency": "EUR",
                    "departure_time_local": "08:25",
                    "source": "startup-fake-provider",
                },
            )()
        ]


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
    session._test_session_factory = testing_session_local  # type: ignore[attr-defined]
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
        departure_time_local="09:10",
        raw_price=price,
        raw_currency="EUR",
        provider="seed-provider",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def test_enqueue_startup_refresh_jobs_deduplicates_shared_route_and_selects_stale_routes() -> None:
    db = _db()
    try:
        reference_now = utc_now_naive().replace(microsecond=0)
        owner_a = _seed_user(db, "startup-a@example.com")
        owner_b = _seed_user(db, "startup-b@example.com")
        fresh_owner = _seed_user(db, "startup-fresh@example.com")
        travel_date = reference_now.date() + dt.timedelta(days=29)

        watch_a = _seed_watch(
            db,
            user_id=owner_a.id,
            origin="MAD",
            destination="DUB",
            travel_date=travel_date,
        )
        _seed_watch(
            db,
            user_id=owner_b.id,
            origin="MAD",
            destination="DUB",
            travel_date=travel_date,
        )
        fresh_watch = _seed_watch(
            db,
            user_id=fresh_owner.id,
            origin="BCN",
            destination="LIS",
            travel_date=travel_date,
        )

        _seed_snapshot(
            db,
            watch_id=watch_a.id,
            captured_at=reference_now - dt.timedelta(days=3),
            price=88.0,
        )
        _seed_snapshot(
            db,
            watch_id=fresh_watch.id,
            captured_at=reference_now - dt.timedelta(hours=2),
            price=55.0,
        )

        report = enqueue_startup_refresh_jobs(
            db,
            now=reference_now,
        )
        jobs = db.execute(select(RevalidationJob)).scalars().all()

        assert report["evaluated_route_count"] == 2
        assert report["stale_route_count"] == 1
        assert report["enqueued_job_count"] == 2
        assert len(jobs) == 2
        assert jobs[0].job_type == "startup_refresh"
        assert jobs[0].target_fingerprint == f"route:MAD:DUB:{travel_date.isoformat()}"
        assert report["jobs"][0]["watch_count"] == 2
        assert report["jobs"][0]["reason"] == "snapshot_expired"
        assert report["jobs"][1]["reason"] == "fresh"
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_process_due_route_revalidation_jobs_refreshes_all_active_watches_for_route() -> None:
    db = _db()
    try:
        reference_now = utc_now_naive().replace(microsecond=0)
        owner_a = _seed_user(db, "process-a@example.com")
        owner_b = _seed_user(db, "process-b@example.com")
        travel_date = reference_now.date() + dt.timedelta(days=30)

        watch_a = _seed_watch(
            db,
            user_id=owner_a.id,
            origin="SVQ",
            destination="FCO",
            travel_date=travel_date,
        )
        watch_b = _seed_watch(
            db,
            user_id=owner_b.id,
            origin="SVQ",
            destination="FCO",
            travel_date=travel_date,
        )
        _seed_snapshot(
            db,
            watch_id=watch_a.id,
            captured_at=reference_now - dt.timedelta(days=3),
            price=95.0,
        )

        enqueue_startup_refresh_jobs(
            db,
            now=reference_now,
        )

        report = process_due_route_revalidation_jobs(
            db._test_session_factory,  # type: ignore[attr-defined]
            provider_client=_FakeProvider(),
        )

        snapshots = db.execute(
            select(PriceSnapshot).where(PriceSnapshot.watch_id.in_([watch_a.id, watch_b.id]))
        ).scalars().all()
        jobs = db.execute(select(RevalidationJob)).scalars().all()
        refreshed_snapshots = [
            snapshot for snapshot in snapshots if float(snapshot.raw_price) == 61.0
        ]

        assert report["processed_job_count"] == 1
        assert report["refreshed_job_count"] == 1
        assert len(refreshed_snapshots) == 2
        assert len(jobs) == 1
        assert jobs[0].status == "done"
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_server_startup_refreshes_stale_watchlist_routes_automatically(monkeypatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    seed_db = TestingSessionLocal()
    try:
        owner_a = _seed_user(seed_db, "startup-live-a@example.com")
        owner_b = _seed_user(seed_db, "startup-live-b@example.com")
        travel_date = dt.date(2026, 7, 21)
        watch_a = _seed_watch(
            seed_db,
            user_id=owner_a.id,
            origin="AGP",
            destination="DUB",
            travel_date=travel_date,
        )
        _seed_watch(
            seed_db,
            user_id=owner_b.id,
            origin="AGP",
            destination="DUB",
            travel_date=travel_date,
        )
        _seed_snapshot(
            seed_db,
            watch_id=watch_a.id,
            captured_at=dt.datetime(2026, 7, 18, 7, 0),
            price=120.0,
        )
    finally:
        seed_db.close()

    original_session_local = main_module.SessionLocal
    original_watchlist_provider = watchlist_revalidation.provider
    original_watchlist_flag = main_module.WATCHLIST_STARTUP_REFRESH_ENABLED
    original_fare_memory_flag = main_module.FARE_MEMORY_BOOT_WARMUP_ENABLED
    try:
        monkeypatch.setattr(main_module, "SessionLocal", TestingSessionLocal)
        monkeypatch.setattr(watchlist_revalidation, "provider", _FakeProvider())
        monkeypatch.setattr(main_module, "WATCHLIST_STARTUP_REFRESH_ENABLED", True)
        monkeypatch.setattr(main_module, "FARE_MEMORY_BOOT_WARMUP_ENABLED", False)

        with TestClient(app):
            deadline = time.time() + 2.0
            while time.time() < deadline:
                check_db = TestingSessionLocal()
                try:
                    refreshed_snapshots = check_db.execute(
                        select(PriceSnapshot).where(PriceSnapshot.raw_price == 61.0)
                    ).scalars().all()
                    if len(refreshed_snapshots) >= 2:
                        break
                finally:
                    check_db.close()
                time.sleep(0.05)

        check_db = TestingSessionLocal()
        try:
            refreshed_snapshots = check_db.execute(
                select(PriceSnapshot).where(PriceSnapshot.raw_price == 61.0)
            ).scalars().all()
            jobs = check_db.execute(select(RevalidationJob)).scalars().all()

            assert len(refreshed_snapshots) == 2
            assert len(jobs) == 1
            assert jobs[0].status == "done"
        finally:
            check_db.close()
    finally:
        main_module.SessionLocal = original_session_local
        main_module.WATCHLIST_STARTUP_REFRESH_ENABLED = original_watchlist_flag
        main_module.FARE_MEMORY_BOOT_WARMUP_ENABLED = original_fare_memory_flag
        watchlist_revalidation.provider = original_watchlist_provider
        engine.dispose()
