"""Community trending notifier — stores lightweight trending route signals in memory
so the inbox can surface them without creating NotificationEvent rows (which require
a non-null alert_rule FK we cannot satisfy for community-level signals)."""

from datetime import date as Date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.vocabulary import WATCH_STATUS_ACTIVE
from app.infrastructure.db.models import FlightWatch
from app.services.community_route_intelligence import _popularity_by_route, TRENDING_SHARE
from math import ceil

SOURCE_COMMUNITY_TRENDING = "community_trending"
TRENDING_CACHE: dict[str, list["TrendingSignal"]] = {}


class TrendingSignal:
    """Lightweight in-memory signal representing a trending route for a user."""

    __slots__ = ("user_id", "origin_iata", "destination_iata", "created_at", "event_id")

    def __init__(
        self,
        user_id: str,
        origin_iata: str,
        destination_iata: str,
        created_at: datetime | None = None,
    ) -> None:
        self.user_id = user_id
        self.origin_iata = origin_iata
        self.destination_iata = destination_iata
        self.created_at = created_at or datetime.now(timezone.utc)
        self.event_id = f"trending:{user_id}:{origin_iata}:{destination_iata}"


def notify_trending_routes(
    db: Session,
    *,
    today: Date | None = None,
) -> int:
    """Compute trending routes and cache them in-memory for the inbox.

    Returns the number of new signals generated.
    """
    current_date = today or Date.today()
    popularity = _popularity_by_route(db, today=current_date)
    if not popularity:
        return 0

    ranked_keys = list(popularity)
    trending_count = ceil(len(ranked_keys) * TRENDING_SHARE)
    trending_keys_set = set(ranked_keys[:trending_count])
    if not trending_keys_set:
        return 0

    # Pre-filter: only fetch watches on trending routes
    trending_origins = {k[0] for k in trending_keys_set}
    trending_destinations = {k[1] for k in trending_keys_set}

    watches = list(
        db.scalars(
            select(FlightWatch).where(
                FlightWatch.status == WATCH_STATUS_ACTIVE,
                FlightWatch.origin_iata.in_(trending_origins),
                FlightWatch.destination_iata.in_(trending_destinations),
            )
        ).all()
    )

    # Build signals for watches whose exact route is trending
    signals: list[TrendingSignal] = []
    seen: set[str] = set()
    for watch in watches:
        route_key = (watch.origin_iata, watch.destination_iata)
        if route_key not in trending_keys_set:
            continue
        key = f"{watch.user_id}:{route_key[0]}:{route_key[1]}"
        if key in seen:
            continue
        seen.add(key)
        signals.append(
            TrendingSignal(
                user_id=watch.user_id,
                origin_iata=route_key[0],
                destination_iata=route_key[1],
            )
        )

    # Replace cache atomically
    by_user: dict[str, list[TrendingSignal]] = {}
    for signal in signals:
        by_user.setdefault(signal.user_id, []).append(signal)
    TRENDING_CACHE.clear()
    TRENDING_CACHE.update(by_user)

    return len(signals)


def get_trending_signals_for_user(user_id: str) -> list[TrendingSignal]:
    """Return trending signals for a user from the in-memory cache."""
    return TRENDING_CACHE.get(user_id, [])
