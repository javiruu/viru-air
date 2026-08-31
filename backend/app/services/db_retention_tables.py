from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.execution import affected_row_count

SAFE_MIN_RETENTION_DAYS = {
    "price_snapshot_days": 30,
    "notification_event_days": 30,
    "security_activity_days": 30,
    "idempotency_days": 3,
}


@dataclass(frozen=True)
class TableRetentionPlan:
    label: str
    model: Any
    ts_column: Any
    retention_days: int


def validate_retention_windows(windows: dict[str, int]) -> None:
    for field_name, min_days in SAFE_MIN_RETENTION_DAYS.items():
        value = windows[field_name]
        if value < min_days:
            raise ValueError(
                f"Unsafe retention window for {field_name}: got {value}, requires >= {min_days} days"
            )


def prune_table(
    session: Session,
    plan: TableRetentionPlan,
    batch_size: int,
    dry_run: bool,
) -> dict[str, Any]:
    started = time.monotonic()
    cutoff = utc_now_naive() - timedelta(days=plan.retention_days)
    candidates = _count_candidates(session, plan.model, plan.ts_column, cutoff)

    table_result: dict[str, Any] = {
        "table": plan.label,
        "retention_days": plan.retention_days,
        "cutoff_utc": cutoff.isoformat() + "Z",
        "candidates": candidates,
        "deleted": 0,
        "batches": 0,
        "dry_run": dry_run,
    }

    if dry_run:
        table_result["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
        return table_result

    total_deleted = 0
    batches = 0
    while True:
        ids = session.scalars(select(plan.model.id).where(plan.ts_column < cutoff).limit(batch_size)).all()
        if not ids:
            break
        deleted = affected_row_count(session.execute(delete(plan.model).where(plan.model.id.in_(ids))))
        session.commit()
        total_deleted += deleted
        batches += 1

    table_result["deleted"] = total_deleted
    table_result["batches"] = batches
    table_result["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
    return table_result


def _count_candidates(session: Session, model: Any, ts_column: Any, cutoff: Any) -> int:
    stmt = select(func.count(model.id)).where(ts_column < cutoff)
    return int(session.scalar(stmt) or 0)
