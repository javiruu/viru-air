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
from app.infrastructure.db.models import QuickSearchCacheEntry, QuickSearchNegativeCacheEntry
from app.services.fare_memory import build_freshness_payload
from app.services.quick_search_execution import (
    CacheResultCategory,
    build_cache_source_hash,
    build_unit_cache_key,
    classify_cache_result,
)
from app.services.quick_search_negative_cache_policy import (
    is_provider_backoff_reason,
    negative_freshness_status_for_reason,
    negative_result_for_reason,
    negative_ttl_for_reason,
)
from app.services.quick_search_cache_upsert import (
    QuickSearchCacheUpsertValues,
    upsert_quick_search_cache_entry,
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
_NEGATIVE_TTL = int(os.getenv("QUICK_SEARCH_NEGATIVE_CACHE_TTL_SECONDS", "1800"))
_PROVIDER_ERROR_TTL = int(os.getenv("QUICK_SEARCH_NEGATIVE_PROVIDER_ERROR_TTL_SECONDS", "600"))
_PROVIDER_ERROR_BACKOFF_MAX_TTL = int(os.getenv("QUICK_SEARCH_NEGATIVE_PROVIDER_ERROR_MAX_TTL_SECONDS", "3600"))

_TTL_BY_CATEGORY: dict[CacheResultCategory, int] = {
    "ready": _READY_TTL,
    "empty": _EMPTY_TTL,
    "degraded": _DEGRADED_TTL,
}

_CATEGORY_SOURCE = {
    "ready": "provider_cache",
    "empty": "negative_cache",
    "degraded": "provider_cache",
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


def serialize_exact_search_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def deserialize_exact_search_payload(payload_json: str) -> dict[str, Any]:
    return json.loads(payload_json)


# ---------------------------------------------------------------------------
# Cache service operations
# ---------------------------------------------------------------------------


def _normalize_reference_now(now: dt.datetime | None = None) -> dt.datetime:
    reference_now = now or utc_now_naive()
    if reference_now.tzinfo:
        return reference_now.astimezone(dt.UTC).replace(tzinfo=None)
    return reference_now


def _normalize_travel_date(value: dt.date | str) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def resolve_ready_cache_ttl_seconds(
    *,
    travel_date: dt.date | str,
    provider: str,
    now: dt.datetime | None = None,
) -> int:
    reference_now = _normalize_reference_now(now)
    departure_date = _normalize_travel_date(travel_date)
    days_until_departure = (departure_date - reference_now.date()).days

    if days_until_departure < 0:
        return 60
    if days_until_departure > 90:
        ttl = 12 * 60 * 60
    elif days_until_departure >= 60:
        ttl = 8 * 60 * 60
    elif days_until_departure >= 30:
        ttl = 4 * 60 * 60
    elif days_until_departure >= 14:
        ttl = 2 * 60 * 60
    elif days_until_departure >= 3:
        ttl = 45 * 60
    elif days_until_departure >= 1:
        ttl = 15 * 60
    else:
        ttl = 5 * 60

    provider_id = str(provider).strip().lower()
    if provider_id in {"manual", "mock", "fixture"}:
        return min(ttl, 15 * 60)
    return ttl


def _ttl_for_category(
    category: CacheResultCategory,
    *,
    travel_date: dt.date | str,
    provider: str,
    now: dt.datetime | None = None,
) -> int:
    if category == "ready":
        return max(60, resolve_ready_cache_ttl_seconds(travel_date=travel_date, provider=provider, now=now))
    return max(60, _TTL_BY_CATEGORY.get(category, _READY_TTL))


def build_negative_cache_fingerprint(
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
    currency: str = "EUR",
) -> str:
    return build_cache_source_hash(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider=provider,
        currency=currency,
    ).replace("qs_", "qsn_")


def _negative_ttl_for_reason(reason: str) -> int:
    return negative_ttl_for_reason(
        reason,
        default_negative_ttl=_NEGATIVE_TTL,
        default_provider_error_ttl=_PROVIDER_ERROR_TTL,
    )


def _is_provider_backoff_reason(reason: str) -> bool:
    return is_provider_backoff_reason(reason)


def _deterministic_backoff_jitter_seconds(*, negative_fingerprint: str, reason: str) -> int:
    seed = f"{negative_fingerprint}:{reason}"
    return sum(ord(ch) for ch in seed) % 31


def _resolve_provider_backoff_seconds(
    *,
    existing_entry: QuickSearchNegativeCacheEntry | None,
    negative_fingerprint: str,
    reason: str,
    now: dt.datetime,
    requested_retry_after_at: dt.datetime | None,
) -> int:
    base_seconds = max(60, _negative_ttl_for_reason(reason))
    if requested_retry_after_at is not None:
        requested_seconds = max(60, int((requested_retry_after_at - now).total_seconds()))
        base_seconds = max(base_seconds, requested_seconds)

    if existing_entry is None or existing_entry.reason != reason:
        return min(_PROVIDER_ERROR_BACKOFF_MAX_TTL, base_seconds + _deterministic_backoff_jitter_seconds(
            negative_fingerprint=negative_fingerprint,
            reason=reason,
        ))

    previous_until = existing_entry.retry_after_at or existing_entry.expires_at
    previous_window_seconds = max(60, int((previous_until - existing_entry.observed_at).total_seconds()))
    escalated = min(_PROVIDER_ERROR_BACKOFF_MAX_TTL, max(base_seconds, previous_window_seconds * 2))
    return min(
        _PROVIDER_ERROR_BACKOFF_MAX_TTL,
        escalated + _deterministic_backoff_jitter_seconds(
            negative_fingerprint=negative_fingerprint,
            reason=reason,
        ),
    )


def _negative_freshness_status_for_reason(reason: str) -> str:
    return negative_freshness_status_for_reason(reason)


def _negative_result_for_reason(reason: str) -> ProviderFetchResult:
    return negative_result_for_reason(reason)


def build_effective_freshness(entry: QuickSearchCacheEntry, *, now: dt.datetime | None = None) -> dict[str, Any]:
    reference_now = _normalize_reference_now(now)
    ttl_seconds = max(1, int(entry.ttl_seconds or 0))
    age_seconds = max(0, int((reference_now - entry.captured_at_utc).total_seconds()))

    if entry.status == "ready" and entry.travel_date < reference_now.date():
        status = "expired"
    elif entry.status == "ready":
        status = "warm" if age_seconds >= ttl_seconds // 2 else "fresh"
    elif entry.status == "empty":
        status = "negative_stale" if age_seconds >= ttl_seconds // 2 else "negative_fresh"
    else:
        status = "provider_error_stale" if age_seconds >= ttl_seconds // 2 else "provider_error_fresh"

    return build_freshness_payload(
        status=status,
        observed_at=entry.captured_at_utc,
        expires_at=entry.expires_at_utc,
        source=_CATEGORY_SOURCE.get(entry.status, "provider_cache"),
        now=reference_now,
        confidence_score=float(entry.confidence_score) if entry.confidence_score is not None else None,
        validation_status="revalidated" if status == "fresh" else "observed",
    )


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
    now = utc_now_naive()

    if isinstance(travel_date, str):
        travel_date_obj = dt.date.fromisoformat(travel_date)
    else:
        travel_date_obj = travel_date
    ttl = _ttl_for_category(
        category,
        travel_date=travel_date_obj,
        provider=provider,
        now=now,
    )
    expires_at = now + dt.timedelta(seconds=ttl)

    with _DB_LOCK:
        key = build_unit_cache_key(
            origin_iata=origin_iata,
            destination_iata=destination_iata,
            travel_date=travel_date,
            provider=provider,
        )
        entry = upsert_quick_search_cache_entry(
            db,
            QuickSearchCacheUpsertValues(
                origin_iata=key[0],
                destination_iata=key[1],
                travel_date=travel_date_obj,
                provider=key[3],
                source_hash=source_hash,
                status=category,
                ttl_seconds=ttl,
                expires_at_utc=expires_at,
                captured_at_utc=now,
                last_accessed_at_utc=now,
                payload_json=payload_json,
                warnings_json=warnings_json,
                provider_latency_ms=provider_latency_ms,
            ),
        )
    return entry


def get_exact_search_cache_entry(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    search_fingerprint: str,
) -> QuickSearchCacheEntry | None:
    return get_fresh_entry(
        db,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider="search_exact",
        source_hash=search_fingerprint,
    )


def set_exact_search_cache_entry(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    search_fingerprint: str,
    canonical_request_json: str,
    provider_set_json: str,
    response_payload: dict[str, Any],
    category: CacheResultCategory,
    confidence_score: float | None = None,
) -> QuickSearchCacheEntry:
    payload_json = serialize_exact_search_payload(response_payload)
    result_count = len(response_payload.get("results", [])) if isinstance(response_payload.get("results"), list) else 0
    entry = set_cache_entry(
        db,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider="search_exact",
        source_hash=search_fingerprint,
        category=category,
        payload_json=payload_json,
        warnings_json="[]",
    )
    with _DB_LOCK:
        entry.search_fingerprint = search_fingerprint
        entry.canonical_request_json = canonical_request_json
        entry.provider_set_json = provider_set_json
        entry.result_count = result_count
        entry.confidence_score = confidence_score
        entry.freshness_status = build_effective_freshness(entry)["status"]
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


def get_fresh_negative_cache_entry(
    db: Session,
    *,
    negative_fingerprint: str,
) -> QuickSearchNegativeCacheEntry | None:
    now = utc_now_naive()
    stmt = (
        select(QuickSearchNegativeCacheEntry)
        .where(
            QuickSearchNegativeCacheEntry.negative_fingerprint == negative_fingerprint,
            QuickSearchNegativeCacheEntry.expires_at > now,
        )
        .order_by(QuickSearchNegativeCacheEntry.expires_at.desc())
        .limit(1)
    )
    with _DB_LOCK:
        entry = db.scalar(stmt)
        if entry:
            entry.hit_count = int(entry.hit_count or 0) + 1
            db.commit()
            db.refresh(entry)
    return entry


def set_negative_cache_entry(
    db: Session,
    *,
    negative_fingerprint: str,
    scope: str,
    reason: str,
    provider: str | None,
    canonical_request_json: str,
    retry_after_at: dt.datetime | None = None,
) -> QuickSearchNegativeCacheEntry:
    now = utc_now_naive()
    existing_entry: QuickSearchNegativeCacheEntry | None = None
    if _is_provider_backoff_reason(reason):
        existing_entry = db.scalar(
            select(QuickSearchNegativeCacheEntry)
            .where(QuickSearchNegativeCacheEntry.negative_fingerprint == negative_fingerprint)
            .order_by(QuickSearchNegativeCacheEntry.expires_at.desc())
            .limit(1)
        )
        ttl = _resolve_provider_backoff_seconds(
            existing_entry=existing_entry,
            negative_fingerprint=negative_fingerprint,
            reason=reason,
            now=now,
            requested_retry_after_at=retry_after_at,
        )
        retry_after_at = now + dt.timedelta(seconds=ttl)
    else:
        ttl = max(60, _negative_ttl_for_reason(reason))
    expires_at = now + dt.timedelta(seconds=ttl)
    freshness_status = _negative_freshness_status_for_reason(reason)

    with _DB_LOCK:
        db.execute(
            delete(QuickSearchNegativeCacheEntry).where(
                QuickSearchNegativeCacheEntry.negative_fingerprint == negative_fingerprint,
            )
        )
        entry = QuickSearchNegativeCacheEntry(
            negative_fingerprint=negative_fingerprint,
            scope=scope,
            reason=reason,
            provider=provider,
            canonical_request_json=canonical_request_json,
            observed_at=now,
            expires_at=expires_at,
            freshness_status=freshness_status,
            retry_after_at=retry_after_at,
            hit_count=0,
            created_at=now,
            updated_at=now,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
    return entry


def resolve_negative_cache_result(entry: QuickSearchNegativeCacheEntry) -> ProviderFetchResult:
    return _negative_result_for_reason(entry.reason)


def prune_expired_entries(db: Session, *, batch_size: int = 200) -> int:
    """Delete expired cache entries. Returns count of deleted rows.

    Thread-safe: protected by _DB_LOCK.
    Prunes both positive (QuickSearchCacheEntry) and negative
    (QuickSearchNegativeCacheEntry) expired entries.
    Uses a subquery because SQLAlchemy Delete does not support .limit().
    """
    now = utc_now_naive()
    with _DB_LOCK:
        # Prune expired positive cache entries
        pos_subquery = (
            select(QuickSearchCacheEntry.id)
            .where(QuickSearchCacheEntry.expires_at_utc <= now)
            .limit(batch_size)
            .scalar_subquery()
        )
        pos_result = db.execute(
            delete(QuickSearchCacheEntry).where(
                QuickSearchCacheEntry.id.in_(pos_subquery)
            )
        )

        # Prune expired negative cache entries
        neg_subquery = (
            select(QuickSearchNegativeCacheEntry.id)
            .where(QuickSearchNegativeCacheEntry.expires_at <= now)
            .limit(batch_size)
            .scalar_subquery()
        )
        neg_result = db.execute(
            delete(QuickSearchNegativeCacheEntry).where(
                QuickSearchNegativeCacheEntry.id.in_(neg_subquery)
            )
        )

        db.commit()
    pos_deleted = pos_result.rowcount
    neg_deleted = neg_result.rowcount
    total = pos_deleted + neg_deleted
    if total > 0:
        logger.info(
            "quick_search_cache_pruned positive=%d negative=%d", pos_deleted, neg_deleted
        )
    return total


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
