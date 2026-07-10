from __future__ import annotations

import json
from typing import Callable
from uuid import uuid4

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import RevalidationJob
from app.services.fare_memory_retention import (
    FareMemoryRetentionOptions,
    retention_result_to_payload,
    run_fare_memory_retention,
)
from app.services.revalidation_jobs import complete_revalidation_job, fail_revalidation_job

RETENTION_JOB_TYPE = "fare_memory_retention"
RETENTION_TARGET_TYPE = "fare_memory"
RETENTION_PROVIDER = "internal"
RETENTION_PRIORITY = 500


def run_startup_fare_memory_retention(
    session_factory: Callable[[], Session],
    *,
    batch_size: int,
) -> dict:
    now_utc = utc_now_naive()
    lock_token = str(uuid4())
    with session_factory() as db:
        job = _claim_daily_retention_job(db, now_utc=now_utc, lock_token=lock_token, batch_size=batch_size)
        if job is None:
            return {
                "status": "skipped",
                "reason": "daily_job_already_claimed",
                "dry_run": False,
                "batch_size": batch_size,
            }
        try:
            result = run_fare_memory_retention(
                db,
                FareMemoryRetentionOptions(
                    dry_run=False,
                    batch_size=batch_size,
                    today=now_utc.date(),
                    now_utc=now_utc,
                ),
            )
        except (SQLAlchemyError, ValueError) as exc:
            fail_revalidation_job(
                db,
                job_id=job.id,
                lock_token=lock_token,
                error_code=type(exc).__name__,
                now=utc_now_naive(),
            )
            raise
        complete_revalidation_job(
            db,
            job_id=job.id,
            lock_token=lock_token,
            final_status="done",
            now=utc_now_naive(),
        )
        return {
            "status": "ok",
            "job_id": job.id,
            "batch_size": batch_size,
            **retention_result_to_payload(result),
        }


def _claim_daily_retention_job(
    db: Session,
    *,
    now_utc,
    lock_token: str,
    batch_size: int,
) -> RevalidationJob | None:
    job = RevalidationJob(
        id=f"fare-memory-retention-{now_utc.date().isoformat()}",
        job_type=RETENTION_JOB_TYPE,
        target_type=RETENTION_TARGET_TYPE,
        target_fingerprint=f"retention:{now_utc.date().isoformat()}",
        provider=RETENTION_PROVIDER,
        priority=RETENTION_PRIORITY,
        status="running",
        scheduled_at=now_utc,
        started_at=now_utc,
        lock_token=lock_token,
        lock_acquired_at=now_utc,
        attempt_count=1,
        payload_json=json.dumps(
            {
                "reason": "startup_fare_memory_retention",
                "batch_size": batch_size,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(job)
    return job
