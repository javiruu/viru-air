from __future__ import annotations

import datetime as dt
import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError, ProviderWarning
from app.services.quick_search_planner import PairPlanItem


# ---------------------------------------------------------------------------
# Shared cache key canonicalization (V2.1)
# ---------------------------------------------------------------------------

CacheUnitKey = tuple[str, str, str, str]
CacheResultCategory = str  # "ready" | "empty" | "degraded"


def build_unit_cache_key(
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
) -> CacheUnitKey:
    """Canonicaliza la clave de unidad exacta cacheable.

    La unidad canonica de reutilizacion es (origin, destination, date, provider).
    Esta clave NO incluye identidad de usuario — la cache es cross-user.
    """
    origin = str(origin_iata).strip().upper()
    destination = str(destination_iata).strip().upper()
    if isinstance(travel_date, dt.date):
        date_str = travel_date.isoformat()
    else:
        date_str = str(travel_date).strip()
    provider_id = str(provider).strip().lower()
    return (origin, destination, date_str, provider_id)


def build_cache_source_hash(
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
) -> str:
    """Hash estable de la fuente de datos para deduplicacion de entradas cacheadas.

    Permite distinguir entradas cacheadas de la misma unidad exacta
    cuando difieren en parametros de consulta internos (e.g. currency).
    """
    payload = {
        "origin": str(origin_iata).strip().upper(),
        "destination": str(destination_iata).strip().upper(),
        "date": str(travel_date).strip() if not isinstance(travel_date, dt.date) else travel_date.isoformat(),
        "provider": str(provider).strip().lower(),
    }
    raw = "|".join(f"{k}={v}" for k, v in sorted(payload.items()))
    return f"qs_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def classify_cache_result(
    *,
    flights: list[ProviderFlight],
    warnings: list[str],
) -> CacheResultCategory:
    """Clasifica un resultado de fetch para determinar TTL de cache.

    - ready: hay vuelos validos
    - empty: sin vuelos (ni siquiera parciales)
    - degraded: resultado parcial, warnings de provider, o errores recuperables
    """
    degradation_codes = {
        "provider_error_partial",
        "provider_timeout_partial",
        "provider_partial_results_served",
        "ryanair_availability_failed_partial",
        "ryanair_fares_failed_partial",
        "ryanair_unavailable_partial",
    }
    has_degradation = any(code in degradation_codes for code in warnings)
    if flights:
        return "degraded" if has_degradation else "ready"
    return "empty"


@dataclass(frozen=True)
class ExecutionUnit:
    origin_iata: str
    destination_iata: str
    travel_date: dt.date
    pair_priority_score: float
    pair_reason: str


@dataclass(frozen=True)
class ExecutionPlan:
    units: list[ExecutionUnit]
    waves: dict[str, int]
    stats: dict[str, int | bool]


_CACHE_LOCK = threading.Lock()
_CACHE: dict[tuple[str, str, str], tuple[float, ProviderFetchResult]] = {}
_CACHE_TTL_SECONDS = 300

# Anti-stampede: per-key locks to prevent duplicate concurrent provider calls
# within a single execute_plan(). Multiple ExecutionUnits may share the same
# (origin, destination, date) tuple; this ensures only one fetches from the
# provider while others wait and reuse the result from L1.
_FETCH_LOCKS: dict[tuple[str, str, str], threading.Lock] = {}
_FETCH_LOCKS_LOCK = threading.Lock()


