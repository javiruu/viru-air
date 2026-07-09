from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import FlightOfferCacheEntry, FlightPriceObservation, FlightWatch


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
