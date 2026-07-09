from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import FlightOfferCacheEntry, FlightPriceObservation, FlightWatch, PriceSnapshot


_BACKFILL_PROVIDER = "historical_backfill"


@dataclass(frozen=True, slots=True)
class BackfillObservation:
    observation_id: str
    offer_id: str
    flight_instance_fingerprint: str | None
    observed_at: dt.datetime
    price_amount: float
    currency: str
    provider: str
    departure_time_local: str | None


def find_backfill_observations_for_watch(
    db: Session,
    watch: FlightWatch,
    *,
    limit: int = 50,
    now: dt.datetime | None = None,
) -> list[BackfillObservation]:
    effective_limit = max(0, int(limit))
    if effective_limit == 0:
        return []

    observed_until = now or utc_now_naive()
    travel_day_start = dt.datetime.combine(watch.travel_date_local, dt.time.min)
    travel_day_end = travel_day_start + dt.timedelta(days=1)

    rows = db.execute(
        select(FlightPriceObservation, FlightOfferCacheEntry)
        .join(FlightOfferCacheEntry, FlightPriceObservation.offer_id == FlightOfferCacheEntry.id)
        .where(FlightOfferCacheEntry.origin_airport == watch.origin_iata.upper())
        .where(FlightOfferCacheEntry.destination_airport == watch.destination_iata.upper())
        .where(FlightOfferCacheEntry.departure_at >= travel_day_start)
        .where(FlightOfferCacheEntry.departure_at < travel_day_end)
        .where(FlightOfferCacheEntry.departure_at >= observed_until)
        .where(FlightPriceObservation.observed_at <= observed_until)
        .where(FlightPriceObservation.price_amount.is_not(None))
        .order_by(FlightPriceObservation.observed_at.asc(), FlightPriceObservation.id.asc())
        .limit(effective_limit)
    ).all()

    return [
        BackfillObservation(
            observation_id=observation.id,
            offer_id=offer.id,
            flight_instance_fingerprint=offer.flight_instance_fingerprint,
            observed_at=observation.observed_at,
            price_amount=float(observation.price_amount),
            currency=observation.currency,
            provider=observation.provider,
            departure_time_local=offer.departure_time_local,
        )
        for observation, offer in rows
    ]


def persist_backfill_snapshots_for_watch(
    db: Session,
    watch: FlightWatch,
    observations: Sequence[BackfillObservation],
) -> int:
    if not observations:
        return 0

    existing_keys = _existing_backfill_snapshot_keys(db, watch.id)
    snapshots: list[PriceSnapshot] = []
    for observation in observations:
        captured_at_utc = observation.observed_at.replace(microsecond=0)
        key = _snapshot_key(
            captured_at_utc=captured_at_utc,
            raw_price=observation.price_amount,
            raw_currency=observation.currency,
            departure_time_local=observation.departure_time_local,
        )
        if key in existing_keys:
            continue
        existing_keys.add(key)
        snapshots.append(
            PriceSnapshot(
                watch_id=watch.id,
                captured_at_utc=captured_at_utc,
                departure_time_local=observation.departure_time_local,
                raw_price=observation.price_amount,
                raw_currency=observation.currency,
                provider=_BACKFILL_PROVIDER,
                is_stale=True,
            )
        )

    if not snapshots:
        return 0
    db.add_all(snapshots)
    db.commit()
    return len(snapshots)


def _existing_backfill_snapshot_keys(db: Session, watch_id: str) -> set[tuple[dt.datetime, float, str, str | None]]:
    snapshots = db.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.watch_id == watch_id)
        .where(PriceSnapshot.provider == _BACKFILL_PROVIDER)
    ).all()
    return {
        _snapshot_key(
            captured_at_utc=snapshot.captured_at_utc.replace(microsecond=0),
            raw_price=float(snapshot.raw_price),
            raw_currency=snapshot.raw_currency,
            departure_time_local=snapshot.departure_time_local,
        )
        for snapshot in snapshots
    }


def _snapshot_key(
    *,
    captured_at_utc: dt.datetime,
    raw_price: float,
    raw_currency: str,
    departure_time_local: str | None,
) -> tuple[dt.datetime, float, str, str | None]:
    return (
        captured_at_utc,
        round(float(raw_price), 2),
        raw_currency.strip().upper(),
        departure_time_local,
    )
