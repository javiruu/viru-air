from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import asc, desc, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import (
    HotelDailyMetric,
    HotelProviderBudget,
    HotelProviderCircuit,
    HotelProviderLatencyAggregate,
    HotelProviderRun,
    HotelSweepLease,
)


METRIC_SWEEP_RUN = "sweep_run"
METRIC_ALERT_EVENT = "alert_event"
METRIC_HOTEL_DELIVERY = "hotel_delivery"

ALLOWED_METRICS = frozenset({METRIC_SWEEP_RUN, METRIC_ALERT_EVENT, METRIC_HOTEL_DELIVERY})
ALLOWED_PROVIDERS = frozenset(
    {"mock", "local_scrape", "makcorps", "osm_overpass", "local", "unknown"}
)

ALLOWED_OUTCOMES = {
    METRIC_SWEEP_RUN: frozenset({"completed", "partial", "failed", "skipped"}),
    METRIC_ALERT_EVENT: frozenset({"created"}),
    METRIC_HOTEL_DELIVERY: frozenset({"delivered", "retried", "failed"}),
}
MAX_QUERY_DAYS = 31
DEFAULT_HEALTH_WINDOW_HOURS = 24
MAX_HEALTH_WINDOW_HOURS = 168
HEALTH_STATUSES = frozenset({"unknown", "not_configured", "ok", "degraded", "critical"})
RUN_STATUSES = frozenset({"running", "completed", "partial", "failed", "skipped"})
HEALTH_RUN_STATUSES = frozenset({"running", "completed", "partial", "failed", "skipped", "unknown"})
RUN_DIAGNOSTIC_PROVIDERS = frozenset(
    {"mock", "local_scrape", "makcorps", "osm_overpass", "local", "unknown"}
)
RUN_DIAGNOSTIC_OUTCOMES = frozenset({
    "offers_scanned",
    "snapshots_created",
    "provider_fetch_attempted",
    "provider_fetch_completed",
    "provider_fetch_empty",
    "provider_fetch_failed",
    "provider_fetch_skipped",
    "provider_fetch_budget_denied",
})
MAX_RUN_DIAGNOSTIC_LIMIT = 50
CONTROL_OPERATIONS = frozenset({"ingestion", "revalidation", "area_search"})
CONTROL_CIRCUIT_STATUSES = frozenset({"closed", "open", "half_open", "unknown"})
CONTROL_BUDGET_SOURCES = frozenset({"local_config", "unknown"})
CONTROL_ERROR_CODES = frozenset({
    "timeout",
    "rate_limited",
    "network_error",
    "provider_5xx",
    "unavailable",
    "failed",
    "provider_error",
    "provider_unavailable",
    "provider_fetch_failed",
    "provider_timeout",
    "unknown",
})
MAX_PROVIDER_CONTROL_ROWS = 50
MAX_SWEEP_LEASE_DIAGNOSTIC_LIMIT = 50
MAX_OUTCOME_DIAGNOSTIC_LIMIT = 50
MAX_LATENCY_DIAGNOSTIC_LIMIT = 50
LATENCY_PROVIDERS = frozenset(
    {"mock", "local_scrape", "makcorps", "osm_overpass", "local", "unknown"}
)
LATENCY_OPERATIONS = frozenset({"ingestion", "revalidation", "area_search", "detail", "rates", "search"})
LATENCY_OUTCOMES = frozenset({
    "success",
    "empty",
    "partial",
    "rate_limited",
    "timeout",
    "unavailable",
    "unsupported",
    "invalid_response",
    "failed",
    "unknown",
})
LATENCY_ERROR_CODES = frozenset({
    "none",
    "timeout",
    "rate_limited",
    "network_error",
    "provider_5xx",
    "unavailable",
    "failed",
    "provider_error",
    "provider_unavailable",
    "provider_fetch_failed",
    "provider_timeout",
    "invalid_response",
    "unknown",
})
LEASE_STATES = frozenset({"queued", "running", "expired", "done", "partial", "skipped", "failed", "unknown"})
LEASE_ERROR_CODES = frozenset({
    "budget_consume_failed",
    "provider_fetch_failed",
    "provider_fetch_skipped",
    "provider_budget_denied",
    "timeout",
    "unknown",
})


