from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import FlightOfferCacheEntry, FlightPriceObservation


class HistoricalDailyAggregatePayload(TypedDict):
    route: str
    origin_iata: str
    destination_iata: str
    departure_date: str
    currency: str
    observation_count: int
    min_price: float
    max_price: float
    latest_price: float
    latest_observed_at: str
    compaction_candidate: bool


@dataclass(frozen=True, slots=True)
class HistoricalAggregateKey:
    origin_iata: str
    destination_iata: str
    departure_date: dt.date
    currency: str


@dataclass(frozen=True, slots=True)
class HistoricalDailyAggregate:
    origin_iata: str
    destination_iata: str
    departure_date: dt.date
    currency: str
    observation_count: int
    min_price: float
    max_price: float
    latest_price: float
    latest_observed_at: dt.datetime
    compaction_candidate: bool

    @property
    def route(self) -> str:
        return f"{self.origin_iata}-{self.destination_iata}"

    def to_payload(self) -> HistoricalDailyAggregatePayload:
        return {
            "route": self.route,
            "origin_iata": self.origin_iata,
            "destination_iata": self.destination_iata,
            "departure_date": self.departure_date.isoformat(),
            "currency": self.currency,
            "observation_count": self.observation_count,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "latest_price": self.latest_price,
            "latest_observed_at": self.latest_observed_at.isoformat(),
            "compaction_candidate": self.compaction_candidate,
        }


@dataclass(frozen=True, slots=True)
class HistoricalAggregateRow:
    key: HistoricalAggregateKey
    observation_count: int
    min_price: float
    max_price: float
    latest_observed_at: dt.datetime


def build_historical_daily_aggregates(
    db: Session,
    *,
    now: dt.datetime | None = None,
    limit: int = 10,
) -> list[HistoricalDailyAggregate]:
    reference_now = now or utc_now_naive()
    rows = db.execute(
        select(
            FlightOfferCacheEntry.origin_airport,
            FlightOfferCacheEntry.destination_airport,
            func.date(FlightOfferCacheEntry.departure_at),
            FlightPriceObservation.currency,
            func.count(FlightPriceObservation.id),
            func.min(FlightPriceObservation.price_amount),
            func.max(FlightPriceObservation.price_amount),
            func.max(FlightPriceObservation.observed_at),
        )
        .join(FlightOfferCacheEntry, FlightPriceObservation.offer_id == FlightOfferCacheEntry.id)
        .group_by(
            FlightOfferCacheEntry.origin_airport,
            FlightOfferCacheEntry.destination_airport,
            func.date(FlightOfferCacheEntry.departure_at),
            FlightPriceObservation.currency,
        )
        .order_by(func.count(FlightPriceObservation.id).desc(), func.max(FlightPriceObservation.observed_at).desc())
        .limit(max(0, int(limit)))
    ).all()

    return [
        _build_aggregate(
            db,
            HistoricalAggregateRow(
                key=HistoricalAggregateKey(
                    origin_iata=str(origin_iata).upper(),
                    destination_iata=str(destination_iata).upper(),
                    departure_date=dt.date.fromisoformat(str(departure_date)),
                    currency=str(currency or "EUR").upper(),
                ),
                observation_count=int(observation_count),
                min_price=float(min_price),
                max_price=float(max_price),
                latest_observed_at=latest_observed_at,
            ),
            now=reference_now,
        )
        for (
            origin_iata,
            destination_iata,
            departure_date,
            currency,
            observation_count,
            min_price,
            max_price,
            latest_observed_at,
        ) in rows
    ]


def _build_aggregate(
    db: Session,
    row: HistoricalAggregateRow,
    *,
    now: dt.datetime,
) -> HistoricalDailyAggregate:
    latest_price = db.scalar(
        select(FlightPriceObservation.price_amount)
        .join(FlightOfferCacheEntry, FlightPriceObservation.offer_id == FlightOfferCacheEntry.id)
        .where(FlightOfferCacheEntry.origin_airport == row.key.origin_iata)
        .where(FlightOfferCacheEntry.destination_airport == row.key.destination_iata)
        .where(func.date(FlightOfferCacheEntry.departure_at) == row.key.departure_date.isoformat())
        .where(FlightPriceObservation.currency == row.key.currency)
        .where(FlightPriceObservation.observed_at == row.latest_observed_at)
        .order_by(FlightPriceObservation.id.desc())
        .limit(1)
    )
    resolved_latest_price = float(latest_price) if latest_price is not None else row.max_price
    return HistoricalDailyAggregate(
        origin_iata=row.key.origin_iata,
        destination_iata=row.key.destination_iata,
        departure_date=row.key.departure_date,
        currency=row.key.currency,
        observation_count=row.observation_count,
        min_price=row.min_price,
        max_price=row.max_price,
        latest_price=resolved_latest_price,
        latest_observed_at=row.latest_observed_at,
        compaction_candidate=row.key.departure_date < now.date(),
    )
