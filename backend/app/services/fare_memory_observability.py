from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import (
    FlightOfferCacheEntry,
    FlightPriceObservation,
    QuickSearchCacheEntry,
    QuickSearchNegativeCacheEntry,
    QuickSearchPopularityCounter,
    RevalidationJob,
)


def build_fare_memory_health_snapshot(
    db: Session,
    *,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    reference_now = now or utc_now_naive()
    recent_from = reference_now - dt.timedelta(hours=24)

    return {
        "generated_at": reference_now.isoformat(),
        "search_cache": {
            "total_entries": _count_all(db, QuickSearchCacheEntry.id),
            "freshness": _count_by_field(db, QuickSearchCacheEntry.freshness_status),
            "status": _count_by_field(db, QuickSearchCacheEntry.status),
            "expired_entries": int(
                db.scalar(
                    select(func.count(QuickSearchCacheEntry.id)).where(
                        QuickSearchCacheEntry.expires_at_utc < reference_now,
                    )
                )
                or 0
            ),
        },
        "negative_cache": {
            "total_entries": _count_all(db, QuickSearchNegativeCacheEntry.id),
            "active_entries": int(
                db.scalar(
                    select(func.count(QuickSearchNegativeCacheEntry.id)).where(
                        QuickSearchNegativeCacheEntry.expires_at >= reference_now,
                    )
                )
                or 0
            ),
            "freshness": _count_by_field(db, QuickSearchNegativeCacheEntry.freshness_status),
            "reasons": _count_by_field(db, QuickSearchNegativeCacheEntry.reason),
        },
        "popularity": {
            "total_routes": _count_all(db, QuickSearchPopularityCounter.id),
            "top_routes": _top_popular_routes(db),
        },
        "offer_memory": {
            "offer_entries": _count_all(db, FlightOfferCacheEntry.id),
            "price_observations": _count_all(db, FlightPriceObservation.id),
            "observations_last_24h": int(
                db.scalar(
                    select(func.count(FlightPriceObservation.id)).where(
                        FlightPriceObservation.observed_at >= recent_from,
                    )
                )
                or 0
            ),
            "changed_observations_last_24h": int(
                db.scalar(
                    select(func.count(FlightPriceObservation.id)).where(
                        FlightPriceObservation.observed_at >= recent_from,
                        FlightPriceObservation.price_changed_since_last_seen.is_(True),
                    )
                )
                or 0
            ),
            "validation_status": _count_by_field(db, FlightPriceObservation.validation_status),
        },
        "revalidation_jobs": {
            "total_entries": _count_all(db, RevalidationJob.id),
            "status": _count_by_field(db, RevalidationJob.status),
            "job_type": _count_by_field(db, RevalidationJob.job_type),
            "overdue_queued": int(
                db.scalar(
                    select(func.count(RevalidationJob.id)).where(
                        RevalidationJob.status == "queued",
                        RevalidationJob.scheduled_at < reference_now,
                    )
                )
                or 0
            ),
            "failed_last_24h": int(
                db.scalar(
                    select(func.count(RevalidationJob.id)).where(
                        RevalidationJob.status == "failed",
                        RevalidationJob.finished_at.is_not(None),
                        RevalidationJob.finished_at >= recent_from,
                    )
                )
                or 0
            ),
        },
    }


def _count_all(db: Session, column) -> int:
    return int(db.scalar(select(func.count(column))) or 0)


def _count_by_field(db: Session, column) -> dict[str, int]:
    rows = db.execute(
        select(column, func.count())
        .group_by(column)
        .order_by(func.count().desc(), column.asc())
    ).all()
    return {
        str(key if key is not None else "null"): int(value)
        for key, value in rows
    }


def _top_popular_routes(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        select(QuickSearchPopularityCounter)
        .order_by(QuickSearchPopularityCounter.search_count.desc(), QuickSearchPopularityCounter.last_searched_at.desc())
        .limit(10)
    ).scalars()
    return [
        {
            "route": f"{row.origin_iata}-{row.destination_iata}",
            "origin_iata": row.origin_iata,
            "destination_iata": row.destination_iata,
            "travel_date": row.travel_date.isoformat(),
            "currency": row.currency,
            "search_count": int(row.search_count),
            "last_searched_at": row.last_searched_at.isoformat(),
        }
        for row in rows
    ]
