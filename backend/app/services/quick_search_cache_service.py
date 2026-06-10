"""Shared persistent cache service for quick-search (V2.1).

Encapsulates access to quick_search_cache_entry table.
Cross-user cache: no user identity stored. TTL varies by result category.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import threading
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight
from app.infrastructure.db.models import QuickSearchCacheEntry
from app.services.quick_search_execution import (
    CacheResultCategory,
    build_cache_source_hash,
    build_unit_cache_key,
    classify_cache_result,
)

logger = logging.getLogger(__name__)

# Thread-safety: SQLAlchemy sessions are not thread-safe. Since execute_plan()
# uses ThreadPoolExecutor, all L2 cache DB access must be serialized.
_DB_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# TTL defaults (configurable via env)
# ---------------------------------------------------------------------------

_READY_TTL = int(os.getenv("QUICK_SEARCH_SHARED_CACHE_READY_TTL_SECONDS", "86400"))
_EMPTY_TTL = int(os.getenv("QUICK_SEARCH_SHARED_CACHE_EMPTY_TTL_SECONDS", "7200"))
_DEGRADED_TTL = int(os.getenv("QUICK_SEARCH_SHARED_CACHE_DEGRADED_TTL_SECONDS", "1800"))

_TTL_BY_CATEGORY: dict[CacheResultCategory, int] = {
    "ready": _READY_TTL,
    "empty": _EMPTY_TTL,
    "degraded": _DEGRADED_TTL,
}

# ---------------------------------------------------------------------------
# Serialization helpers (Phase 5)
# ---------------------------------------------------------------------------


def serialize_flights(flights: list[ProviderFlight]) -> list[dict[str, Any]]:
    """Serialize ProviderFlight list to JSON-safe dicts."""
    return [
        {
            "price": float(f.price),
            "currency": str(f.currency),
            "departure_time_local": f.departure_time_local,
            "captured_at": f.captured_at.isoformat() if f.captured_at else None,
            "source": str(f.source),
        }
        for f in flights
    ]


def deserialize_flights(raw: list[dict[str, Any]]) -> list[ProviderFlight]:
    """Deserialize JSON dicts back to ProviderFlight objects."""
    flights: list[ProviderFlight] = []
    for item in raw:
        captured_at_raw = item.get("captured_at")
        captured_at = dt.datetime.fromisoformat(captured_at_raw) if captured_at_raw else utc_now_naive()
        flights.append(
            ProviderFlight(
                price=float(item["price"]),
                currency=str(item.get("currency", "EUR")),
                departure_time_local=item.get("departure_time_local"),
                captured_at=captured_at,
                source=str(item.get("source", "ryanair-public")),
            )
        )
    return flights


def serialize_fetch_result(result: ProviderFetchResult) -> tuple[str, str]:
    """Serialize a ProviderFetchResult to (payload_json, warnings_json)."""
    payload = {
        "flights": serialize_flights(result.flights),
    }
    warnings_list = list(result.warnings) if result.warnings else []
    return json.dumps(payload, ensure_ascii=False), json.dumps(warnings_list, ensure_ascii=False)


def deserialize_fetch_result(payload_json: str, warnings_json: str) -> ProviderFetchResult:
    """Deserialize back to ProviderFetchResult."""
    payload = json.loads(payload_json)
    warnings = json.loads(warnings_json) if warnings_json else []
    flights = deserialize_flights(payload.get("flights", []))
    return ProviderFetchResult(flights=flights, warnings=warnings)


# ---------------------------------------------------------------------------
# Cache service operations
# ---------------------------------------------------------------------------


def _ttl_for_category(category: CacheResultCategory) -> int:
    return max(60, _TTL_BY_CATEGORY.get(category, _READY_TTL))


def get_fresh_entry(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
    source_hash: str,
) -> QuickSearchCacheEntry | None:
    """Retrieve a fresh (non-expired) cache entry for the given unit.

    Thread-safe: protected by _DB_LOCK.
    """
    now = utc_now_naive()
    key = build_unit_cache_key(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider=provider,
    )
    stmt = (
        select(QuickSearchCacheEntry)
        .where(
            QuickSearchCacheEntry.origin_iata == key[0],
            QuickSearchCacheEntry.destination_iata == key[1],
            QuickSearchCacheEntry.travel_date == dt.date.fromisoformat(key[2]) if isinstance(key[2], str) else key[2],
            QuickSearchCacheEntry.provider == key[3],
            QuickSearchCacheEntry.source_hash == source_hash,
            QuickSearchCacheEntry.expires_at_utc > now,
        )
        .order_by(QuickSearchCacheEntry.expires_at_utc.desc())
        .limit(1)
    )
    with _DB_LOCK:
        entry = db.scalar(stmt)
        if entry:
            entry.last_accessed_at_utc = now
            db.commit()
    return entry


def set_cache_entry(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
    source_hash: str,
    category: CacheResultCategory,
    payload_json: str,
    warnings_json: str,
    provider_latency_ms: int | None = None,
) -> QuickSearchCacheEntry:
    """Persist a cache entry. Uses upsert semantics via unique constraint."""
    ttl = _ttl_for_category(category)
    now = utc_now_naive()
    expires_at = now + dt.timedelta(seconds=ttl)

    if isinstance(travel_date, str):
        travel_date_obj = dt.date.fromisoformat(travel_date)
    else:
        travel_date_obj = travel_date

    with _DB_LOCK:
        # Delete existing entry for the same unique key before inserting
        key = build_unit_cache_key(
            origin_iata=origin_iata,
            destination_iata=destination_iata,
            travel_date=travel_date,
            provider=provider,
        )
        db.execute(
            delete(QuickSearchCacheEntry).where(
                QuickSearchCacheEntry.origin_iata == key[0],
                QuickSearchCacheEntry.destination_iata == key[1],
                QuickSearchCacheEntry.travel_date == travel_date_obj,
                QuickSearchCacheEntry.provider == key[3],
                QuickSearchCacheEntry.source_hash == source_hash,
            )
        )

        entry = QuickSearchCacheEntry(
            origin_iata=str(origin_iata).strip().upper(),
            destination_iata=str(destination_iata).strip().upper(),
            travel_date=travel_date_obj,
            provider=str(provider).strip().lower(),
            status=category,
            ttl_seconds=ttl,
            expires_at_utc=expires_at,
            captured_at_utc=now,
            last_accessed_at_utc=now,
            payload_json=payload_json,
            warnings_json=warnings_json,
            source_hash=source_hash,
            provider_latency_ms=provider_latency_ms,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
    return entry


def get_or_set_cache_entry(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
    fetch_result: ProviderFetchResult,
    category: CacheResultCategory | None = None,
    provider_latency_ms: int | None = None,
    currency: str = "EUR",
) -> tuple[ProviderFetchResult, bool]:
    """Read-through cache: return fresh entry if exists, otherwise persist and return.

    Returns (result, was_cache_hit).
    """
    source_hash = build_cache_source_hash(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider=provider,
        currency=currency,
    )
    entry = get_fresh_entry(
        db,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider=provider,
        source_hash=source_hash,
    )
    if entry is not None:
        logger.debug(
            "quick_search_cache_hit origin=%s destination=%s date=%s provider=%s status=%s",
            origin_iata, destination_iata, travel_date, provider, entry.status,
        )
        return deserialize_fetch_result(entry.payload_json, entry.warnings_json), True

    if category is None:
        category = classify_cache_result(
            flights=fetch_result.flights,
            warnings=fetch_result.warnings,
        )
    payload_json, warnings_json = serialize_fetch_result(fetch_result)
    set_cache_entry(
        db,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider=provider,
        source_hash=source_hash,
        category=category,
        payload_json=payload_json,
        warnings_json=warnings_json,
        provider_latency_ms=provider_latency_ms,
    )
    logger.debug(
        "quick_search_cache_miss origin=%s destination=%s date=%s provider=%s category=%s",
        origin_iata, destination_iata, travel_date, provider, category,
    )
    return fetch_result, False


def prune_expired_entries(db: Session, *, batch_size: int = 200) -> int:
    """Delete expired cache entries. Returns count of deleted rows.

    Thread-safe: protected by _DB_LOCK.
    Uses a subquery because SQLAlchemy Delete does not support .limit().
    """
    now = utc_now_naive()
    with _DB_LOCK:
        subquery = (
            select(QuickSearchCacheEntry.id)
            .where(QuickSearchCacheEntry.expires_at_utc <= now)
            .limit(batch_size)
            .scalar_subquery()
        )
        result = db.execute(
            delete(QuickSearchCacheEntry).where(
                QuickSearchCacheEntry.id.in_(subquery)
            )
        )
        db.commit()
    deleted = result.rowcount
    if deleted > 0:
        logger.info("quick_search_cache_pruned count=%d", deleted)
    return deleted


def prune_expired_entries_async(*, batch_size: int = 200) -> None:
    """Fire-and-forget pruning in a daemon thread.

    Does not block the caller. Creates its own DB session internally.
    Failures are logged but never propagated.
    """
    from app.infrastructure.db.session import SessionLocal

    def _prune() -> None:
        session = SessionLocal()
        try:
            deleted = prune_expired_entries(session, batch_size=batch_size)
            if deleted > 0:
                logger.debug("quick_search_cache_pruned_async count=%d", deleted)
        except Exception:
            logger.warning("quick_search_cache_prune_async_failed", exc_info=True)
        finally:
            session.close()

    threading.Thread(target=_prune, daemon=True).start()


def get_cache_stats(db: Session) -> dict[str, int]:
    """Return cache stats for observability."""
    from sqlalchemy import func
    now = utc_now_naive()

    def _count(where=None):
        stmt = select(func.count()).select_from(QuickSearchCacheEntry)
        if where is not None:
            stmt = stmt.where(where)
        return db.execute(stmt).scalar() or 0

    with _DB_LOCK:
        return {
            "total_entries": _count(),
            "fresh_entries": _count(QuickSearchCacheEntry.expires_at_utc > now),
            "expired_entries": _count(QuickSearchCacheEntry.expires_at_utc <= now),
            "status_ready": _count(QuickSearchCacheEntry.status == "ready"),
            "status_empty": _count(QuickSearchCacheEntry.status == "empty"),
            "status_degraded": _count(QuickSearchCacheEntry.status == "degraded"),
        }
