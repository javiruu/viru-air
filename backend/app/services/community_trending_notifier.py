"""Persist daily community trending snapshots for the notification inbox."""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import date as Date, datetime, timedelta
from math import ceil

from sqlalchemy.orm import Session

from app.core.time import as_utc_naive, utc_now_naive
from app.infrastructure.db.models import (
    CommunityTrendingSnapshot,
    CommunityTrendingSnapshotRoute,
)
from app.services.community_route_intelligence import TRENDING_SHARE, _popularity_by_route

logger = logging.getLogger("app.services.community_trending_notifier")

TRENDING_SNAPSHOT_TTL_SECONDS = 3600
_COMMUNITY_TRENDING_SOURCE_RE = re.compile(
    r"^ct-(?P<date>\d{8})-(?P<origin>[A-Z]{3})-(?P<destination>[A-Z]{3})$"
)


def build_community_trending_source_id(
    reporting_date: Date,
    origin_iata: str,
    destination_iata: str,
) -> str:
    """Build the stable inbox source ID for one reporting day and route."""
    origin = origin_iata.strip().upper()
    destination = destination_iata.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", origin) or not re.fullmatch(r"[A-Z]{3}", destination):
        raise ValueError("invalid_community_trending_route")
    return f"ct-{reporting_date:%Y%m%d}-{origin}-{destination}"


def parse_community_trending_source_id(
    source_id: str,
) -> tuple[Date, str, str] | None:
    """Parse a current stable source ID; legacy user-scoped IDs are rejected."""
    match = _COMMUNITY_TRENDING_SOURCE_RE.fullmatch(source_id)
    if match is None:
        return None
    try:
        reporting_date = datetime.strptime(match.group("date"), "%Y%m%d").date()
    except ValueError:
        return None
    return reporting_date, match.group("origin"), match.group("destination")
def notify_trending_routes(
    db: Session,
    *,
    today: Date | None = None,
    now: datetime | None = None,
) -> int:
    """Persist one complete published snapshot.

    ``today`` controls the logical seven-day popularity window. ``now`` is optional
    for deterministic tests and is normalized to naive UTC for persistence, matching
    the database convention used throughout the backend. The return value is the
    number of routes persisted, not the number of user-specific inbox signals.
    """
    started = time.perf_counter()
    current_date = today or Date.today()
    calculated_at = as_utc_naive(now) if now is not None else utc_now_naive()

    try:
        popularity = _popularity_by_route(db, today=current_date)
        ranked_routes = sorted(
            popularity.items(),
            key=lambda item: (-int(item[1]), item[0][0], item[0][1]),
        )
        trending_count = ceil(len(ranked_routes) * TRENDING_SHARE)
        trending_routes = ranked_routes[:trending_count]
        snapshot = CommunityTrendingSnapshot(
            reporting_date=current_date,
            window_start_date=current_date - timedelta(days=6),
            window_end_date=current_date,
            calculated_at_utc=calculated_at,
            expires_at_utc=calculated_at + timedelta(seconds=TRENDING_SNAPSHOT_TTL_SECONDS),
            status="building",
            route_count=len(trending_routes),
        )
        snapshot.routes = [
            CommunityTrendingSnapshotRoute(
                origin_iata=origin_iata,
                destination_iata=destination_iata,
                rank=rank,
                search_count=int(search_count),
                created_at=calculated_at,
            )
            for rank, ((origin_iata, destination_iata), search_count) in enumerate(
                trending_routes,
                start=1,
            )
        ]
        snapshot.published_at_utc = calculated_at
        snapshot.status = "published"
        db.add(snapshot)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            json.dumps(
                {
                    "event": "community_trending_snapshot_failed",
                    "reporting_date": current_date.isoformat(),
                    "window_start_date": (current_date - timedelta(days=6)).isoformat(),
                    "window_end_date": current_date.isoformat(),
                },
                ensure_ascii=False,
            )
        )
        raise

    duration_ms = round((time.perf_counter() - started) * 1000)
    logger.info(
        json.dumps(
            {
                "event": "community_trending_snapshot_published",
                "reporting_date": current_date.isoformat(),
                "window_start_date": (current_date - timedelta(days=6)).isoformat(),
                "window_end_date": current_date.isoformat(),
                "candidate_route_count": len(ranked_routes),
                "trending_route_count": len(trending_routes),
                "snapshot_id": snapshot.id,
                "snapshot_status": snapshot.status,
                "routes_persisted": len(snapshot.routes),
                "duration_ms": duration_ms,
            },
            ensure_ascii=False,
        )
    )
    return len(trending_routes)