@dataclass(frozen=True, slots=True)
class HotelMetricKey:
    metric_date: date
    metric_name: str
    provider: str
    outcome: str


def record_hotel_daily_metric(
    db: Session,
    *,
    metric_name: str,
    provider: str,
    outcome: str,
    increment: int = 1,
    metric_date: date | None = None,
) -> None:
    """Increment one allowlisted aggregate without committing the caller's transaction."""
    if metric_name not in ALLOWED_METRICS:
        raise ValueError("hotel_metric_name_not_allowed")
    if outcome not in ALLOWED_OUTCOMES[metric_name]:
        raise ValueError("hotel_metric_outcome_not_allowed")
    if increment < 1 or increment > 100_000:
        raise ValueError("hotel_metric_increment_out_of_bounds")

    normalized_provider = provider.strip().lower() or "unknown"
    if normalized_provider not in ALLOWED_PROVIDERS:
        raise ValueError("hotel_metric_provider_not_allowed")
    key = HotelMetricKey(
        metric_date=metric_date or utc_now_naive().date(),
        metric_name=metric_name,
        provider=normalized_provider,
        outcome=outcome,
    )
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "postgresql":
        db.execute(_postgresql_upsert(key, increment))
    elif dialect_name == "sqlite":
        db.execute(_sqlite_upsert(key, increment))
    else:
        raise RuntimeError("hotel_metric_atomic_upsert_unsupported_dialect")


def list_hotel_daily_metrics(
    db: Session,
    *,
    days: int = 7,
    provider: str | None = None,
    metric_name: str | None = None,
    outcome: str | None = None,
) -> list[HotelDailyMetric]:
    """Return only bounded, low-cardinality aggregate rows for admin use."""
    if days < 1 or days > MAX_QUERY_DAYS:
        raise ValueError("hotel_metric_days_out_of_bounds")
    if metric_name is not None and metric_name not in ALLOWED_METRICS:
        raise ValueError("hotel_metric_name_not_allowed")
    if outcome is not None and metric_name is not None and outcome not in ALLOWED_OUTCOMES[metric_name]:
        raise ValueError("hotel_metric_outcome_not_allowed")

    since = utc_now_naive().date() - timedelta(days=days - 1)
    stmt = select(HotelDailyMetric).where(HotelDailyMetric.metric_date >= since)
    if provider:
        normalized_provider = provider.strip().lower()
        if normalized_provider not in ALLOWED_PROVIDERS:
            raise ValueError("hotel_metric_provider_not_allowed")
        stmt = stmt.where(HotelDailyMetric.provider == normalized_provider)
    if metric_name:
        stmt = stmt.where(HotelDailyMetric.metric_name == metric_name)
    if outcome:
        stmt = stmt.where(HotelDailyMetric.outcome == outcome)
    stmt = stmt.order_by(
        asc(HotelDailyMetric.metric_date),
        asc(HotelDailyMetric.metric_name),
        asc(HotelDailyMetric.provider),
        asc(HotelDailyMetric.outcome),
    )
    return list(db.scalars(stmt))


