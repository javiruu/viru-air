from __future__ import annotations

import datetime as dt
import logging
from threading import Lock
from typing import Any, cast

from sqlalchemy import delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightOperationalSnapshot


logger = logging.getLogger("app.live_flight.retention")
_prune_lock = Lock()
_last_pruned_at: dt.datetime | None = None


def prune_old_operational_snapshots(
    db: Session,
    *,
    now: dt.datetime,
    retention_days: int = 30,
    cadence_seconds: int = 21600,
) -> int:
    global _last_pruned_at
    with _prune_lock:
        if (
            cadence_seconds > 0
            and _last_pruned_at is not None
            and (now - _last_pruned_at).total_seconds() < cadence_seconds
        ):
            return 0
        cutoff = now - dt.timedelta(days=max(1, retention_days))
        try:
            deleted = cast(
                CursorResult[Any],
                db.execute(
                    delete(FlightOperationalSnapshot).where(
                        FlightOperationalSnapshot.observed_at < cutoff
                    )
                )
            )
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.warning("live_flight_retention outcome=failed", exc_info=True)
            return 0
        _last_pruned_at = now
        count = int(deleted.rowcount or 0)
        logger.info("live_flight_retention outcome=ok deleted=%s", count)
        return count
