from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightWatch, PriceSnapshot


@dataclass(frozen=True, slots=True)
class RouteFreshnessEvaluation:
    state: str
    oldest_snapshot_age_seconds: int | None

    @property
    def needs_refresh(self) -> bool:
        return self.state in {"missing_snapshot", "snapshot_expired"}


def latest_snapshot_by_watch_ids(db: Session, watch_ids: list[str]) -> dict[str, PriceSnapshot]:
    if not watch_ids:
        return {}
    rows = db.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.watch_id.in_(watch_ids))
        .order_by(
            PriceSnapshot.watch_id.asc(),
            PriceSnapshot.captured_at_utc.desc(),
            PriceSnapshot.id.desc(),
        )
    ).all()
    latest_by_watch: dict[str, PriceSnapshot] = {}
    for snapshot in rows:
        latest_by_watch.setdefault(snapshot.watch_id, snapshot)
    return latest_by_watch


def evaluate_route_freshness(
    *,
    watches: list[FlightWatch],
    latest_snapshot_by_watch: dict[str, PriceSnapshot],
    now: datetime,
    max_age_seconds: int,
) -> RouteFreshnessEvaluation:
    if not watches:
        return RouteFreshnessEvaluation(state="no_active_watches", oldest_snapshot_age_seconds=None)

    oldest_snapshot_age_seconds = 0
    for watch in watches:
        latest_snapshot = latest_snapshot_by_watch.get(watch.id)
        if latest_snapshot is None:
            return RouteFreshnessEvaluation(state="missing_snapshot", oldest_snapshot_age_seconds=None)
        snapshot_age_seconds = max(0, int((now - latest_snapshot.captured_at_utc).total_seconds()))
        oldest_snapshot_age_seconds = max(oldest_snapshot_age_seconds, snapshot_age_seconds)
        if snapshot_age_seconds >= max_age_seconds:
            return RouteFreshnessEvaluation(
                state="snapshot_expired",
                oldest_snapshot_age_seconds=oldest_snapshot_age_seconds,
            )

    return RouteFreshnessEvaluation(
        state="fresh",
        oldest_snapshot_age_seconds=oldest_snapshot_age_seconds,
    )
