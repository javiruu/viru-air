from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightOperationalRefreshLock


@dataclass(frozen=True, slots=True)
class LiveFlightRefreshLease:
    lock_token: str
    expires_at: dt.datetime


def acquire_live_flight_refresh_lease(
    db: Session,
    *,
    flight_instance_fingerprint: str,
    now: dt.datetime,
    ttl_seconds: int = 30,
) -> LiveFlightRefreshLease | None:
    expires_at = now + dt.timedelta(seconds=max(1, ttl_seconds))
    lock_token = uuid.uuid4().hex
    try:
        db.add(
            FlightOperationalRefreshLock(
                flight_instance_fingerprint=flight_instance_fingerprint,
                lock_token=lock_token,
                acquired_at=now,
                expires_at=expires_at,
                outcome=None,
            )
        )
        db.commit()
        return LiveFlightRefreshLease(lock_token=lock_token, expires_at=expires_at)
    except IntegrityError:
        db.rollback()

    taken_over = cast(
        CursorResult[Any],
        db.execute(
            update(FlightOperationalRefreshLock)
            .where(
                FlightOperationalRefreshLock.flight_instance_fingerprint
                == flight_instance_fingerprint,
                FlightOperationalRefreshLock.expires_at <= now,
            )
            .values(lock_token=lock_token, acquired_at=now, expires_at=expires_at, outcome=None)
        )
    )
    if taken_over.rowcount != 1:
        db.rollback()
        return None
    db.commit()
    return LiveFlightRefreshLease(lock_token=lock_token, expires_at=expires_at)


def get_live_flight_refresh_cooldown_outcome(
    db: Session,
    *,
    flight_instance_fingerprint: str,
    now: dt.datetime,
) -> str | None:
    return db.scalar(
        select(FlightOperationalRefreshLock.outcome).where(
            FlightOperationalRefreshLock.flight_instance_fingerprint
            == flight_instance_fingerprint,
            FlightOperationalRefreshLock.expires_at > now,
        )
    )


def hold_live_flight_refresh_cooldown(
    db: Session,
    *,
    lock_token: str,
    outcome: str,
    now: dt.datetime,
    ttl_seconds: int,
) -> bool:
    held = cast(
        CursorResult[Any],
        db.execute(
            update(FlightOperationalRefreshLock)
            .where(FlightOperationalRefreshLock.lock_token == lock_token)
            .values(
                outcome=outcome,
                expires_at=now + dt.timedelta(seconds=max(1, ttl_seconds)),
            )
        )
    )
    if held.rowcount != 1:
        db.rollback()
        return False
    db.commit()
    return True


def release_live_flight_refresh_lease(db: Session, *, lock_token: str) -> bool:
    released = cast(
        CursorResult[Any],
        db.execute(
            delete(FlightOperationalRefreshLock).where(
                FlightOperationalRefreshLock.lock_token == lock_token
            )
        )
    )
    if released.rowcount != 1:
        db.rollback()
        return False
    db.commit()
    return True
