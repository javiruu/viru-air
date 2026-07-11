from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("app.fare_memory.metrics")


def log_fare_memory_quick_search_counters(
    *,
    query_trace_id: str | None,
    pipeline_counters: dict[str, Any],
) -> None:
    cache_hits = _as_int(pipeline_counters.get("cache_hits"))
    cache_misses = _as_int(pipeline_counters.get("cache_misses"))
    l1_cache_hits = _as_int(pipeline_counters.get("l1_cache_hits"))
    l2_cache_hits = _as_int(pipeline_counters.get("l2_cache_hits"))
    negative_cache_hits = _as_int(pipeline_counters.get("negative_cache_hits"))
    provider_calls_avoided = _as_int(pipeline_counters.get("provider_calls_avoided"))

    base = {"query_trace_id": query_trace_id or None}
    if cache_hits:
        _emit(
            "fare_memory_cache_hit",
            **base,
            cache_hits=cache_hits,
            l1_cache_hits=l1_cache_hits,
            l2_cache_hits=l2_cache_hits,
            negative_cache_hits=negative_cache_hits,
        )
    if cache_misses:
        _emit("fare_memory_cache_miss", **base, cache_misses=cache_misses)
    if provider_calls_avoided:
        _emit("fare_memory_provider_call_avoided", **base, provider_calls_avoided=provider_calls_avoided)
    if negative_cache_hits:
        _emit("fare_memory_negative_cache_hit", **base, negative_cache_hits=negative_cache_hits)


def log_fare_memory_watchlist_backfill_applied(
    *,
    candidates_count: int,
    inserted_count: int,
    source: str,
) -> None:
    if inserted_count <= 0:
        return
    _emit(
        "fare_memory_watchlist_backfill_applied",
        candidates_count=max(0, int(candidates_count)),
        inserted_count=max(0, int(inserted_count)),
        source=source,
    )


def log_fare_memory_retention_pruned(payload: dict[str, Any]) -> None:
    totals = payload.get("totals") if isinstance(payload.get("totals"), dict) else {}
    _emit(
        "fare_memory_retention_pruned",
        dry_run=bool(payload.get("dry_run")),
        candidates=_as_int(totals.get("candidates")),
        deleted=_as_int(totals.get("deleted")),
        table_count=len(payload.get("tables") or []),
    )


def _emit(event: str, **fields: Any) -> None:
    logger.info(json.dumps({"event": event, **fields}, ensure_ascii=False, sort_keys=True))


def _as_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
