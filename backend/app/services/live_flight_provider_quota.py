from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal, Protocol

from sqlalchemy import Connection, Engine, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightProviderQuota
from app.infrastructure.db.execution import affected_row_count


QuotaWindow = Literal["day", "month"]


@dataclass(frozen=True, slots=True)
class ProviderBudgetPolicy:
    provider: str
    window: QuotaWindow
    hard_limit: int
    units_per_request: int


class ProviderQuotaLedger(Protocol):
    def reserve(self, policy: ProviderBudgetPolicy, now: dt.datetime) -> bool: ...

    def block(self, provider: str, now: dt.datetime, seconds: int, reason: str) -> None: ...


class SqlAlchemyProviderQuotaLedger:
    def __init__(self, engine: Engine | Connection) -> None:
        self._engine = engine

    def reserve(self, policy: ProviderBudgetPolicy, now: dt.datetime) -> bool:
        window_key = _window_key(policy.window, now)
        self._ensure_row(policy.provider, window_key, now)
        if policy.units_per_request > policy.hard_limit:
            return False
        with Session(self._engine) as db, db.begin():
            db.execute(
                update(FlightProviderQuota)
                .where(
                    FlightProviderQuota.provider == policy.provider,
                    FlightProviderQuota.window_key != window_key,
                )
                .values(window_key=window_key, units_used=0, updated_at=now)
            )
            result = db.execute(
                update(FlightProviderQuota)
                .where(
                    FlightProviderQuota.provider == policy.provider,
                    FlightProviderQuota.window_key == window_key,
                    or_(
                        FlightProviderQuota.blocked_until.is_(None),
                        FlightProviderQuota.blocked_until <= now,
                    ),
                    FlightProviderQuota.units_used <= policy.hard_limit - policy.units_per_request,
                )
                .values(
                    units_used=FlightProviderQuota.units_used + policy.units_per_request,
                    updated_at=now,
                )
            )
            return affected_row_count(result) == 1

    def block(self, provider: str, now: dt.datetime, seconds: int, reason: str) -> None:
        self._ensure_row(provider, now.strftime("%Y-%m"), now)
        blocked_until = now + dt.timedelta(seconds=max(1, seconds))
        with Session(self._engine) as db, db.begin():
            db.execute(
                update(FlightProviderQuota)
                .where(
                    FlightProviderQuota.provider == provider,
                    or_(
                        FlightProviderQuota.blocked_until.is_(None),
                        FlightProviderQuota.blocked_until < blocked_until,
                    ),
                )
                .values(
                    blocked_until=blocked_until,
                    block_reason=reason[:32],
                    updated_at=now,
                )
            )

    def _ensure_row(self, provider: str, window_key: str, now: dt.datetime) -> None:
        try:
            with Session(self._engine) as db, db.begin():
                db.add(
                    FlightProviderQuota(
                        provider=provider,
                        window_key=window_key,
                        units_used=0,
                        updated_at=now,
                    )
                )
        except IntegrityError:
            return


def _window_key(window: QuotaWindow, now: dt.datetime) -> str:
    return now.strftime("%Y-%m-%d" if window == "day" else "%Y-%m")
