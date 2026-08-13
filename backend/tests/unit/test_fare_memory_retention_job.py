import datetime as dt
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.infrastructure.db.models import Base, QuickSearchCacheEntry, RevalidationJob
from app.main import app
from app.services.fare_memory_retention_job import run_startup_fare_memory_retention


def test_startup_fare_memory_retention_processes_batches_once_per_day() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None, microsecond=0)
    today = now.date()
    seed_db = testing_session_local()
    try:
        seed_db.add_all(
            [
                QuickSearchCacheEntry(
                    origin_iata="LEI",
                    destination_iata="DUB",
                    travel_date=today - dt.timedelta(days=1),
                    provider="test-provider",
                    expires_at_utc=now - dt.timedelta(hours=1),
                    payload_json=f'{{"marker":"expired-{index}"}}',
                    source_hash=f"expired-{index}",
                )
                for index in range(1000)
            ]
        )
        seed_db.add(
            QuickSearchCacheEntry(
                origin_iata="LEI",
                destination_iata="DUB",
                travel_date=today + dt.timedelta(days=10),
                provider="test-provider",
                expires_at_utc=now + dt.timedelta(hours=1),
                payload_json='{"marker":"live"}',
                source_hash="live",
            )
        )
        seed_db.commit()
    finally:
        seed_db.close()

    try:
        first = run_startup_fare_memory_retention(testing_session_local, batch_size=200)
        second = run_startup_fare_memory_retention(testing_session_local, batch_size=200)

        check_db = testing_session_local()
        try:
            remaining_cache_rows = check_db.scalar(select(func.count(QuickSearchCacheEntry.id)))
            jobs = check_db.scalars(select(RevalidationJob)).all()
        finally:
            check_db.close()

        search_table = next(item for item in first["tables"] if item["table"] == "quick_search_cache_entry")
        assert first["status"] == "ok"
        assert search_table["candidates"] == 1000
        assert search_table["deleted"] == 1000
        assert search_table["batches"] == 5
        assert second["status"] == "skipped"
        assert second["reason"] == "daily_job_already_claimed"
        assert remaining_cache_rows == 1
        assert len(jobs) == 1
        assert jobs[0].status == "done"
    finally:
        engine.dispose()


def test_server_startup_schedules_fare_memory_retention_without_blocking(monkeypatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(main_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(main_module, "enable_in_process_workers", True)
    monkeypatch.setattr(main_module, "FARE_MEMORY_RETENTION_ENABLED", True)
    monkeypatch.setattr(main_module, "FARE_MEMORY_RETENTION_BATCH_SIZE", 50)
    monkeypatch.setattr(main_module, "WATCHLIST_STARTUP_REFRESH_ENABLED", False)
    monkeypatch.setattr(main_module, "FARE_MEMORY_BOOT_WARMUP_ENABLED", False)

    try:
        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            assert hasattr(app.state, "fare_memory_retention_task")

            deadline = time.time() + 2.0
            while time.time() < deadline:
                check_db = testing_session_local()
                try:
                    jobs = check_db.scalars(select(RevalidationJob)).all()
                    if jobs and jobs[0].status == "done":
                        break
                finally:
                    check_db.close()
                time.sleep(0.05)

        check_db = testing_session_local()
        try:
            jobs = check_db.scalars(select(RevalidationJob)).all()
            assert len(jobs) == 1
            assert jobs[0].job_type == "fare_memory_retention"
            assert jobs[0].status == "done"
        finally:
            check_db.close()
    finally:
        engine.dispose()
