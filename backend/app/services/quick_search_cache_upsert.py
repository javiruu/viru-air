from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.infrastructure.db.models import QuickSearchCacheEntry

CacheValue = str | int | dt.date | dt.datetime | None

_CONFLICT_COLUMNS = (
    "origin_iata",
    "destination_iata",
    "travel_date",
    "provider",
    "source_hash",
)
_UPDATE_COLUMNS = (
    "search_fingerprint",
    "canonical_request_json",
    "provider_set_json",
    "status",
    "freshness_status",
    "ttl_seconds",
    "expires_at_utc",
    "captured_at_utc",
    "last_accessed_at_utc",
    "payload_json",
    "warnings_json",
    "provider_latency_ms",
    "result_count",
    "confidence_score",
)


class QuickSearchCacheUpsertError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class QuickSearchCacheUpsertValues:
    origin_iata: str
    destination_iata: str
    travel_date: dt.date
    provider: str
    source_hash: str
    status: str
    ttl_seconds: int
    expires_at_utc: dt.datetime
    captured_at_utc: dt.datetime
    last_accessed_at_utc: dt.datetime
    payload_json: str
    warnings_json: str
    provider_latency_ms: int | None = None


def upsert_quick_search_cache_entry(
    db: Session,
    values: QuickSearchCacheUpsertValues,
) -> QuickSearchCacheEntry:
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "postgresql":
        db.execute(_build_postgresql_upsert(values))
    elif dialect_name == "sqlite":
        db.execute(_build_sqlite_upsert(values))
    else:
        return _fallback_upsert(db, values)

    db.commit()
    return _get_cache_entry_by_key(db, values)


def _build_postgresql_upsert(values: QuickSearchCacheUpsertValues):
    stmt = postgresql_insert(QuickSearchCacheEntry).values(**_insert_values(values))
    return stmt.on_conflict_do_update(
        constraint="uq_quick_search_cache_unit",
        set_={column: getattr(stmt.excluded, column) for column in _UPDATE_COLUMNS},
    )


def _build_sqlite_upsert(values: QuickSearchCacheUpsertValues):
    stmt = sqlite_insert(QuickSearchCacheEntry).values(**_insert_values(values))
    return stmt.on_conflict_do_update(
        index_elements=list(_CONFLICT_COLUMNS),
        set_={column: getattr(stmt.excluded, column) for column in _UPDATE_COLUMNS},
    )


def _fallback_upsert(db: Session, values: QuickSearchCacheUpsertValues) -> QuickSearchCacheEntry:
    entry = db.scalar(_select_by_key(values))
    if entry is None:
        entry = QuickSearchCacheEntry(**_insert_values(values))
        db.add(entry)
    else:
        for column, column_value in _mutable_values(values).items():
            setattr(entry, column, column_value)
    db.commit()
    db.refresh(entry)
    return entry


def _get_cache_entry_by_key(db: Session, values: QuickSearchCacheUpsertValues) -> QuickSearchCacheEntry:
    entry = db.scalar(_select_by_key(values))
    if entry is None:
        raise QuickSearchCacheUpsertError("quick search cache upsert did not persist the requested unit key")
    return entry


def _select_by_key(values: QuickSearchCacheUpsertValues):
    return select(QuickSearchCacheEntry).where(
        QuickSearchCacheEntry.origin_iata == values.origin_iata,
        QuickSearchCacheEntry.destination_iata == values.destination_iata,
        QuickSearchCacheEntry.travel_date == values.travel_date,
        QuickSearchCacheEntry.provider == values.provider,
        QuickSearchCacheEntry.source_hash == values.source_hash,
    )


def _insert_values(values: QuickSearchCacheUpsertValues) -> dict[str, CacheValue]:
    return {
        "origin_iata": values.origin_iata,
        "destination_iata": values.destination_iata,
        "travel_date": values.travel_date,
        "provider": values.provider,
        "source_hash": values.source_hash,
        **_mutable_values(values),
    }


def _mutable_values(values: QuickSearchCacheUpsertValues) -> dict[str, CacheValue]:
    return {
        "search_fingerprint": None,
        "canonical_request_json": None,
        "provider_set_json": None,
        "status": values.status,
        "freshness_status": "fresh",
        "ttl_seconds": values.ttl_seconds,
        "expires_at_utc": values.expires_at_utc,
        "captured_at_utc": values.captured_at_utc,
        "last_accessed_at_utc": values.last_accessed_at_utc,
        "payload_json": values.payload_json,
        "warnings_json": values.warnings_json,
        "provider_latency_ms": values.provider_latency_ms,
        "result_count": 0,
        "confidence_score": None,
    }
