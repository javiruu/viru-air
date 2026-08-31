from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import HotelSweepLease


def _rowcount(result: object) -> int:
    if not isinstance(result, CursorResult):
        raise RuntimeError("hotel_sweep_lease_update_result_invalid")
    return result.rowcount


@dataclass(frozen=True, slots=True)
class HotelSweepLeaseToken:
    fingerprint: str
    lock_token: str
    lease_expires_at: dt.datetime


def stay_query_fingerprint(
    *,
    provider: str,
    operation: str,
    canonical_hotel_id: str,
    provider_hotel_id: str,
    check_in: object,
    check_out: object,
    guests: int,
    currency: str,
    room_label: str | None = None,
    meal_plan: str | None = None,
    cancellation_policy: str | None = None,
    rooms: int = 1,
    adults: int | None = None,
    children_ages: tuple[int, ...] = (),
    room_id: str | None = None,
) -> str:
    """Hash all price-affecting StayQuery dimensions in canonical JSON."""
    payload = {
        "provider": provider,
        "operation": operation,
        "canonical_hotel_id": canonical_hotel_id,
        "provider_hotel_id": provider_hotel_id,
        "check_in": str(check_in),
        "check_out": str(check_out),
        "guests": guests,
        "rooms": rooms,
        "adults": adults if adults is not None else guests,
        "children_ages": list(children_ages),
        "room_id": room_id,
        "currency": currency,
        "room_label": room_label,
        "meal_plan": meal_plan,
        "cancellation_policy": cancellation_policy,
    }
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class HotelSweepLeaseStore:
    def __init__(self, db: Session) -> None:
        self._db = db

    def acquire(
        self,
        fingerprint: str,
        *,
        now: dt.datetime,
        ttl_seconds: int = 60,
    ) -> HotelSweepLeaseToken | None:
        ttl = max(1, ttl_seconds)
        token = uuid.uuid4().hex
        expires_at = now + dt.timedelta(seconds=ttl)
        try:
            self._db.add(
                HotelSweepLease(
                    fingerprint=fingerprint,
                    status="running",
                    lock_token=token,
                    lock_acquired_at=now,
                    lease_expires_at=expires_at,
                    attempt_count=1,
                    updated_at=now,
                )
            )
            self._db.commit()
            return HotelSweepLeaseToken(fingerprint, token, expires_at)
        except IntegrityError:
            self._db.rollback()

        result = self._db.execute(
            update(HotelSweepLease)
            .where(
                HotelSweepLease.fingerprint == fingerprint,
                or_(
                    HotelSweepLease.status != "running",
                    HotelSweepLease.lease_expires_at <= now,
                ),
            )
            .values(
                status="running",
                lock_token=token,
                lock_acquired_at=now,
                lease_expires_at=expires_at,
                attempt_count=HotelSweepLease.attempt_count + 1,
                last_error_code=None,
                finished_at=None,
                updated_at=now,
            )
        )
        if _rowcount(result) != 1:
            self._db.rollback()
            return None
        self._db.commit()
        return HotelSweepLeaseToken(fingerprint, token, expires_at)

    def renew(
        self,
        lease: HotelSweepLeaseToken,
        *,
        now: dt.datetime,
        ttl_seconds: int = 60,
    ) -> bool:
        result = self._db.execute(
            update(HotelSweepLease)
            .where(
                HotelSweepLease.fingerprint == lease.fingerprint,
                HotelSweepLease.lock_token == lease.lock_token,
                HotelSweepLease.lease_expires_at > now,
            )
            .values(
                lease_expires_at=now + dt.timedelta(seconds=max(1, ttl_seconds)),
                updated_at=now,
            )
        )
        affected_rows = _rowcount(result)
        self._db.commit() if affected_rows == 1 else self._db.rollback()
        return affected_rows == 1

    def finish(
        self,
        lease: HotelSweepLeaseToken,
        *,
        status: str,
        now: dt.datetime,
        provider_run_id: str | None = None,
        error_code: str | None = None,
        commit: bool = True,
    ) -> bool:
        if status not in {"done", "partial", "skipped", "failed"}:
            raise ValueError("invalid_hotel_sweep_lease_status")
        result = self._db.execute(
            update(HotelSweepLease)
            .where(
                HotelSweepLease.fingerprint == lease.fingerprint,
                HotelSweepLease.lock_token == lease.lock_token,
                HotelSweepLease.lease_expires_at > now,
                HotelSweepLease.status == "running",
            )
            .values(
                status=status,
                lease_expires_at=None,
                finished_at=now,
                last_provider_run_id=provider_run_id,
                last_error_code=error_code,
                updated_at=now,
            )
        )
        affected_rows = _rowcount(result)
        if affected_rows == 1:
            self._db.flush()
            if commit:
                self._db.commit()
        elif commit:
            self._db.rollback()
        return affected_rows == 1

    def owns_active_lease(self, lease: HotelSweepLeaseToken, *, now: dt.datetime) -> bool:
        return self._db.scalar(
            select(HotelSweepLease.fingerprint).where(
                HotelSweepLease.fingerprint == lease.fingerprint,
                HotelSweepLease.lock_token == lease.lock_token,
                HotelSweepLease.lease_expires_at > now,
                HotelSweepLease.status == "running",
            )
        ) is not None
