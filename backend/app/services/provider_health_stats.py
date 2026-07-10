from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from app.services.quick_search_warning_codes import (
    PROVIDER_INVALID_PRICE_CODES,
    PROVIDER_SCHEMA_CHANGED_CODES,
    PROVIDER_TOTAL_OUTAGE_CODES,
    has_provider_waf_warning,
    normalize_warning_code,
)

PROVIDER_NO_RESULT_CODES = frozenset({"no_results", "no_availability", "provider_empty_result"})


@dataclass(frozen=True, slots=True)
class ProviderHealthSample:
    provider_id: str
    elapsed_ms: int
    flights_count: int
    warning_codes: tuple[str, ...]
    succeeded: bool


@dataclass(frozen=True, slots=True)
class ProviderHealthSnapshot:
    provider_id: str
    calls: int
    successes: int
    timeouts: int
    waf_challenges: int
    invalid_prices: int
    no_results: int
    schema_changes: int
    outages: int
    errors: int
    total_latency_ms: int
    average_latency_ms: float


@dataclass(slots=True)
class _ProviderHealthCounters:
    calls: int = 0
    successes: int = 0
    timeouts: int = 0
    waf_challenges: int = 0
    invalid_prices: int = 0
    no_results: int = 0
    schema_changes: int = 0
    outages: int = 0
    errors: int = 0
    total_latency_ms: int = 0


_provider_health_lock = Lock()
_provider_health_stats: dict[str, _ProviderHealthCounters] = {}


def record_provider_health_sample(sample: ProviderHealthSample) -> None:
    provider_id = sample.provider_id.strip() or "unknown"
    codes = {normalize_warning_code(code) for code in sample.warning_codes}
    elapsed_ms = max(0, sample.elapsed_ms)

    with _provider_health_lock:
        counters = _provider_health_stats.setdefault(provider_id, _ProviderHealthCounters())
        counters.calls += 1
        counters.total_latency_ms += elapsed_ms

        has_timeout = "provider_timeout_partial" in codes
        has_waf = has_provider_waf_warning(codes)
        has_invalid_price = bool(codes & PROVIDER_INVALID_PRICE_CODES)
        has_schema_change = bool(codes & PROVIDER_SCHEMA_CHANGED_CODES)
        has_outage = bool(codes & PROVIDER_TOTAL_OUTAGE_CODES)
        has_no_results = bool(codes & PROVIDER_NO_RESULT_CODES)
        has_dangerous_error = any((has_timeout, has_waf, has_invalid_price, has_schema_change, has_outage))

        if sample.succeeded and sample.flights_count > 0 and not codes:
            counters.successes += 1
        if (sample.succeeded and sample.flights_count == 0 and not has_dangerous_error) or has_no_results:
            counters.no_results += 1
        if has_timeout:
            counters.timeouts += 1
        if has_waf:
            counters.waf_challenges += 1
        if has_invalid_price:
            counters.invalid_prices += 1
        if has_schema_change:
            counters.schema_changes += 1
        if has_outage:
            counters.outages += 1
        if not sample.succeeded and not has_dangerous_error and not has_no_results:
            counters.errors += 1


def snapshot_provider_health() -> list[ProviderHealthSnapshot]:
    with _provider_health_lock:
        snapshots = [
            _snapshot_provider_health(provider_id, counters)
            for provider_id, counters in sorted(_provider_health_stats.items())
        ]
    return snapshots


def reset_provider_health_stats_for_tests() -> None:
    with _provider_health_lock:
        _provider_health_stats.clear()


def _snapshot_provider_health(
    provider_id: str,
    counters: _ProviderHealthCounters,
) -> ProviderHealthSnapshot:
    average_latency_ms = 0.0
    if counters.calls:
        average_latency_ms = round(counters.total_latency_ms / counters.calls, 2)
    return ProviderHealthSnapshot(
        provider_id=provider_id,
        calls=counters.calls,
        successes=counters.successes,
        timeouts=counters.timeouts,
        waf_challenges=counters.waf_challenges,
        invalid_prices=counters.invalid_prices,
        no_results=counters.no_results,
        schema_changes=counters.schema_changes,
        outages=counters.outages,
        errors=counters.errors,
        total_latency_ms=counters.total_latency_ms,
        average_latency_ms=average_latency_ms,
    )
