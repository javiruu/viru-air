from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import ProviderFlight
from app.infrastructure.db.models import FlightWatch, PriceSnapshot


@dataclass(frozen=True)
class CanonicalPriceSnapshot:
    watch_id: str
    captured_at_utc: datetime
    raw_price: float
    raw_currency: str
    departure_time_local: str | None
    provider: str
    is_stale: bool


def select_canonical_refresh_flight(flights: list[ProviderFlight]) -> ProviderFlight | None:
    if not flights:
        return None
    return min(
        flights,
        key=lambda flight: (
            float(flight.price),
            flight.departure_time_local or "99:99",
            flight.source,
        ),
    )


def canonicalize_snapshot_rows(rows: Iterable[PriceSnapshot]) -> list[CanonicalPriceSnapshot]:
    canonical_by_refresh: dict[tuple[str, datetime], CanonicalPriceSnapshot] = {}
    for row in rows:
        refresh_bucket = row.captured_at_utc.replace(microsecond=0)
        key = (row.watch_id, refresh_bucket)
        candidate = CanonicalPriceSnapshot(
            watch_id=row.watch_id,
            captured_at_utc=refresh_bucket,
            raw_price=float(row.raw_price),
            raw_currency=row.raw_currency,
            departure_time_local=row.departure_time_local,
            provider=row.provider,
            is_stale=row.is_stale,
        )
        current = canonical_by_refresh.get(key)
        if current is None or _snapshot_sort_key(candidate) < _snapshot_sort_key(current):
            canonical_by_refresh[key] = candidate
    return list(canonical_by_refresh.values())


def persist_changed_snapshots_for_watches(
    db: Session,
    *,
    watches: list[FlightWatch],
    canonical_flight: ProviderFlight,
    captured_at_utc: datetime,
) -> int:
    latest_by_watch = _latest_snapshot_by_watch_ids(db, [watch.id for watch in watches])
    snapshots = [
        PriceSnapshot(
            watch_id=watch.id,
            captured_at_utc=captured_at_utc,
            departure_time_local=canonical_flight.departure_time_local,
            raw_price=canonical_flight.price,
            raw_currency=canonical_flight.currency,
            provider=canonical_flight.source,
        )
        for watch in watches
        if _should_persist_snapshot(latest_by_watch.get(watch.id), canonical_flight)
    ]
    if not snapshots:
        return 0
    db.add_all(snapshots)
    db.commit()
    return len(snapshots)


def _latest_snapshot_by_watch_ids(db: Session, watch_ids: list[str]) -> dict[str, PriceSnapshot]:
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


def _should_persist_snapshot(
    latest_snapshot: PriceSnapshot | None,
    canonical_flight: ProviderFlight,
) -> bool:
    if latest_snapshot is None or latest_snapshot.is_stale:
        return True
    return (
        float(latest_snapshot.raw_price) != float(canonical_flight.price)
        or latest_snapshot.raw_currency != canonical_flight.currency
    )


def _snapshot_sort_key(snapshot: CanonicalPriceSnapshot) -> tuple[float, int, str, str]:
    return (
        snapshot.raw_price,
        1 if snapshot.is_stale else 0,
        snapshot.departure_time_local or "99:99",
        snapshot.provider,
    )
