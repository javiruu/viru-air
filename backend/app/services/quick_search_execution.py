from __future__ import annotations

import datetime as dt
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from app.domain.entities import ProviderFlight
from app.services.quick_search_planner import PairPlanItem


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


_CACHE_LOCK = threading.Lock()
_CACHE: dict[tuple[str, str, str], tuple[float, list[ProviderFlight]]] = {}
_CACHE_TTL_SECONDS = 300


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
    selected = [row[1] for row in rows[: max(1, max_requests)]]

    waves = {"wave_1": 0, "wave_2": 0, "wave_3": 0}
    for unit in selected:
        if unit.pair_reason == "seed-seed":
            waves["wave_1"] += 1
        elif unit.pair_reason in {"seed-nearby", "nearby-seed"}:
            waves["wave_2"] += 1
        else:
            waves["wave_3"] += 1

    return ExecutionPlan(units=selected, waves=waves)


def execute_plan(
    plan: ExecutionPlan,
    *,
    concurrency_limit: int,
    timeout_ms: int,
    fetch_flights: Callable[[str, str, str, int], list[ProviderFlight]],
) -> tuple[list[tuple[str, str, dt.date, ProviderFlight]], dict[str, Any], list[str]]:
    timeout_ms = max(1000, timeout_ms)
    concurrency = max(1, concurrency_limit)

    combined: list[tuple[str, str, dt.date, ProviderFlight]] = []
    warnings: list[str] = []
    cache_hits = 0
    provider_calls = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(_fetch_with_cache, unit, timeout_ms, fetch_flights): unit
            for unit in plan.units
        }
        for future in as_completed(futures):
            unit = futures[future]
            try:
                flights, was_cache_hit = future.result()
                if was_cache_hit:
                    cache_hits += 1
                else:
                    provider_calls += 1
                for flight in flights:
                    combined.append((unit.origin_iata, unit.destination_iata, unit.travel_date, flight))
            except Exception:
                warnings.append("ryanair_unavailable_parcial")

    meta = {
        "planned_units": len(plan.units),
        "executed_units": len(plan.units),
        "provider_calls": provider_calls,
        "cache_hits": cache_hits,
        "concurrency_limit": concurrency,
        "timeout_ms": timeout_ms,
        "waves": plan.waves,
    }
    return combined, meta, warnings


def _fetch_with_cache(
    unit: ExecutionUnit,
    timeout_ms: int,
    fetch_flights: Callable[[str, str, str, int], list[ProviderFlight]],
) -> tuple[list[ProviderFlight], bool]:
    key = (unit.origin_iata, unit.destination_iata, str(unit.travel_date))
    now = time.time()

    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] <= _CACHE_TTL_SECONDS:
            return cached[1], True

    flights = fetch_flights(unit.origin_iata, unit.destination_iata, str(unit.travel_date), timeout_ms)

    with _CACHE_LOCK:
        _CACHE[key] = (now, flights)

    return flights, False
