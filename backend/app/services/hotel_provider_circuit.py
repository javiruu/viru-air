from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import case, select, update
from sqlalchemy.engine import Connection, CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import HotelProviderCircuit


def _rowcount(result: object) -> int:
    if not isinstance(result, CursorResult):
        raise RuntimeError("hotel_circuit_update_result_invalid")
    return result.rowcount


_FAILURE_OUTCOMES = frozenset(
    {
        "timeout",
        "rate_limited",
        "network_error",
        "provider_5xx",
        "unavailable",
        "failed",
    }
)


@dataclass(frozen=True, slots=True)
class HotelCircuitPermit:
    provider: str
    operation: str
    probe_token: str | None = None
    state_version: int = 0


@dataclass(frozen=True, slots=True)
class HotelCircuitAdmission:
    allowed: bool
    reason: str
    permit: HotelCircuitPermit | None = None


class HotelProviderCircuitStore:
    """Cross-process circuit breaker with a transaction isolated from callers.

    The caller's session is used only to obtain its bind. Every admission and
    outcome is committed by a short-lived private session, so circuit state
    cannot commit, rollback, or expire unrelated sweep work.
    """

    def __init__(self, db: Session) -> None:
        bind = db.get_bind()
        # A caller may be backed by a Connection (not an Engine). Use the
        # engine in that case so the breaker cannot join the caller's open
        # transaction.
        if isinstance(bind, Connection):
            bind = bind.engine
        self._session_factory = sessionmaker(
            bind=bind,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def admit(
        self,
        provider: str,
        operation: str,
        *,
        now: dt.datetime,
        failure_threshold: int | None = None,
        cooldown_seconds: int | None = None,
        probe_ttl_seconds: int | None = None,
    ) -> HotelCircuitAdmission:
        threshold = max(1, failure_threshold or _env_int("HOTEL_PROVIDER_CIRCUIT_FAILURE_THRESHOLD", 3))
        cooldown = max(1, cooldown_seconds or _env_int("HOTEL_PROVIDER_CIRCUIT_RECOVERY_SECONDS", 300))
        probe_ttl = max(1, probe_ttl_seconds or _env_int("HOTEL_PROVIDER_CIRCUIT_PROBE_TTL_SECONDS", 30))

        with self._session_factory() as db:
            row = self._ensure_row(db, provider, operation, threshold, cooldown, now)

            if row.status == "closed":
                # Closed admissions are read-only. Several in-flight provider
                # calls may legitimately share this generation; failures are
                # accumulated atomically and a success cannot reset a newer
                # generation after a failure has been recorded.
                db.rollback()
                return HotelCircuitAdmission(
                    True,
                    "allowed",
                    HotelCircuitPermit(provider, operation, state_version=row.state_version),
                )

            if row.status == "open" and (row.next_probe_at is None or row.next_probe_at <= now):
                return self._claim_probe(
                    db,
                    provider,
                    operation,
                    now=now,
                    probe_ttl=probe_ttl,
                    expected_status="open",
                    expected_version=row.state_version,
                )

            if row.status == "half_open" and row.probe_expires_at is not None and row.probe_expires_at <= now:
                # A crashed/partitioned worker must not strand the circuit in
                # half-open forever. Reclaim its expired probe atomically.
                return self._claim_probe(
                    db,
                    provider,
                    operation,
                    now=now,
                    probe_ttl=probe_ttl,
                    expected_status="half_open",
                    expected_version=row.state_version,
                )

            db.rollback()
            return HotelCircuitAdmission(False, "skipped_circuit")

    def record(
        self,
        permit: HotelCircuitPermit,
        outcome: str,
        *,
        now: dt.datetime,
        cooldown_seconds: int | None = None,
    ) -> bool:
        if outcome not in _FAILURE_OUTCOMES and outcome not in {"success", "empty"}:
            outcome = "failed"

        with self._session_factory() as db:
            row = db.scalar(
                select(HotelProviderCircuit).where(
                    HotelProviderCircuit.provider == permit.provider,
                    HotelProviderCircuit.operation == permit.operation,
                )
            )
            if row is None:
                db.rollback()
                return False
            cooldown = max(1, cooldown_seconds or row.cooldown_seconds)

            if outcome in {"success", "empty"}:
                conditions = [
                    HotelProviderCircuit.provider == permit.provider,
                    HotelProviderCircuit.operation == permit.operation,
                ]
                conditions.append(HotelProviderCircuit.state_version == permit.state_version)
                values = {
                    "status": "closed",
                    "consecutive_failures": 0,
                    "opened_at": None,
                    "next_probe_at": None,
                    "probe_token": None,
                    "probe_expires_at": None,
                    "last_error_code": None,
                    "state_version": HotelProviderCircuit.state_version + 1,
                    "updated_at": now,
                }
                if permit.probe_token is not None:
                    conditions.extend(
                        [
                            HotelProviderCircuit.status == "half_open",
                            HotelProviderCircuit.probe_token == permit.probe_token,
                            HotelProviderCircuit.probe_expires_at > now,
                        ]
                    )
                else:
                    conditions.append(HotelProviderCircuit.status == "closed")
                result = db.execute(update(HotelProviderCircuit).where(*conditions).values(**values))
                if _rowcount(result) == 1:
                    db.commit()
                    return True
                db.rollback()
                return False

            # A failed half-open probe reopens the circuit. A closed circuit
            # counts failures only if this permit still represents its state.
            if permit.probe_token is not None:
                result = db.execute(
                    update(HotelProviderCircuit)
                    .where(
                        HotelProviderCircuit.provider == permit.provider,
                        HotelProviderCircuit.operation == permit.operation,
                        HotelProviderCircuit.status == "half_open",
                        HotelProviderCircuit.probe_token == permit.probe_token,
                        HotelProviderCircuit.probe_expires_at > now,
                        HotelProviderCircuit.state_version == permit.state_version,
                    )
                    .values(
                        status="open",
                        opened_at=now,
                        next_probe_at=now + dt.timedelta(seconds=cooldown),
                        probe_token=None,
                        probe_expires_at=None,
                        consecutive_failures=HotelProviderCircuit.consecutive_failures + 1,
                        last_error_code=outcome,
                        state_version=HotelProviderCircuit.state_version + 1,
                        updated_at=now,
                    )
                )
            else:
                next_failure_count = HotelProviderCircuit.consecutive_failures + 1
                result = db.execute(
                    update(HotelProviderCircuit)
                    .where(
                        HotelProviderCircuit.provider == permit.provider,
                        HotelProviderCircuit.operation == permit.operation,
                        HotelProviderCircuit.status == "closed",
                    )
                    .values(
                        consecutive_failures=next_failure_count,
                        status=case(
                            (
                                next_failure_count >= HotelProviderCircuit.failure_threshold,
                                "open",
                            ),
                            else_="closed",
                        ),
                        opened_at=case(
                            (
                                next_failure_count >= HotelProviderCircuit.failure_threshold,
                                now,
                            ),
                            else_=None,
                        ),
                        next_probe_at=case(
                            (
                                next_failure_count >= HotelProviderCircuit.failure_threshold,
                                now + dt.timedelta(seconds=cooldown),
                            ),
                            else_=None,
                        ),
                        last_error_code=outcome,
                        state_version=HotelProviderCircuit.state_version + 1,
                        updated_at=now,
                    )
                )
            if _rowcount(result) == 1:
                db.commit()
                return True
            db.rollback()
            return False

    @staticmethod
    def _claim_probe(
        db: Session,
        provider: str,
        operation: str,
        *,
        now: dt.datetime,
        probe_ttl: int,
        expected_status: str,
        expected_version: int,
    ) -> HotelCircuitAdmission:
        probe_token = uuid4().hex
        conditions = [
            HotelProviderCircuit.provider == provider,
            HotelProviderCircuit.operation == operation,
            HotelProviderCircuit.status == expected_status,
            HotelProviderCircuit.state_version == expected_version,
        ]
        if expected_status == "open":
            conditions.append(
                (HotelProviderCircuit.next_probe_at.is_(None))
                | (HotelProviderCircuit.next_probe_at <= now)
            )
        else:
            conditions.append(HotelProviderCircuit.probe_expires_at <= now)
        result = db.execute(
            update(HotelProviderCircuit)
            .where(*conditions)
            .values(
                status="half_open",
                probe_token=probe_token,
                probe_expires_at=now + dt.timedelta(seconds=probe_ttl),
                state_version=HotelProviderCircuit.state_version + 1,
                updated_at=now,
            )
        )
        if _rowcount(result) != 1:
            db.rollback()
            return HotelCircuitAdmission(False, "skipped_circuit")
        db.commit()
        return HotelCircuitAdmission(
            True,
            "half_open_probe",
            HotelCircuitPermit(
                provider,
                operation,
                probe_token,
                expected_version + 1,
            ),
        )

    @staticmethod
    def _ensure_row(
        db: Session,
        provider: str,
        operation: str,
        threshold: int,
        cooldown: int,
        now: dt.datetime,
    ) -> HotelProviderCircuit:
        row = db.scalar(
            select(HotelProviderCircuit).where(
                HotelProviderCircuit.provider == provider,
                HotelProviderCircuit.operation == operation,
            )
        )
        if row is not None:
            return row
        try:
            with db.begin_nested():
                db.add(
                    HotelProviderCircuit(
                        provider=provider,
                        operation=operation,
                        status="closed",
                        failure_threshold=threshold,
                        cooldown_seconds=cooldown,
                        consecutive_failures=0,
                        state_version=0,
                        updated_at=now,
                    )
                )
                db.flush()
        except IntegrityError:
            pass
        row = db.scalar(
            select(HotelProviderCircuit).where(
                HotelProviderCircuit.provider == provider,
                HotelProviderCircuit.operation == operation,
            )
        )
        if row is None:
            raise RuntimeError("hotel_provider_circuit_row_unavailable")
        return row


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default