def build_hotel_health_snapshot(
    db: Session,
    *,
    window_hours: int = DEFAULT_HEALTH_WINDOW_HOURS,
) -> dict[str, object]:
    """Build an admin-only health view from persisted runs and low-cardinality metrics.

    This intentionally performs no provider calls and does not mutate the session. A
    missing run is ``unknown`` rather than healthy; ``skipped`` is the explicit
    ``not_configured`` state emitted by the sweep lifecycle.
    """
    if window_hours < 1 or window_hours > MAX_HEALTH_WINDOW_HOURS:
        raise ValueError("hotel_health_window_hours_out_of_bounds")

    now = utc_now_naive()
    since = now - timedelta(hours=window_hours)
    run_statuses = tuple(sorted(RUN_STATUSES))
    provider_names = tuple(sorted(ALLOWED_PROVIDERS))
    latest_runs: dict[str, HotelProviderRun | None] = {}
    for provider in provider_names:
        latest_runs[provider] = db.scalar(
            select(HotelProviderRun)
            .where(HotelProviderRun.provider == provider)
            .order_by(desc(HotelProviderRun.started_at))
            .limit(1)
        )

    run_counts = {
        provider: {status: 0 for status in run_statuses}
        for provider in provider_names
    }
    run_rows = db.execute(
        select(
            HotelProviderRun.provider,
            HotelProviderRun.status,
            func.count(HotelProviderRun.id),
        )
        .where(
            HotelProviderRun.provider.in_(provider_names),
            HotelProviderRun.started_at >= since,
        )
        .group_by(HotelProviderRun.provider, HotelProviderRun.status)
    ).all()
    for provider, status, count in run_rows:
        if provider in run_counts and status in run_counts[provider]:
            run_counts[provider][status] = int(count)

    metric_rows = list(
        db.execute(
            select(
                HotelDailyMetric.provider,
                HotelDailyMetric.metric_name,
                HotelDailyMetric.outcome,
                func.sum(HotelDailyMetric.count),
            )
            .where(
                HotelDailyMetric.metric_date >= since.date(),
                HotelDailyMetric.provider.in_(provider_names),
            )
            .group_by(
                HotelDailyMetric.provider,
                HotelDailyMetric.metric_name,
                HotelDailyMetric.outcome,
            )
        ).all()
    )
    metric_counts = {
        provider: {"failed": 0, "partial": 0, "retried": 0}
        for provider in provider_names
    }
    for provider, metric_name, outcome, count in metric_rows:
        if provider not in metric_counts:
            continue
        if metric_name == METRIC_HOTEL_DELIVERY and outcome == "failed":
            metric_counts[provider]["failed"] += int(count or 0)
        elif metric_name == METRIC_HOTEL_DELIVERY and outcome == "retried":
            metric_counts[provider]["retried"] += int(count or 0)
        elif metric_name == METRIC_SWEEP_RUN and outcome in {"failed", "partial"}:
            metric_counts[provider][outcome] += int(count or 0)

    def _age_seconds(run: HotelProviderRun | None) -> int | None:
        if run is None:
            return None
        reference = run.finished_at or run.started_at
        return max(0, int((now - reference).total_seconds()))

    def _status(provider: str, run: HotelProviderRun | None) -> str:
        counts = run_counts[provider]
        metric = metric_counts[provider]
        if run is None:
            if metric["failed"] > 0:
                return "critical"
            return "unknown"
        if run.status == "skipped":
            return "not_configured"
        if run.status == "failed" or metric["failed"] > 0:
            return "critical"
        age_seconds = _age_seconds(run)
        if (
            run.status == "partial"
            or run.status == "running"
            or metric["partial"] > 0
            or metric["retried"] > 0
            or (age_seconds is not None and age_seconds > window_hours * 3600)
        ):
            return "degraded"
        if counts["completed"] > 0 and run.status == "completed":
            return "ok"
        return "unknown"

    def _safe_run_status(run: HotelProviderRun) -> str:
        return run.status if run.status in HEALTH_RUN_STATUSES else "unknown"

    def _run_payload(run: HotelProviderRun | None) -> dict[str, object] | None:
        if run is None:
            return None
        return {
            "provider": run.provider,
            "status": _safe_run_status(run),
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "age_seconds": _age_seconds(run),
        }

    providers: list[dict[str, object]] = []
    for provider in provider_names:
        run = latest_runs[provider]
        counts = run_counts[provider]
        providers.append(
            {
                "provider": provider,
                "status": _status(provider, run),
                "runs": sum(counts.values()),
                "running": counts["running"],
                "completed": counts["completed"],
                "partial": counts["partial"],
                "failed": counts["failed"],
                "skipped": counts["skipped"],
                "deliveries_failed": metric_counts[provider]["failed"],
                "last_run_at": run.started_at.isoformat() if run else None,
                "last_run_status": _safe_run_status(run) if run else None,
                "last_finished_at": run.finished_at.isoformat() if run and run.finished_at else None,
                "age_seconds": _age_seconds(run),
            }
        )

    observed = [item for item in providers if item["runs"] or item["last_run_at"]]
    statuses = [str(item["status"]) for item in observed]
    if not observed:
        overall_status = "unknown"
    elif any(status == "critical" for status in statuses):
        overall_status = "critical"
    elif any(status == "degraded" for status in statuses):
        overall_status = "degraded"
    elif all(status == "not_configured" for status in statuses):
        overall_status = "not_configured"
    elif any(status == "ok" for status in statuses):
        overall_status = "ok"
    else:
        overall_status = "unknown"

    latest_run = max(
        (run for run in latest_runs.values() if run is not None),
        key=lambda run: run.started_at,
        default=None,
    )
    return {
        "status": overall_status,
        "generated_at": now.isoformat(),
        "window_hours": window_hours,
        "latest_run": _run_payload(latest_run),
        "providers": providers,
    }


