import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, RevalidationJob
from app.services.revalidation_jobs import (
    claim_next_revalidation_job,
    complete_revalidation_job,
    enqueue_revalidation_job,
    fail_revalidation_job,
)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def test_enqueue_revalidation_job_dedupes_running_job() -> None:
    db = _db()
    try:
        # Given
        original, created_original = enqueue_revalidation_job(
            db,
            job_type="startup_refresh",
            target_type="route",
            target_fingerprint="route:LEI:DUB:2026-06-20",
            provider="multi",
            scheduled_at=dt.datetime(2026, 6, 16, 10, 0),
        )
        running = claim_next_revalidation_job(db, lock_token="worker-a", now=dt.datetime(2026, 6, 16, 10, 1))

        # When
        duplicate, created_duplicate = enqueue_revalidation_job(
            db,
            job_type="startup_refresh",
            target_type="route",
            target_fingerprint="route:LEI:DUB:2026-06-20",
            provider="multi",
            scheduled_at=dt.datetime(2026, 6, 16, 10, 2),
        )

        # Then
        jobs = db.execute(select(RevalidationJob)).scalars().all()
        assert created_original is True
        assert running is not None
        assert running.status == "running"
        assert created_duplicate is False
        assert duplicate.id == original.id
        assert len(jobs) == 1
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_completed_revalidation_job_can_be_reenqueued() -> None:
    db = _db()
    try:
        # Given
        original, _ = enqueue_revalidation_job(
            db,
            job_type="startup_refresh",
            target_type="route",
            target_fingerprint="route:AGP:FCO:2026-06-21",
            provider="multi",
            scheduled_at=dt.datetime(2026, 6, 16, 10, 0),
        )
        claim_next_revalidation_job(db, lock_token="worker-a", now=dt.datetime(2026, 6, 16, 10, 1))
        completed = complete_revalidation_job(
            db,
            job_id=original.id,
            lock_token="worker-a",
            now=dt.datetime(2026, 6, 16, 10, 2),
        )

        # When
        next_job, created_next = enqueue_revalidation_job(
            db,
            job_type="startup_refresh",
            target_type="route",
            target_fingerprint="route:AGP:FCO:2026-06-21",
            provider="multi",
            scheduled_at=dt.datetime(2026, 6, 16, 10, 3),
        )

        # Then
        jobs = db.execute(select(RevalidationJob).order_by(RevalidationJob.created_at.asc(), RevalidationJob.id.asc())).scalars().all()
        assert completed is not None
        assert completed.status == "done"
        assert created_next is True
        assert next_job.id != original.id
        assert len(jobs) == 2
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_failed_revalidation_job_retry_dedupes_existing_active_retry() -> None:
    db = _db()
    try:
        # Given
        original, _ = enqueue_revalidation_job(
            db,
            job_type="startup_refresh",
            target_type="route",
            target_fingerprint="route:MAD:DUB:2026-06-22",
            provider="multi",
            scheduled_at=dt.datetime(2026, 6, 16, 10, 0),
        )
        claim_next_revalidation_job(db, lock_token="worker-a", now=dt.datetime(2026, 6, 16, 10, 1))
        failed = fail_revalidation_job(
            db,
            job_id=original.id,
            lock_token="worker-a",
            error_code="provider_timeout",
            now=dt.datetime(2026, 6, 16, 10, 2),
        )
        retry, created_retry = enqueue_revalidation_job(
            db,
            job_type="startup_refresh",
            target_type="route",
            target_fingerprint="route:MAD:DUB:2026-06-22",
            provider="multi",
            scheduled_at=dt.datetime(2026, 6, 16, 10, 3),
        )

        # When
        duplicate_retry, created_duplicate = enqueue_revalidation_job(
            db,
            job_type="startup_refresh",
            target_type="route",
            target_fingerprint="route:MAD:DUB:2026-06-22",
            provider="multi",
            scheduled_at=dt.datetime(2026, 6, 16, 10, 4),
        )

        # Then
        jobs = db.execute(select(RevalidationJob).order_by(RevalidationJob.created_at.asc(), RevalidationJob.id.asc())).scalars().all()
        assert failed is not None
        assert failed.status == "failed"
        assert created_retry is True
        assert created_duplicate is False
        assert duplicate_retry.id == retry.id
        assert len(jobs) == 2
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