def _dedupe_warning_codes(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for code in warnings:
        if code in seen:
            continue
        seen.add(code)
        deduped.append(code)
    return deduped


def build_execution_plan(
    planned_pairs: list[PairPlanItem],
    date_candidates: list[dt.date],
    *,
    max_requests: int,
) -> ExecutionPlan:
    # Wave strategy: seed-seed first, then mixed seed/nearby, then nearby-nearby
    wave_order = {"seed-seed": 0, "seed-nearby": 1, "nearby-seed": 1, "nearby-nearby": 2}

    rows: list[tuple[tuple[int, float, str, str, str], ExecutionUnit]] = []
    for pair in planned_pairs:
        for date_value in date_candidates:
            unit = ExecutionUnit(
                origin_iata=pair.origin_iata,
                destination_iata=pair.destination_iata,
                travel_date=date_value,
                pair_priority_score=pair.pair_priority_score,
                pair_reason=pair.pair_reason,
            )
            key = (
                wave_order.get(pair.pair_reason, 9),
                pair.pair_priority_score,
                str(date_value),
                pair.origin_iata,
                pair.destination_iata,
            )
            rows.append((key, unit))

    rows.sort(key=lambda row: row[0])
    requested_units_count = min(len(rows), max(1, max_requests))
    selected = [row[1] for row in rows[:requested_units_count]]

    waves = {"wave_1": 0, "wave_2": 0, "wave_3": 0}
    executed_pair_keys: set[tuple[str, str]] = set()
    for unit in selected:
        if unit.pair_reason == "seed-seed":
            waves["wave_1"] += 1
        elif unit.pair_reason in {"seed-nearby", "nearby-seed"}:
            waves["wave_2"] += 1
        else:
            waves["wave_3"] += 1
        executed_pair_keys.add((unit.origin_iata, unit.destination_iata))

    planned_pair_keys = {(pair.origin_iata, pair.destination_iata) for pair in planned_pairs}
    skipped_pair_keys = planned_pair_keys - executed_pair_keys

    return ExecutionPlan(
        units=selected,
        waves=waves,
        stats={
            "planned_pairs_count": len(planned_pair_keys),
            "executed_pairs_count": len(executed_pair_keys),
            "skipped_pairs_count": len(skipped_pair_keys),
            "requested_units_count": requested_units_count,
            "skipped_units_count": max(0, len(rows) - requested_units_count),
            "truncated_by_max_requests": len(rows) > requested_units_count,
        },
    )


def execute_plan(
    plan: ExecutionPlan,
    *,
    concurrency_limit: int,
    timeout_ms: int,
    fetch_flights: Callable[[str, str, str, int], list[ProviderFlight] | ProviderFetchResult],
    shared_cache_get: Callable[[str, str, dt.date | str, str], ProviderFetchResult | None] | None = None,
    shared_cache_set: Callable[[str, str, dt.date | str, str, ProviderFetchResult], None] | None = None,
) -> tuple[list[tuple[str, str, dt.date, ProviderFlight]], dict[str, Any], list[str]]:
    timeout_ms = max(1000, timeout_ms)
    concurrency = max(1, concurrency_limit)

    combined: list[tuple[str, str, dt.date, ProviderFlight]] = []
    warnings: list[str] = []
    cache_hits = 0
    cache_misses = 0
    l1_cache_hits = 0
    l2_cache_hits = 0
    provider_calls = 0
    timed_out_units_count = 0
    provider_failures = 0
    provider_stats: dict[str, dict[str, Any]] = {}
    structured_warning_events: list[ProviderWarning] = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(
                _fetch_with_cache, unit, timeout_ms, fetch_flights,
                shared_cache_get, shared_cache_set,
            ): unit
            for unit in plan.units
        }
        for future in as_completed(futures):
            unit = futures[future]
            try:
                fetch_result, cache_hit_type = future.result()
                if cache_hit_type == "L1":
                    cache_hits += 1
                    l1_cache_hits += 1
                elif cache_hit_type == "L2":
                    cache_hits += 1
                    l2_cache_hits += 1
                else:
                    provider_calls += 1
                    cache_misses += 1
                warnings.extend(fetch_result.warnings)
                for warning_event in fetch_result.warnings_structured or []:
                    structured_warning_events.append(warning_event)
                    stats = provider_stats.setdefault(
                        warning_event.provider,
                        {"id": warning_event.provider, "errors": 0, "timeouts": 0, "results_count": 0, "status": "ok"},
                    )
                    if warning_event.code == "provider_timeout_partial":
                        stats["timeouts"] += 1
                        stats["status"] = "degraded"
                    if warning_event.severity in {"error", "warning"} and warning_event.code in {
                        "provider_error_partial",
                        "provider_total_outage",
                    }:
                        stats["errors"] += 1
                        stats["status"] = "degraded"
                for flight in fetch_result.flights:
                    combined.append((unit.origin_iata, unit.destination_iata, unit.travel_date, flight))
                    source_provider = (flight.source or "").split("-")[0]
                    if source_provider:
                        stats = provider_stats.setdefault(
                            source_provider,
                            {"id": source_provider, "errors": 0, "timeouts": 0, "results_count": 0, "status": "ok"},
                        )
                        stats["results_count"] += 1
            except ProviderSourceFetchError as exc:
                provider_failures += 1
                warnings.extend(exc.warning_codes)
                provider_key = exc.provider_id or "unknown"
                stats = provider_stats.setdefault(
                    provider_key,
                    {"id": provider_key, "errors": 0, "timeouts": 0, "results_count": 0, "status": "degraded"},
                )
                stats["errors"] += 1
                stats["status"] = "degraded"
            except Exception as exc:
                provider_failures += 1
                if "timeout" in str(exc).lower():
                    timed_out_units_count += 1
                    warnings.append("provider_timeout_parcial")
                else:
                    warnings.append("ryanair_unavailable_parcial")

    meta = {
        **plan.stats,
        "planned_units": len(plan.units),
        "executed_units": len(plan.units),
        "provider_calls": provider_calls,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "l1_cache_hits": l1_cache_hits,
        "l2_cache_hits": l2_cache_hits,
        "timed_out_units_count": timed_out_units_count,
        "provider_failures": provider_failures,
        "concurrency_limit": concurrency,
        "timeout_ms": timeout_ms,
        "waves": plan.waves,
        "provider_statuses": list(provider_stats.values()),
        "warnings_structured_events": [
            {"code": item.code, "provider": item.provider, "severity": item.severity, "meta": item.meta or {}}
            for item in structured_warning_events
        ],
    }
    return combined, meta, _dedupe_warning_codes(warnings)