def list_hotel_provider_run_diagnostics(
    db: Session,
    *,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return bounded, privacy-safe summaries of recent persisted provider runs."""
    if limit < 1 or limit > MAX_RUN_DIAGNOSTIC_LIMIT:
        raise ValueError("hotel_run_diagnostic_limit_out_of_bounds")

    rows = list(
        db.scalars(
            select(HotelProviderRun)
            .where(HotelProviderRun.provider.in_(RUN_DIAGNOSTIC_PROVIDERS))
            .order_by(desc(HotelProviderRun.started_at), desc(HotelProviderRun.id))
            .limit(limit)
        )
    )

    def _safe_status(status: str) -> str:
        return status if status in HEALTH_RUN_STATUSES else "unknown"

    diagnostics: list[dict[str, object]] = []
    for row in rows:
        duration_seconds = None
        if row.finished_at is not None:
            duration_seconds = max(0, int((row.finished_at - row.started_at).total_seconds()))
        raw_outcomes = row.tracked_outcomes if isinstance(row.tracked_outcomes, dict) else {}
        outcomes = {
            key: int(value)
            for key, value in raw_outcomes.items()
            if key in RUN_DIAGNOSTIC_OUTCOMES and isinstance(value, int) and not isinstance(value, bool) and value >= 0
        }
        diagnostics.append(
            {
                "provider": row.provider,
                "status": _safe_status(row.status),
                "started_at": row.started_at.isoformat(),
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                "duration_seconds": duration_seconds,
                "items_processed": max(0, int(row.items_processed or 0)),
                "has_error": bool(row.error_message),
                "outcomes": outcomes,
            }
        )
    return diagnostics


def list_hotel_provider_controls(
    db: Session,
    *,
    limit: int = 50,
) -> dict[str, list[dict[str, object]]]:
    """Return bounded, read-only budget/circuit state for admin diagnosis.

    This intentionally exposes no primary keys, probe tokens, raw error text or
    mutable control action. Unknown legacy dimensions are normalized instead of
    being emitted as arbitrary labels.
    """
    if limit < 1 or limit > MAX_PROVIDER_CONTROL_ROWS:
        raise ValueError("hotel_provider_control_limit_out_of_bounds")

    now = utc_now_naive()
    budgets: list[HotelProviderBudget] = list(
        db.scalars(
            select(HotelProviderBudget)
            .where(
                HotelProviderBudget.provider.in_(ALLOWED_PROVIDERS),
                HotelProviderBudget.operation.in_(CONTROL_OPERATIONS),
                HotelProviderBudget.window_expires_at >= now,
            )
            .order_by(asc(HotelProviderBudget.window_expires_at), asc(HotelProviderBudget.provider), asc(HotelProviderBudget.operation))
            .limit(limit)
        )
    )
    circuits: list[HotelProviderCircuit] = list(
        db.scalars(
            select(HotelProviderCircuit)
            .where(
                HotelProviderCircuit.provider.in_(ALLOWED_PROVIDERS),
                HotelProviderCircuit.operation.in_(CONTROL_OPERATIONS),
            )
            .order_by(asc(HotelProviderCircuit.provider), asc(HotelProviderCircuit.operation))
            .limit(limit)
        )
    )

    def _provider(value: str) -> str:
        return value if value in ALLOWED_PROVIDERS else "unknown"

    def _operation(value: str) -> str:
        return value if value in CONTROL_OPERATIONS else "unknown"

    def _status(value: str) -> str:
        return value if value in CONTROL_CIRCUIT_STATUSES else "unknown"

    def _source(value: str) -> str:
        return value if value in CONTROL_BUDGET_SOURCES else "unknown"

    def _error_code(value: str | None) -> str | None:
        if value is None:
            return None
        return value if value in CONTROL_ERROR_CODES else "unknown"

    def _window_key(value: str) -> str:
        if re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", value):
            try:
                date.fromisoformat(value)
            except ValueError:
                return "unknown"
            return value
        if re.fullmatch(r"\\d{4}-\\d{2}", value):
            try:
                date.fromisoformat(f"{value}-01")
            except ValueError:
                return "unknown"
            return value
        return "unknown"

    budget_payload = []
    for budget in budgets:
        remaining = max(0, int(budget.hard_limit or 0) - int(budget.units_used or 0) - int(budget.units_reserved or 0))
        budget_payload.append(
            {
                "provider": _provider(budget.provider),
                "operation": _operation(budget.operation),
                "window_key": _window_key(budget.window_key),
                "hard_limit": max(0, int(budget.hard_limit or 0)),
                "units_reserved": max(0, int(budget.units_reserved or 0)),
                "units_used": max(0, int(budget.units_used or 0)),
                "units_released": max(0, int(budget.units_released or 0)),
                "units_remaining": remaining,
                "window_expires_at": budget.window_expires_at.isoformat(),
                "source": _source(budget.source),
            }
        )

    circuit_payload = []
    for circuit in circuits:
        circuit_payload.append(
            {
                "provider": _provider(circuit.provider),
                "operation": _operation(circuit.operation),
                "status": _status(circuit.status),
                "consecutive_failures": max(0, int(circuit.consecutive_failures or 0)),
                "failure_threshold": max(1, int(circuit.failure_threshold or 1)),
                "opened_at": circuit.opened_at.isoformat() if circuit.opened_at else None,
                "next_probe_at": circuit.next_probe_at.isoformat() if circuit.next_probe_at else None,
                "last_error_code": _error_code(circuit.last_error_code),
                "updated_at": circuit.updated_at.isoformat(),
            }
        )
    return {"budgets": budget_payload, "circuits": circuit_payload}


def list_hotel_provider_latency_diagnostics(
    db: Session,
    *,
    limit: int = 20,
    provider: str | None = None,
    operation: str | None = None,
) -> dict[str, object]:
    """Return bounded latency aggregates without exposing internal run IDs."""
    if limit < 1 or limit > MAX_LATENCY_DIAGNOSTIC_LIMIT:
        raise ValueError("hotel_latency_diagnostic_limit_out_of_bounds")
    if provider is not None and provider not in LATENCY_PROVIDERS:
        raise ValueError("hotel_latency_provider_not_allowed")
    if operation is not None and operation not in LATENCY_OPERATIONS:
        raise ValueError("hotel_latency_operation_not_allowed")

    stmt = (
        select(HotelProviderLatencyAggregate)
        .join(HotelProviderRun, HotelProviderRun.id == HotelProviderLatencyAggregate.provider_run_id)
        .where(HotelProviderRun.provider.in_(LATENCY_PROVIDERS))
        .order_by(
            desc(HotelProviderLatencyAggregate.created_at),
            asc(HotelProviderLatencyAggregate.provider),
            asc(HotelProviderLatencyAggregate.operation),
            asc(HotelProviderLatencyAggregate.outcome),
        )
        .limit(limit)
    )
    if provider is not None:
        stmt = stmt.where(HotelProviderLatencyAggregate.provider == provider)
    if operation is not None:
        stmt = stmt.where(HotelProviderLatencyAggregate.operation == operation)

    rows = list(db.scalars(stmt))
    aggregates: list[dict[str, object]] = []
    for row in rows:
        safe_provider = row.provider if row.provider in LATENCY_PROVIDERS else "unknown"
        safe_operation = row.operation if row.operation in LATENCY_OPERATIONS else "unknown"
        safe_outcome = row.outcome if row.outcome in LATENCY_OUTCOMES else "unknown"
        safe_error = row.error_code if row.error_code in LATENCY_ERROR_CODES else "unknown"
        count = max(0, int(row.sample_count or 0))
        total = max(0, int(row.total_duration_ms or 0))
        minimum = max(0, int(row.min_duration_ms or 0))
        maximum = max(0, int(row.max_duration_ms or 0))
        aggregates.append(
            {
                "provider": safe_provider,
                "operation": safe_operation,
                "outcome": safe_outcome,
                "error_code": None if safe_error == "none" else safe_error,
                "sample_count": count,
                "total_duration_ms": total,
                "min_duration_ms": minimum,
                "max_duration_ms": maximum,
                "average_duration_ms": round(total / count, 2) if count else None,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            }
        )
    return {
        "limit": limit,
        "sample_size": len(aggregates),
        "aggregates": aggregates,
    }


def list_hotel_provider_outcome_diagnostics(
    db: Session,
    *,
    limit: int = 20,
) -> dict[str, object]:
    """Aggregate persisted run outcomes without exposing run/entity identifiers.

    ``tracked_outcomes`` is a run-level counter map, not a per-hotel event log;
    the response preserves that distinction through ``sample_size`` and
    ``runs``. It never contacts a provider or mutates the session.
    """
    if limit < 1 or limit > MAX_OUTCOME_DIAGNOSTIC_LIMIT:
        raise ValueError("hotel_outcome_diagnostic_limit_out_of_bounds")

    rows = list(
        db.scalars(
            select(HotelProviderRun)
            .where(HotelProviderRun.provider.in_(RUN_DIAGNOSTIC_PROVIDERS))
            .order_by(desc(HotelProviderRun.started_at), desc(HotelProviderRun.id))
            .limit(limit)
        )
    )
    statuses = tuple(sorted(HEALTH_RUN_STATUSES))
    providers: dict[str, dict[str, object]] = {}
    totals: dict[str, int] = {}
    for row in rows:
        provider = row.provider if row.provider in RUN_DIAGNOSTIC_PROVIDERS else "unknown"
        item = providers.setdefault(
            provider,
            {
                "provider": provider,
                "runs": 0,
                "statuses": {status: 0 for status in statuses},
                "outcomes": {},
            },
        )
        runs = item["runs"]
        assert isinstance(runs, int)
        item["runs"] = runs + 1
        safe_status = row.status if row.status in HEALTH_RUN_STATUSES else "unknown"
        status_counts = item["statuses"]
        assert isinstance(status_counts, dict)
        status_counts[safe_status] = int(status_counts.get(safe_status, 0)) + 1
        raw_outcomes = row.tracked_outcomes if isinstance(row.tracked_outcomes, dict) else {}
        provider_outcomes = item["outcomes"]
        assert isinstance(provider_outcomes, dict)
        for key, value in raw_outcomes.items():
            if (
                key not in RUN_DIAGNOSTIC_OUTCOMES
                or not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                continue
            provider_outcomes[key] = int(provider_outcomes.get(key, 0)) + value
            totals[key] = totals.get(key, 0) + value

    return {
        "limit": limit,
        "generated_at": utc_now_naive().isoformat(),
        "sample_size": len(rows),
        "providers": [providers[key] for key in sorted(providers)],
        "totals": totals,
    }


def list_hotel_sweep_lease_diagnostics(
    db: Session,
    *,
    limit: int = 20,
) -> dict[str, object]:
    """Return a bounded, privacy-safe view of persisted sweep leases.

    A lease is called ``expired`` only when its persisted state is ``running``
    and its TTL has elapsed. This is an operational signal, not proof that a
    scheduler window was missed because the model has no scheduled-window field.
    """
    if limit < 1 or limit > MAX_SWEEP_LEASE_DIAGNOSTIC_LIMIT:
        raise ValueError("hotel_sweep_lease_diagnostic_limit_out_of_bounds")

    now = utc_now_naive()
    rows = list(
        db.scalars(
            select(HotelSweepLease)
            .order_by(desc(HotelSweepLease.updated_at), desc(HotelSweepLease.fingerprint))
            .limit(limit)
        )
    )

    def _state(row: HotelSweepLease) -> str:
        if row.status == "running" and row.lease_expires_at is not None and row.lease_expires_at <= now:
            return "expired"
        return row.status if row.status in LEASE_STATES else "unknown"

    def _error_code(value: str | None) -> str | None:
        if value is None:
            return None
        return value if value in LEASE_ERROR_CODES else "unknown"

    leases: list[dict[str, object]] = []
    counts = {state: 0 for state in LEASE_STATES}
    attention_count = 0
    for row in rows:
        state = _state(row)
        counts[state] += 1
        attention = state in {"expired", "partial", "failed"}
        if attention:
            attention_count += 1
        leases.append(
            {
                "state": state,
                "attempt_count": max(0, int(row.attempt_count or 0)),
                "lease_expires_at": row.lease_expires_at.isoformat() if row.lease_expires_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                "last_error_code": _error_code(row.last_error_code),
                "has_provider_run": bool(row.last_provider_run_id),
                "attention": attention,
                "updated_at": row.updated_at.isoformat(),
            }
        )

    return {
        "limit": limit,
        "generated_at": now.isoformat(),
        "sample_size": len(leases),
        "attention_count": attention_count,
        "counts": {state: counts[state] for state in sorted(counts)},
        "leases": leases,
    }


def _postgresql_upsert(key: HotelMetricKey, increment: int):
    stmt = postgresql_insert(HotelDailyMetric).values(
        metric_date=key.metric_date,
        metric_name=key.metric_name,
        provider=key.provider,
        outcome=key.outcome,
        count=increment,
        updated_at=utc_now_naive(),
    )
    return stmt.on_conflict_do_update(
        constraint="uq_hotel_daily_metric_key",
        set_={
            "count": HotelDailyMetric.count + increment,
            "updated_at": utc_now_naive(),
        },
    )


def _sqlite_upsert(key: HotelMetricKey, increment: int):
    stmt = sqlite_insert(HotelDailyMetric).values(
        metric_date=key.metric_date,
        metric_name=key.metric_name,
        provider=key.provider,
        outcome=key.outcome,
        count=increment,
        updated_at=utc_now_naive(),
    )
    return stmt.on_conflict_do_update(
        index_elements=["metric_date", "metric_name", "provider", "outcome"],
        set_={
            "count": HotelDailyMetric.count + increment,
            "updated_at": utc_now_naive(),
        },
    )
