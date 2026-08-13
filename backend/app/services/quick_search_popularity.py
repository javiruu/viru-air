from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import inspect, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import (
    QuickSearchPopularityCounter,
    QuickSearchPopularityDaily,
)


PopularityValue = str | int | dt.date | dt.datetime
_CONFLICT_COLUMNS = ("origin_iata", "destination_iata", "travel_date", "currency")
_DAILY_CONFLICT_COLUMNS = (
    "search_date",
    "origin_iata",
    "destination_iata",
    "currency",
)


class QuickSearchPopularityUpsertError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class QuickSearchPopularitySignal:
    origin_iata: str
    destination_iata: str
    travel_date: dt.date
    currency: str = "EUR"
    searched_at: dt.datetime | None = None


def record_quick_search_popularity(
    db: Session,
    signal: QuickSearchPopularitySignal,
) -> QuickSearchPopularityCounter:
    normalized = _normalize_signal(signal)
    dialect_name = db.get_bind().dialect.name
    daily_table_available = inspect(db.get_bind()).has_table(
        QuickSearchPopularityDaily.__tablename__
    )
    try:
        if dialect_name == "postgresql":
            db.execute(_build_postgresql_upsert(normalized))
            if daily_table_available:
                db.execute(_build_postgresql_daily_upsert(normalized))
        elif dialect_name == "sqlite":
            db.execute(_build_sqlite_upsert(normalized))
            if daily_table_available:
                db.execute(_build_sqlite_daily_upsert(normalized))
        else:
            entry = _fallback_upsert(db, normalized)
            if daily_table_available:
                _fallback_daily_upsert(db, normalized)
            db.commit()
            db.refresh(entry)
            return entry

        db.commit()
    except Exception:
        db.rollback()
        raise
    return _get_counter_by_key(db, normalized)


def _normalize_signal(signal: QuickSearchPopularitySignal) -> QuickSearchPopularitySignal:
    searched_at = signal.searched_at or utc_now_naive()
    if searched_at.tzinfo is not None:
        searched_at = searched_at.astimezone(dt.UTC).replace(tzinfo=None)
    return QuickSearchPopularitySignal(
        origin_iata=signal.origin_iata.strip().upper(),
        destination_iata=signal.destination_iata.strip().upper(),
        travel_date=signal.travel_date,
        currency=signal.currency.strip().upper() or "EUR",
        searched_at=searched_at,
    )


def _build_postgresql_upsert(signal: QuickSearchPopularitySignal):
    stmt = postgresql_insert(QuickSearchPopularityCounter).values(**_insert_values(signal))
    return stmt.on_conflict_do_update(
        constraint="uq_qs_popularity_route_day_currency",
        set_=_update_values(signal),
    )


def _build_sqlite_upsert(signal: QuickSearchPopularitySignal):
    stmt = sqlite_insert(QuickSearchPopularityCounter).values(**_insert_values(signal))
    return stmt.on_conflict_do_update(
        index_elements=list(_CONFLICT_COLUMNS),
        set_=_update_values(signal),
    )


def _build_postgresql_daily_upsert(signal: QuickSearchPopularitySignal):
    stmt = postgresql_insert(QuickSearchPopularityDaily).values(
        **_daily_insert_values(signal)
    )
    return stmt.on_conflict_do_update(
        constraint="uq_qs_popularity_daily_route_currency",
        set_=_daily_update_values(signal),
    )


def _build_sqlite_daily_upsert(signal: QuickSearchPopularitySignal):
    stmt = sqlite_insert(QuickSearchPopularityDaily).values(**_daily_insert_values(signal))
    return stmt.on_conflict_do_update(
        index_elements=list(_DAILY_CONFLICT_COLUMNS),
        set_=_daily_update_values(signal),
    )


def _fallback_upsert(
    db: Session,
    signal: QuickSearchPopularitySignal,
) -> QuickSearchPopularityCounter:
    entry = db.scalar(_select_by_key(signal))
    if entry is None:
        entry = QuickSearchPopularityCounter(**_insert_values(signal))
        db.add(entry)
    else:
        searched_at = _searched_at(signal)
        entry.search_count += 1
        entry.last_searched_at = searched_at
        entry.updated_at = searched_at
    return entry


def _fallback_daily_upsert(
    db: Session,
    signal: QuickSearchPopularitySignal,
) -> QuickSearchPopularityDaily:
    entry = db.scalar(_select_daily_by_key(signal))
    if entry is None:
        entry = QuickSearchPopularityDaily(**_daily_insert_values(signal))
        db.add(entry)
    else:
        searched_at = _searched_at(signal)
        entry.search_count += 1
        entry.last_searched_at = searched_at
        entry.updated_at = searched_at
    return entry


def _get_counter_by_key(
    db: Session,
    signal: QuickSearchPopularitySignal,
) -> QuickSearchPopularityCounter:
    entry = db.scalar(_select_by_key(signal))
    if entry is None:
        raise QuickSearchPopularityUpsertError("quick search popularity counter was not persisted")
    return entry


def _select_by_key(signal: QuickSearchPopularitySignal):
    return select(QuickSearchPopularityCounter).where(
        QuickSearchPopularityCounter.origin_iata == signal.origin_iata,
        QuickSearchPopularityCounter.destination_iata == signal.destination_iata,
        QuickSearchPopularityCounter.travel_date == signal.travel_date,
        QuickSearchPopularityCounter.currency == signal.currency,
    )


def _select_daily_by_key(signal: QuickSearchPopularitySignal):
    return select(QuickSearchPopularityDaily).where(
        QuickSearchPopularityDaily.search_date == _searched_at(signal).date(),
        QuickSearchPopularityDaily.origin_iata == signal.origin_iata,
        QuickSearchPopularityDaily.destination_iata == signal.destination_iata,
        QuickSearchPopularityDaily.currency == signal.currency,
    )


def _insert_values(signal: QuickSearchPopularitySignal) -> dict[str, PopularityValue]:
    searched_at = _searched_at(signal)
    return {
        "origin_iata": signal.origin_iata,
        "destination_iata": signal.destination_iata,
        "travel_date": signal.travel_date,
        "currency": signal.currency,
        "search_count": 1,
        "first_searched_at": searched_at,
        "last_searched_at": searched_at,
        "created_at": searched_at,
        "updated_at": searched_at,
    }


def _update_values(signal: QuickSearchPopularitySignal) -> dict[str, PopularityValue]:
    return {
        "search_count": QuickSearchPopularityCounter.search_count + 1,
        "last_searched_at": _searched_at(signal),
        "updated_at": _searched_at(signal),
    }


def _daily_insert_values(signal: QuickSearchPopularitySignal) -> dict[str, PopularityValue]:
    searched_at = _searched_at(signal)
    return {
        "search_date": searched_at.date(),
        "origin_iata": signal.origin_iata,
        "destination_iata": signal.destination_iata,
        "currency": signal.currency,
        "search_count": 1,
        "first_searched_at": searched_at,
        "last_searched_at": searched_at,
        "created_at": searched_at,
        "updated_at": searched_at,
    }


def _daily_update_values(signal: QuickSearchPopularitySignal) -> dict[str, PopularityValue]:
    return {
        "search_count": QuickSearchPopularityDaily.search_count + 1,
        "last_searched_at": _searched_at(signal),
        "updated_at": _searched_at(signal),
    }


def _searched_at(signal: QuickSearchPopularitySignal) -> dt.datetime:
    if signal.searched_at is None:
        raise QuickSearchPopularityUpsertError("normalized popularity signal is missing searched_at")
    return signal.searched_at
