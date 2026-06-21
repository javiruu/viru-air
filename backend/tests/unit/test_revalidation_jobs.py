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


def test_enqueue_revalidation_job_is_idempotent_for_active_duplicates() -> None:
    db = _db()
    try:
        first, created_first = enqueue_revalidation_job(
            db,
            job_type="manual",
            target_type="offer",
            target_fingerprint="fsm_offer_123",
            provider="ryanair",
            priority=10,
        )
        second, created_second = enqueue_revalidation_job(
            db,
            job_type="manual",
            target_type="offer",
            target_fingerprint="fsm_offer_123",
            provider="ryanair",
            priority=5,
        )

        assert created_first is True
        assert created_second is False
        assert first.id == second.id
        assert db.execute(select(RevalidationJob)).scalars().all() == [first]
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_claim_next_revalidation_job_locks_single_due_job() -> None:
    db = _db()
    try:
        enqueue_revalidation_job(
            db,
            job_type="watchlist",
            target_type="search",
            target_fingerprint="fsm_search_123",
            provider="multi",
            priority=20,
            scheduled_at=dt.datetime(2026, 6, 16, 10, 0),
        )

        claimed = claim_next_revalidation_job(
            db,
            lock_token="worker-a",
            now=dt.datetime(2026, 6, 16, 10, 1),
        )
        duplicate_claim = claim_next_revalidation_job(
            db,
            lock_token="worker-b",
            now=dt.datetime(2026, 6, 16, 10, 1),
        )

        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.lock_token == "worker-a"
        assert claimed.attempt_count == 1
        assert duplicate_claim is None
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_complete_revalidation_job_requires_matching_lock_token() -> None:
    db = _db()
    try:
        job, _ = enqueue_revalidation_job(
            db,
            job_type="manual",
            target_type="route",
            target_fingerprint="route_lei_dub_2026-06-16",
            provider="multi",
            scheduled_at=dt.datetime(2026, 6, 16, 10, 59),
        )
        claim_next_revalidation_job(db, lock_token="worker-a", now=dt.datetime(2026, 6, 16, 11, 0))

        rejected = complete_revalidation_job(
            db,
            job_id=job.id,
            lock_token="worker-b",
            now=dt.datetime(2026, 6, 16, 11, 1),
        )
        completed = complete_revalidation_job(
            db,
            job_id=job.id,
            lock_token="worker-a",
            now=dt.datetime(2026, 6, 16, 11, 2),
        )

        assert rejected is None
        assert completed is not None
        assert completed.status == "done"
        assert completed.finished_at == dt.datetime(2026, 6, 16, 11, 2)
        assert completed.lock_token is None
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_failed_job_can_be_reenqueued_after_terminal_state() -> None:
    db = _db()
    try:
        job, _ = enqueue_revalidation_job(
            db,
            job_type="alert_threshold",
            target_type="offer",
            target_fingerprint="fsm_offer_999",
            provider="duffel",
            scheduled_at=dt.datetime(2026, 6, 16, 11, 59),
        )
        claim_next_revalidation_job(db, lock_token="worker-a", now=dt.datetime(2026, 6, 16, 12, 0))
        failed = fail_revalidation_job(
            db,
            job_id=job.id,
            lock_token="worker-a",
            error_code="provider_timeout",
            now=dt.datetime(2026, 6, 16, 12, 1),
        )
        reenqueued, created = enqueue_revalidation_job(
            db,
            job_type="alert_threshold",
            target_type="offer",
            target_fingerprint="fsm_offer_999",
            provider="duffel",
            scheduled_at=dt.datetime(2026, 6, 16, 12, 2),
        )

        jobs = db.execute(select(RevalidationJob).order_by(RevalidationJob.created_at.asc(), RevalidationJob.id.asc())).scalars().all()

        assert failed is not None
        assert failed.status == "failed"
        assert failed.last_error_code == "provider_timeout"
        assert created is True
        assert reenqueued.id != job.id
        assert len(jobs) == 2
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
