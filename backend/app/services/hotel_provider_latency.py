from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import HotelProviderLatencyAggregate


T = TypeVar("T")
Clock = Callable[[], float]
OutcomeClassifier = Callable[[T], tuple[str, str | None]]
ExceptionClassifier = Callable[[Exception], tuple[str, str | None]]
SampleSink = Callable[["ProviderLatencySample"], None]

PROVIDER_OPERATIONS = frozenset({"ingestion", "revalidation", "area_search", "detail", "rates", "search"})
PROVIDER_NAMES = frozenset(
    {"mock", "local_scrape", "makcorps", "osm_overpass", "local", "unknown"}
)
PROVIDER_OUTCOMES = frozenset(
    {
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
    }
)
PRE_IO_SKIP_OUTCOMES = frozenset(
    {"skipped_mapping", "skipped_budget", "skipped_circuit", "skipped_window"}
)
PROVIDER_ERROR_CODES = frozenset(
    {
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
        "schema_drift",
        "rate_without_currency",
        "hotel_ambiguous",
        "partial_batch",
        "unknown",
    }
)
DEFAULT_MAX_DURATION_MS = 60 * 60 * 1000
MAX_ATTEMPT = 100_000
MAX_AGGREGATE_GROUPS = 1_000
MAX_SAMPLES_PER_GROUP = 100_000
MAX_TOTAL_DURATION_MS = DEFAULT_MAX_DURATION_MS * MAX_SAMPLES_PER_GROUP


@dataclass(frozen=True, slots=True)
class ProviderLatencySample:
    """Safe, low-cardinality timing data for one effective provider call."""

    provider: str
    operation: str
    outcome: str
    duration_ms: int
    attempt: int
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderCallMeasurement(Generic[T]):
    """Result of measuring one call without retaining its raw exception."""

    value: T | None
    sample: ProviderLatencySample
    raised: bool


def measure_provider_call(
    call: Callable[[], T],
    *,
    provider: str,
    operation: str,
    attempt: int = 1,
    skip_reason: str | None = None,
    classify_result: OutcomeClassifier[T] | None = None,
    classify_exception: ExceptionClassifier | None = None,
    on_sample: SampleSink | None = None,
    propagate_exception: bool = False,
    clock: Clock = time.monotonic,
    max_duration_ms: int = DEFAULT_MAX_DURATION_MS,
) -> ProviderCallMeasurement[T] | None:
    """Measure only an effective provider call with a monotonic clock.

    The callback is never invoked when ``skip_reason`` is a recognized pre-I/O
    skip. In that case this returns ``None`` so callers cannot accidentally
    persist a zero-latency provider sample for budget, mapping, circuit or
    window denials.

    Exceptions are converted to a terminal, allowlisted outcome and error code;
    their text is intentionally not retained. The helper has no DB, logging,
    network or provider side effects.
    """
    if max_duration_ms < 1:
        raise ValueError("hotel_provider_latency_max_duration_out_of_bounds")
    if attempt < 1 or attempt > MAX_ATTEMPT:
        raise ValueError("hotel_provider_latency_attempt_out_of_bounds")
    if skip_reason is not None:
        if skip_reason not in PRE_IO_SKIP_OUTCOMES:
            raise ValueError("hotel_provider_latency_skip_outcome_not_allowed")
        return None

    started = clock()
    try:
        value = call()
        finished = clock()
    except Exception as exc:
        finished = clock()
        try:
            outcome, error_code = (
                classify_exception(exc)
                if classify_exception is not None
                else _classify_exception(exc)
            )
        except Exception:
            # A classifier is local instrumentation code; never let it expose
            # raw exception data or hide the terminal provider failure.
            outcome, error_code = "failed", "provider_error"
        measurement = ProviderCallMeasurement(
            value=None,
            sample=ProviderLatencySample(
                provider=_normalize_dimension(provider, PROVIDER_NAMES),
                operation=_normalize_dimension(operation, PROVIDER_OPERATIONS),
                outcome=_normalize_outcome(outcome),
                duration_ms=_duration_ms(started, finished, max_duration_ms),
                attempt=attempt,
                error_code=_normalize_error_code(error_code),
            ),
            raised=True,
        )
        _emit_sample(on_sample, measurement.sample)
        if propagate_exception:
            raise
        return measurement

    outcome = "success"
    error_code: str | None = None
    if classify_result is not None:
        try:
            outcome, error_code = classify_result(value)
        except Exception:
            # A classifier is local instrumentation code; never let a bad
            # classifier expose raw data or hide the completed provider call.
            outcome, error_code = "failed", "provider_error"

    measurement = ProviderCallMeasurement(
        value=value,
        sample=ProviderLatencySample(
            provider=_normalize_dimension(provider, PROVIDER_NAMES),
            operation=_normalize_dimension(operation, PROVIDER_OPERATIONS),
            outcome=_normalize_outcome(outcome),
            duration_ms=_duration_ms(started, finished, max_duration_ms),
            attempt=attempt,
            error_code=_normalize_error_code(error_code),
        ),
        raised=False,
    )
    _emit_sample(on_sample, measurement.sample)
    return measurement


