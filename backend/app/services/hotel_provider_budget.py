from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import HotelProviderBudget, HotelProviderBudgetReservation


def _rowcount(result: object) -> int:
    if not isinstance(result, CursorResult):
        raise RuntimeError("hotel_budget_update_result_invalid")
    return result.rowcount


@dataclass(frozen=True, slots=True)
class HotelBudgetPolicy:
    provider: str
    operation: str
    window: str = "day"
    hard_limit: int = 0
    units_per_request: int = 1
    source: str = "local_config"


@dataclass(frozen=True, slots=True)
class HotelBudgetReservation:
    allowed: bool
    reason: str
    provider: str
    operation: str
    window_key: str
    units_reserved: int
    reservation_id: str | None = None


class HotelBudgetDeniedError(RuntimeError):
    def __init__(self, provider: str, operation: str) -> None:
        self.provider = provider
        self.operation = operation
        super().__init__(f"hotel_provider_budget_denied:{provider}:{operation}")


class HotelProviderBudgetLedger:
    """Windowed, database-backed budget with an outstanding reservation state.

    ``units_reserved`` protects requests between admission and completion;
    ``units_used`` records requests that actually reached the adapter. Both
    transitions are atomic SQL updates, so callers can use this with separate
    worker sessions without a process-local lock.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def reserve(
        self,
        policy: HotelBudgetPolicy,
        *,
        now: dt.datetime | None = None,
    ) -> HotelBudgetReservation:
        now = now or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        if policy.hard_limit < 0 or policy.units_per_request <= 0:
            raise ValueError("invalid_hotel_budget_policy")

        window_key, expires_at = _window_key(policy.window, now)
        row = self._ensure_row(policy, window_key, expires_at, now)
        if row.hard_limit < policy.units_per_request:
            self._db.flush()
            return _denied(policy, window_key)

        # Admission is atomic. Existing reservations and consumed units both
        # count against the hard limit; no read/modify/write race is used.
        result = self._db.execute(
            update(HotelProviderBudget)
            .where(
                HotelProviderBudget.id == row.id,
                HotelProviderBudget.units_used + HotelProviderBudget.units_reserved
                <= row.hard_limit - policy.units_per_request,
            )
            .values(
                units_reserved=HotelProviderBudget.units_reserved + policy.units_per_request,
                updated_at=now,
            )
        )
        self._db.flush()
        if _rowcount(result) != 1:
            return _denied(policy, window_key)
        reservation_id = str(uuid4())
        self._db.add(
            HotelProviderBudgetReservation(
                id=reservation_id,
                budget_id=row.id,
                units=policy.units_per_request,
                status="reserved",
                created_at=now,
                updated_at=now,
            )
        )
        self._db.flush()
        return HotelBudgetReservation(
            True,
            "reserved",
            policy.provider,
            policy.operation,
            window_key,
            policy.units_per_request,
            reservation_id,
        )

    def consume(
        self,
        reservation: HotelBudgetReservation,
        *,
        now: dt.datetime | None = None,
    ) -> bool:
        """Move an admitted request from outstanding to used atomically."""
        return self._transition(reservation, "used", now=now)

    def release(
        self,
        reservation: HotelBudgetReservation,
        *,
        now: dt.datetime | None = None,
    ) -> bool:
        """Return an admission that never reached the provider adapter atomically."""
        return self._transition(reservation, "released", now=now)

    def _transition(
        self,
        reservation: HotelBudgetReservation,
        status: str,
        *,
        now: dt.datetime | None = None,
    ) -> bool:
        if (
            not reservation.allowed
            or reservation.units_reserved <= 0
            or reservation.reservation_id is None
            or status not in {"used", "released"}
        ):
            return False
        now = now or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        try:
            with self._db.begin_nested():
                reservation_row = self._db.scalar(
                    select(HotelProviderBudgetReservation).where(
                        HotelProviderBudgetReservation.id == reservation.reservation_id,
                        HotelProviderBudgetReservation.status == "reserved",
                    )
                )
                if reservation_row is None:
                    raise RuntimeError("hotel_budget_reservation_not_available")
                result = self._db.execute(
                    update(HotelProviderBudgetReservation)
                    .where(
                        HotelProviderBudgetReservation.id == reservation.reservation_id,
                        HotelProviderBudgetReservation.status == "reserved",
                    )
                    .values(status=status, updated_at=now)
                )
                if _rowcount(result) != 1:
                    raise RuntimeError("hotel_budget_reservation_transition_failed")
                values = {
                    "units_reserved": HotelProviderBudget.units_reserved - reservation.units_reserved,
                    "updated_at": now,
                }
                if status == "used":
                    values["units_used"] = HotelProviderBudget.units_used + reservation.units_reserved
                else:
                    values["units_released"] = HotelProviderBudget.units_released + reservation.units_reserved
                budget_result = self._db.execute(
                    update(HotelProviderBudget)
                    .where(
                        HotelProviderBudget.id == reservation_row.budget_id,
                        HotelProviderBudget.units_reserved >= reservation.units_reserved,
                    )
                    .values(**values)
                )
                if _rowcount(budget_result) != 1:
                    raise RuntimeError("hotel_budget_transition_failed")
                self._db.flush()
        except RuntimeError:
            return False
        return True

    def _ensure_row(
        self,
        policy: HotelBudgetPolicy,
        window_key: str,
        expires_at: dt.datetime,
        now: dt.datetime,
    ) -> HotelProviderBudget:
        row = self._db.scalar(
            select(HotelProviderBudget).where(
                HotelProviderBudget.provider == policy.provider,
                HotelProviderBudget.operation == policy.operation,
                HotelProviderBudget.window_key == window_key,
            )
        )
        if row is not None:
            if row.hard_limit != policy.hard_limit or row.source != policy.source:
                row.hard_limit = policy.hard_limit
                row.source = policy.source
                row.updated_at = now
                self._db.flush()
            return row

        # A nested transaction confines a uniqueness race to a savepoint. It
        # avoids rolling back unrelated work in the caller's transaction, then
        # re-reads the winner inserted by another worker.
        try:
            with self._db.begin_nested():
                self._db.add(
                    HotelProviderBudget(
                        id=str(uuid4()),
                        provider=policy.provider,
                        operation=policy.operation,
                        window_key=window_key,
                        hard_limit=policy.hard_limit,
                        window_expires_at=expires_at,
                        source=policy.source,
                        updated_at=now,
                    )
                )
                self._db.flush()
        except IntegrityError:
            pass

        row = self._db.scalar(
            select(HotelProviderBudget).where(
                HotelProviderBudget.provider == policy.provider,
                HotelProviderBudget.operation == policy.operation,
                HotelProviderBudget.window_key == window_key,
            )
        )
        if row is None:
            raise RuntimeError("hotel_budget_row_unavailable")
        return row


def _denied(policy: HotelBudgetPolicy, window_key: str) -> HotelBudgetReservation:
    return HotelBudgetReservation(
        False,
        "skipped_budget",
        policy.provider,
        policy.operation,
        window_key,
        0,
        None,
    )


def _window_key(window: str, now: dt.datetime) -> tuple[str, dt.datetime]:
    if window == "month":
        return now.strftime("%Y-%m"), (now.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    if window != "day":
        raise ValueError("unsupported_hotel_budget_window")
    next_day = now.date() + dt.timedelta(days=1)
    return now.strftime("%Y-%m-%d"), dt.datetime.combine(next_day, dt.time.min)


def policy_from_env(provider: str, operation: str) -> HotelBudgetPolicy:
    normalized = provider.upper().replace("-", "_")
    raw_limit = os.getenv(
        f"HOTEL_PROVIDER_{normalized}_DAILY_REQUEST_BUDGET",
        "0",
    )
    try:
        hard_limit = max(0, int(raw_limit))
    except ValueError:
        hard_limit = 0
    return HotelBudgetPolicy(
        provider=provider,
        operation=operation,
        window="day",
        hard_limit=hard_limit,
        units_per_request=1,
        source="local_config",
    )