def _fetch_with_cache(
    unit: ExecutionUnit,
    timeout_ms: int,
    fetch_flights: Callable[[str, str, str, int], list[ProviderFlight] | ProviderFetchResult],
    shared_cache_get: Callable[[str, str, dt.date | str, str], ProviderFetchResult | None] | None = None,
    shared_cache_set: Callable[[str, str, dt.date | str, str, ProviderFetchResult], None] | None = None,
) -> tuple[ProviderFetchResult, str]:
    """Fetch with multi-level cache: L1 (memory) -> L2 (persistent) -> provider.

    Returns (result, cache_hit_type) where cache_hit_type is "L1", "L2", or "MISS".

    Anti-stampede: per-key locks prevent duplicate concurrent provider calls
    for the same (origin, destination, date) within a single execute_plan().
    """
    key = (unit.origin_iata, unit.destination_iata, str(unit.travel_date))
    now = time.time()

    # L1: in-memory hot cache (300s TTL)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] <= _CACHE_TTL_SECONDS:
            return cached[1], "L1"

    # L2: persistent shared cache (cross-user, DB-backed)
    if shared_cache_get is not None:
        l2_result = shared_cache_get(
            unit.origin_iata, unit.destination_iata,
            unit.travel_date, "multi",
        )
        if l2_result is not None:
            # Populate L1 from L2
            with _CACHE_LOCK:
                _CACHE[key] = (now, l2_result)
            return l2_result, "L2"

    # Anti-stampede: acquire per-key lock before hitting provider.
    # If another thread is already fetching this key, wait for it to
    # complete and then check L1 again.
    with _FETCH_LOCKS_LOCK:
        key_lock = _FETCH_LOCKS.get(key)
        if key_lock is None:
            key_lock = threading.Lock()
            _FETCH_LOCKS[key] = key_lock

    with key_lock:
        # Re-check L1 after acquiring lock — the previous holder may have
        # populated the cache.
        with _CACHE_LOCK:
            cached_after_wait = _CACHE.get(key)
            if cached_after_wait and now - cached_after_wait[0] <= _CACHE_TTL_SECONDS:
                return cached_after_wait[1], "L1"

        # MISS: fetch from provider
        raw_result = fetch_flights(unit.origin_iata, unit.destination_iata, str(unit.travel_date), timeout_ms)
        if isinstance(raw_result, ProviderFetchResult):
            fetch_result = raw_result
        else:
            fetch_result = ProviderFetchResult(flights=raw_result, warnings=[])

        # Populate L1
        with _CACHE_LOCK:
            _CACHE[key] = (now, fetch_result)

        # Populate L2
        if shared_cache_set is not None:
            shared_cache_set(
                unit.origin_iata, unit.destination_iata,
                unit.travel_date, "multi", fetch_result,
            )

    # Cleanup: remove the per-key lock to avoid memory leak
    with _FETCH_LOCKS_LOCK:
        if key in _FETCH_LOCKS:
            del _FETCH_LOCKS[key]

    return fetch_result, "MISS"