@dataclass(frozen=True, slots=True)
class ProviderLatencyAggregateKey:
    provider: str
    operation: str
    outcome: str
    error_code: str


@dataclass(frozen=True, slots=True)
class ProviderLatencyAggregateValue:
    provider: str
    operation: str
    outcome: str
    error_code: str
    sample_count: int
    total_duration_ms: int
    min_duration_ms: int
    max_duration_ms: int


class HotelProviderLatencyAccumulator:
    """Bounded in-memory reducer for one persisted provider run."""

    def __init__(self) -> None:
        self._groups: dict[ProviderLatencyAggregateKey, list[int]] = {}

    def add(self, sample: ProviderLatencySample) -> None:
        if sample.provider not in PROVIDER_NAMES:
            raise ValueError("hotel_provider_latency_provider_not_allowed")
        if sample.operation not in PROVIDER_OPERATIONS:
            raise ValueError("hotel_provider_latency_operation_not_allowed")
        if sample.outcome not in PROVIDER_OUTCOMES:
            raise ValueError("hotel_provider_latency_outcome_not_allowed")
        if sample.error_code is not None and sample.error_code not in PROVIDER_ERROR_CODES:
            raise ValueError("hotel_provider_latency_error_code_not_allowed")
        key = ProviderLatencyAggregateKey(
            provider=sample.provider,
            operation=sample.operation,
            outcome=sample.outcome,
            error_code=sample.error_code or "none",
        )
        duration = sample.duration_ms
        if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0 or duration > DEFAULT_MAX_DURATION_MS:
            raise ValueError("hotel_provider_latency_duration_out_of_bounds")
        group = self._groups.get(key)
        if group is None:
            if len(self._groups) >= MAX_AGGREGATE_GROUPS:
                raise ValueError("hotel_provider_latency_group_limit_exceeded")
            group = [0, 0, duration, duration]
            self._groups[key] = group
        if group[0] >= MAX_SAMPLES_PER_GROUP or group[1] + duration > MAX_TOTAL_DURATION_MS:
            raise ValueError("hotel_provider_latency_aggregate_limit_exceeded")
        group[0] += 1
        group[1] += duration
        group[2] = min(group[2], duration)
        group[3] = max(group[3], duration)

    def snapshot(self) -> list[ProviderLatencyAggregateValue]:
        return [
            ProviderLatencyAggregateValue(
                provider=key.provider,
                operation=key.operation,
                outcome=key.outcome,
                error_code=key.error_code,
                sample_count=values[0],
                total_duration_ms=values[1],
                min_duration_ms=values[2],
                max_duration_ms=values[3],
            )
            for key, values in sorted(
                self._groups.items(),
                key=lambda item: (item[0].provider, item[0].operation, item[0].outcome, item[0].error_code),
            )
        ]


