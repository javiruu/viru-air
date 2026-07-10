from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import (
    FlightOfferCacheEntry,
    FlightPriceObservation,
    QuickSearchCacheEntry,
    QuickSearchNegativeCacheEntry,
)


@dataclass(frozen=True, slots=True)
class FareMemoryRetentionOptions:
    dry_run: bool
    batch_size: int
    today: dt.date
    now_utc: dt.datetime


@dataclass(frozen=True, slots=True)
class FareMemoryRetentionTableResult:
    table: str
    criterion: str
    candidates: int
    deleted: int
    batches: int
    dry_run: bool


@dataclass(frozen=True, slots=True)
class FareMemoryRetentionResult:
    dry_run: bool
    tables: list[FareMemoryRetentionTableResult]

    @property
    def candidates_total(self) -> int:
        return sum(table.candidates for table in self.tables)

    @property
    def deleted_total(self) -> int:
        return sum(table.deleted for table in self.tables)


def run_fare_memory_retention(session: Session, options: FareMemoryRetentionOptions) -> FareMemoryRetentionResult:
    tables = [
        _prune_price_observations(session, options),
        _prune_offer_cache_entries(session, options),
        _prune_search_cache_entries(session, options),
        _prune_negative_cache_entries(session, options),
    ]
    return FareMemoryRetentionResult(dry_run=options.dry_run, tables=tables)


def retention_result_to_payload(result: FareMemoryRetentionResult) -> dict:
    return {
        "dry_run": result.dry_run,
        "tables": [
            {
                "table": table.table,
                "criterion": table.criterion,
                "candidates": table.candidates,
                "deleted": table.deleted,
                "batches": table.batches,
                "dry_run": table.dry_run,
            }
            for table in result.tables
        ],
        "totals": {
            "candidates": result.candidates_total,
            "deleted": result.deleted_total,
        },
    }


def _prune_price_observations(
    session: Session,
    options: FareMemoryRetentionOptions,
) -> FareMemoryRetentionTableResult:
    criterion = "offer_departure_at_before_now"
    candidate_stmt = (
        select(FlightPriceObservation.id)
        .join(FlightOfferCacheEntry, FlightPriceObservation.offer_id == FlightOfferCacheEntry.id)
        .where(FlightOfferCacheEntry.departure_at < options.now_utc)
    )
    candidates = _count_statement(session, candidate_stmt)
    deleted, batches = _delete_entries(session, FlightPriceObservation, candidate_stmt, options)
    return FareMemoryRetentionTableResult(
        table="flight_price_observation",
        criterion=criterion,
        candidates=candidates,
        deleted=deleted,
        batches=batches,
        dry_run=options.dry_run,
    )


def _prune_offer_cache_entries(
    session: Session,
    options: FareMemoryRetentionOptions,
) -> FareMemoryRetentionTableResult:
    criterion = "departure_at_before_now_or_without_observations"
    observation_exists = (
        select(FlightPriceObservation.id)
        .where(FlightPriceObservation.offer_id == FlightOfferCacheEntry.id)
        .exists()
    )
    candidate_stmt = select(FlightOfferCacheEntry.id).where(
        or_(FlightOfferCacheEntry.departure_at < options.now_utc, ~observation_exists)
    )
    candidates = _count_statement(session, candidate_stmt)
    deleted, batches = _delete_entries(session, FlightOfferCacheEntry, candidate_stmt, options)
    return FareMemoryRetentionTableResult(
        table="flight_offer_cache_entry",
        criterion=criterion,
        candidates=candidates,
        deleted=deleted,
        batches=batches,
        dry_run=options.dry_run,
    )


def _prune_search_cache_entries(
    session: Session,
    options: FareMemoryRetentionOptions,
) -> FareMemoryRetentionTableResult:
    criterion = "travel_date_before_today"
    candidate_stmt = select(QuickSearchCacheEntry.id).where(QuickSearchCacheEntry.travel_date < options.today)
    candidates = _count_statement(session, candidate_stmt)
    deleted, batches = _delete_entries(session, QuickSearchCacheEntry, candidate_stmt, options)
    return FareMemoryRetentionTableResult(
        table="quick_search_cache_entry",
        criterion=criterion,
        candidates=candidates,
        deleted=deleted,
        batches=batches,
        dry_run=options.dry_run,
    )


def _prune_negative_cache_entries(
    session: Session,
    options: FareMemoryRetentionOptions,
) -> FareMemoryRetentionTableResult:
    criterion = "expires_at_or_retry_after_at_before_now"
    candidate_stmt = select(QuickSearchNegativeCacheEntry.id).where(
        or_(
            QuickSearchNegativeCacheEntry.expires_at < options.now_utc,
            QuickSearchNegativeCacheEntry.retry_after_at < options.now_utc,
        )
    )
    candidates = _count_statement(session, candidate_stmt)
    deleted, batches = _delete_entries(session, QuickSearchNegativeCacheEntry, candidate_stmt, options)
    return FareMemoryRetentionTableResult(
        table="quick_search_negative_cache_entry",
        criterion=criterion,
        candidates=candidates,
        deleted=deleted,
        batches=batches,
        dry_run=options.dry_run,
    )


def _count_statement(session: Session, candidate_stmt) -> int:
    return int(session.scalar(select(func.count()).select_from(candidate_stmt.subquery())) or 0)


def _delete_entries(
    session: Session,
    model: Any,
    candidate_stmt,
    options: FareMemoryRetentionOptions,
) -> tuple[int, int]:
    if options.dry_run:
        return 0, 0
    total_deleted = 0
    batches = 0
    while True:
        ids = session.scalars(candidate_stmt.limit(options.batch_size)).all()
        if not ids:
            break
        total_deleted += session.execute(delete(model).where(model.id.in_(ids))).rowcount or 0
        session.commit()
        batches += 1
    return total_deleted, batches
