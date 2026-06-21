from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import RevalidationJob

ACTIVE_REVALIDATION_JOB_STATUSES = {"queued", "running"}
FINAL_REVALIDATION_JOB_STATUSES = {"done", "skipped", "failed"}


def enqueue_revalidation_job(
    db: Session,
    *,
    job_type: str,
    target_type: str,
    target_fingerprint: str,
    provider: str | None,
    priority: int = 100,
    scheduled_at=None,
    payload: dict[str, Any] | None = None,
) -> tuple[RevalidationJob, bool]:
    scheduled_at = scheduled_at or utc_now_naive()
    existing = db.scalar(
        select(RevalidationJob)
        .where(RevalidationJob.job_type == job_type)
        .where(RevalidationJob.target_type == target_type)
        .where(RevalidationJob.target_fingerprint == target_fingerprint)
        .where(RevalidationJob.provider == provider)
        .where(RevalidationJob.status.in_(tuple(ACTIVE_REVALIDATION_JOB_STATUSES)))
        .order_by(RevalidationJob.created_at.desc(), RevalidationJob.id.desc())
        .limit(1)
    )
    if existing is not None:
        return existing, False

    job = RevalidationJob(
        job_type=job_type,
        target_type=target_type,
        target_fingerprint=target_fingerprint,
        provider=provider,
        priority=int(priority),
        status="queued",
        scheduled_at=scheduled_at,
        payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True) if payload is not None else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job, True


def find_active_revalidation_job(
    db: Session,
    *,
    target_type: str,
    target_fingerprint: str,
    provider: str | None,
) -> RevalidationJob | None:
    return db.scalar(
        select(RevalidationJob)
        .where(RevalidationJob.target_type == target_type)
        .where(RevalidationJob.target_fingerprint == target_fingerprint)
        .where(RevalidationJob.provider == provider)
        .where(RevalidationJob.status.in_(tuple(ACTIVE_REVALIDATION_JOB_STATUSES)))
        .order_by(RevalidationJob.created_at.desc(), RevalidationJob.id.desc())
        .limit(1)
    )


def build_due_revalidation_job_query(
    *,
    now=None,
    job_types: tuple[str, ...] | None = None,
    target_types: tuple[str, ...] | None = None,
) -> Select[tuple[RevalidationJob]]:
    reference_now = now or utc_now_naive()
    query = (
        select(RevalidationJob)
        .where(RevalidationJob.status == "queued")
        .where(RevalidationJob.scheduled_at <= reference_now)
        .order_by(
            RevalidationJob.priority.asc(),
            RevalidationJob.scheduled_at.asc(),
            RevalidationJob.created_at.asc(),
            RevalidationJob.id.asc(),
        )
    )
    if job_types:
        query = query.where(RevalidationJob.job_type.in_(job_types))
    if target_types:
        query = query.where(RevalidationJob.target_type.in_(target_types))
    return query


def claim_next_revalidation_job(
    db: Session,
    *,
    lock_token: str,
    now=None,
    job_types: tuple[str, ...] | None = None,
    target_types: tuple[str, ...] | None = None,
) -> RevalidationJob | None:
    reference_now = now or utc_now_naive()
    candidates = db.scalars(
        build_due_revalidation_job_query(
            now=reference_now,
            job_types=job_types,
            target_types=target_types,
        ).limit(10)
    ).all()
    for candidate in candidates:
        claimed = db.execute(
            update(RevalidationJob)
            .where(RevalidationJob.id == candidate.id)
            .where(RevalidationJob.status == "queued")
            .values(
                status="running",
                lock_token=lock_token,
                lock_acquired_at=reference_now,
                started_at=reference_now,
                attempt_count=RevalidationJob.attempt_count + 1,
            )
        )
        if claimed.rowcount != 1:
            db.rollback()
            continue
        db.commit()
        return db.get(RevalidationJob, candidate.id)
    return None


def claim_revalidation_job(
    db: Session,
    *,
    job_id: str,
    lock_token: str,
    now=None,
) -> RevalidationJob | None:
    reference_now = now or utc_now_naive()
    claimed = db.execute(
        update(RevalidationJob)
        .where(RevalidationJob.id == job_id)
        .where(RevalidationJob.status == "queued")
        .values(
            status="running",
            lock_token=lock_token,
            lock_acquired_at=reference_now,
            started_at=reference_now,
            attempt_count=RevalidationJob.attempt_count + 1,
        )
    )
    if claimed.rowcount != 1:
        db.rollback()
        return None
    db.commit()
    return db.get(RevalidationJob, job_id)


def complete_revalidation_job(
    db: Session,
    *,
    job_id: str,
    lock_token: str,
    final_status: str = "done",
    now=None,
) -> RevalidationJob | None:
    if final_status not in {"done", "skipped"}:
        raise ValueError(f"Unsupported final status: {final_status}")
    reference_now = now or utc_now_naive()
    updated = db.execute(
        update(RevalidationJob)
        .where(RevalidationJob.id == job_id)
        .where(RevalidationJob.status == "running")
        .where(RevalidationJob.lock_token == lock_token)
        .values(
            status=final_status,
            finished_at=reference_now,
            last_error_code=None,
            lock_token=None,
        )
    )
    if updated.rowcount != 1:
        db.rollback()
        return None
    db.commit()
    return db.get(RevalidationJob, job_id)


def fail_revalidation_job(
    db: Session,
    *,
    job_id: str,
    lock_token: str,
    error_code: str,
    now=None,
) -> RevalidationJob | None:
    reference_now = now or utc_now_naive()
    updated = db.execute(
        update(RevalidationJob)
        .where(RevalidationJob.id == job_id)
        .where(RevalidationJob.status == "running")
        .where(RevalidationJob.lock_token == lock_token)
        .values(
            status="failed",
            finished_at=reference_now,
            last_error_code=error_code,
            lock_token=None,
        )
    )
    if updated.rowcount != 1:
        db.rollback()
        return None
    db.commit()
    return db.get(RevalidationJob, job_id)