def compose_provider_latency_sinks(*sinks: SampleSink | None) -> SampleSink | None:
    """Fan out samples without allowing one optional sink to block another."""
    active = tuple(sink for sink in sinks if sink is not None)
    if not active:
        return None

    def _fanout(sample: ProviderLatencySample) -> None:
        for sink in active:
            try:
                sink(sample)
            except Exception:
                continue

    return _fanout


def persist_hotel_provider_latency_aggregates(
    db: Session,
    *,
    provider_run_id: str,
    accumulator: HotelProviderLatencyAccumulator,
) -> int:
    """Upsert one row per aggregate group without committing the caller transaction."""
    if not provider_run_id:
        raise ValueError("hotel_provider_latency_run_id_required")
    aggregates = accumulator.snapshot()
    if not aggregates:
        return 0
    dialect_name = db.get_bind().dialect.name
    for aggregate in aggregates:
        values = {
            "provider_run_id": provider_run_id,
            "provider": aggregate.provider,
            "operation": aggregate.operation,
            "outcome": aggregate.outcome,
            "error_code": aggregate.error_code,
            "sample_count": aggregate.sample_count,
            "total_duration_ms": aggregate.total_duration_ms,
            "min_duration_ms": aggregate.min_duration_ms,
            "max_duration_ms": aggregate.max_duration_ms,
            "created_at": utc_now_naive(),
            "updated_at": utc_now_naive(),
        }
        if dialect_name == "postgresql":
            stmt = postgresql_insert(HotelProviderLatencyAggregate).values(**values)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                constraint="uq_hotel_provider_latency_aggregate_key",
                set_={
                    "sample_count": excluded.sample_count,
                    "total_duration_ms": excluded.total_duration_ms,
                    "min_duration_ms": excluded.min_duration_ms,
                    "max_duration_ms": excluded.max_duration_ms,
                    "updated_at": utc_now_naive(),
                },
            )
        elif dialect_name == "sqlite":
            stmt = sqlite_insert(HotelProviderLatencyAggregate).values(**values)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=["provider_run_id", "provider", "operation", "outcome", "error_code"],
                set_={
                    "sample_count": excluded.sample_count,
                    "total_duration_ms": excluded.total_duration_ms,
                    "min_duration_ms": excluded.min_duration_ms,
                    "max_duration_ms": excluded.max_duration_ms,
                    "updated_at": utc_now_naive(),
                },
            )
        else:
            raise RuntimeError("hotel_provider_latency_aggregate_unsupported_dialect")
        db.execute(stmt)
    return len(aggregates)


def _emit_sample(on_sample: SampleSink | None, sample: ProviderLatencySample) -> None:
    if on_sample is None:
        return
    try:
        on_sample(sample)
    except Exception:
        # Instrumentation must never change provider behavior.
        return


def _normalize_dimension(value: str, allowed: frozenset[str]) -> str:
    normalized = value.strip().lower() if isinstance(value, str) else ""
    return normalized if normalized in allowed else "unknown"


def _normalize_outcome(value: str) -> str:
    normalized = value.strip().lower() if isinstance(value, str) else ""
    return normalized if normalized in PROVIDER_OUTCOMES else "unknown"


def _normalize_error_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower() if isinstance(value, str) else ""
    return normalized if normalized in PROVIDER_ERROR_CODES else "unknown"


def _duration_ms(started: float, finished: float, maximum: int) -> int:
    elapsed_ms = (finished - started) * 1000
    if math.isnan(elapsed_ms) or elapsed_ms <= 0:
        return 0
    if math.isinf(elapsed_ms):
        return maximum
    return min(maximum, int(elapsed_ms))


def _classify_exception(exc: Exception) -> tuple[str, str]:
    """Classify by exception type only; never inspect exception text."""
    name = type(exc).__name__.lower()
    if isinstance(exc, TimeoutError) or "timeout" in name:
        return "timeout", "timeout"
    if "ratelimit" in name or "toomanyrequests" in name:
        return "rate_limited", "rate_limited"
    if "jsondecode" in name or "invalidresponse" in name:
        return "invalid_response", "invalid_response"
    if "connection" in name or "network" in name:
        return "unavailable", "network_error"
    return "failed", "provider_error"
