from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.domain.entities import ProviderFlight
from app.infrastructure.db.models import PriceSnapshot


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


def _snapshot_sort_key(snapshot: CanonicalPriceSnapshot) -> tuple[float, int, str, str]:
    return (
        snapshot.raw_price,
        1 if snapshot.is_stale else 0,
        snapshot.departure_time_local or "99:99",
        snapshot.provider,
    )
