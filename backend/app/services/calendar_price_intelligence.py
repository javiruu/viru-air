import datetime as dt
import hashlib
import json
import statistics
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import CalendarPriceObservation


CalendarBucket = Literal["low", "mid", "high"]
CalendarAggregationMode = Literal["min", "median", "fixed_route"]
CalendarLeg = Literal["outbound", "return"]

_CURRENCY_TO_EUR = {
    "EUR": 1.0,
    "USD": 0.93,
    "GBP": 1.17,
}
_MINIMUM_REFERENCE_SAMPLE = 5
_CONTEXTUAL_BAND_RATIO = 0.15


@dataclass(frozen=True, slots=True)
class CalendarComparableObservation:
    price: float
    observed_at: dt.datetime
    travel_date: dt.date | None = None


@dataclass(frozen=True, slots=True)
class CalendarPriceClassification:
    bucket: CalendarBucket | None
    reason: str | None
    reference_median: float | None
    reference_sample_size: int


@dataclass(frozen=True, slots=True)
class CalendarStoredPrice:
    price: float
    observed_at: dt.datetime
    expires_at: dt.datetime | None
    freshness_status: str
    coverage_status: str


def build_calendar_query_fingerprint(
    *,
    origin_scope: tuple[str, ...],
    destination_scope: tuple[str, ...],
    travel_date: dt.date,
    leg: CalendarLeg,
    adults: int,
    currency: str,
    provider_set: tuple[str, ...],
    aggregation_mode: CalendarAggregationMode,
    cabin: str = "economy",
) -> str:
    payload = {
        "adults": adults,
        "aggregation_mode": aggregation_mode,
        "cabin": cabin.strip().lower(),
        "currency": currency.strip().upper(),
        "destination_scope": sorted(code.strip().upper() for code in destination_scope),
        "leg": leg,
        "origin_scope": sorted(code.strip().upper() for code in origin_scope),
        "provider_set": sorted(provider.strip().lower() for provider in provider_set),
        "travel_date": travel_date.isoformat(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_calendar_reference_fingerprint(
    *,
    origin_scope: tuple[str, ...],
    destination_scope: tuple[str, ...],
    leg: CalendarLeg,
    adults: int,
    currency: str,
    provider_set: tuple[str, ...],
    aggregation_mode: CalendarAggregationMode,
    cabin: str = "economy",
) -> str:
    payload = {
        "adults": adults,
        "aggregation_mode": aggregation_mode,
        "cabin": cabin.strip().lower(),
        "currency": currency.strip().upper(),
        "destination_scope": sorted(code.strip().upper() for code in destination_scope),
        "leg": leg,
        "origin_scope": sorted(code.strip().upper() for code in origin_scope),
        "provider_set": sorted(provider.strip().lower() for provider in provider_set),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def convert_calendar_price(amount: float, from_currency: str, to_currency: str) -> float | None:
    source_rate = _CURRENCY_TO_EUR.get(from_currency.strip().upper())
    target_rate = _CURRENCY_TO_EUR.get(to_currency.strip().upper())
    if source_rate is None or target_rate is None:
        return None
    return round(float(amount) * source_rate / target_rate, 2)


def classify_contextual_price(
    price: float,
    observations: list[CalendarComparableObservation],
) -> CalendarPriceClassification:
    values = sorted(item.price for item in observations if item.price > 0)
    sample_size = len(values)
    if sample_size < _MINIMUM_REFERENCE_SAMPLE:
        return CalendarPriceClassification(
            bucket=None,
            reason="insufficient_reference",
            reference_median=None,
            reference_sample_size=sample_size,
        )
    median = float(statistics.median(values))
    low_limit = median * (1 - _CONTEXTUAL_BAND_RATIO)
    high_limit = median * (1 + _CONTEXTUAL_BAND_RATIO)
    if price < low_limit:
        bucket: CalendarBucket = "low"
    elif price > high_limit:
        bucket = "high"
    else:
        bucket = "mid"
    return CalendarPriceClassification(
        bucket=bucket,
        reason=None,
        reference_median=round(median, 2),
        reference_sample_size=sample_size,
    )


def load_fresh_calendar_reference(
    db: Session,
    *,
    reference_fingerprint: str,
    now: dt.datetime,
) -> list[CalendarComparableObservation]:
    cutoff = now - dt.timedelta(days=30)
    rows = db.scalars(
        select(CalendarPriceObservation)
        .where(
            CalendarPriceObservation.reference_fingerprint == reference_fingerprint,
            CalendarPriceObservation.validation_status.in_(("observed", "revalidated")),
            CalendarPriceObservation.freshness_status == "fresh",
            CalendarPriceObservation.coverage_status == "available",
            CalendarPriceObservation.observed_at >= cutoff,
        )
        .order_by(CalendarPriceObservation.observed_at.desc())
        .limit(500)
    ).all()
    latest_by_day: dict[dt.date, CalendarComparableObservation] = {}
    for row in rows:
        if row.travel_date in latest_by_day:
            continue
        latest_by_day[row.travel_date] = CalendarComparableObservation(
            price=float(row.normalized_price_amount),
            observed_at=row.observed_at,
            travel_date=row.travel_date,
        )
    return list(latest_by_day.values())


def load_latest_calendar_days(
    db: Session,
    *,
    query_fingerprints: dict[dt.date, str],
) -> dict[dt.date, CalendarStoredPrice]:
    if not query_fingerprints:
        return {}
    rows = db.scalars(
        select(CalendarPriceObservation)
        .where(CalendarPriceObservation.query_fingerprint.in_(tuple(query_fingerprints.values())))
        .order_by(CalendarPriceObservation.observed_at.desc())
        .limit(max(100, len(query_fingerprints) * 8))
    ).all()
    fingerprint_to_day = {fingerprint: day for day, fingerprint in query_fingerprints.items()}
    latest_by_day: dict[dt.date, CalendarStoredPrice] = {}
    for row in rows:
        day = fingerprint_to_day.get(row.query_fingerprint)
        if day is None or day in latest_by_day:
            continue
        latest_by_day[day] = CalendarStoredPrice(
            price=float(row.normalized_price_amount),
            observed_at=row.observed_at,
            expires_at=row.expires_at,
            freshness_status=row.freshness_status,
            coverage_status=row.coverage_status,
        )
    return latest_by_day


def record_calendar_prices(
    db: Session,
    *,
    query_fingerprints: dict[dt.date, str],
    reference_fingerprint: str,
    route_signature: str,
    prices_by_day: dict[dt.date, float],
    coverage_status_by_day: dict[dt.date, str],
    leg: CalendarLeg,
    adults: int,
    cabin: str,
    currency: str,
    aggregation_mode: CalendarAggregationMode,
    provider: str,
    observed_at: dt.datetime,
    expires_at: dt.datetime,
) -> None:
    db.execute(
        delete(CalendarPriceObservation).where(
            CalendarPriceObservation.expires_at < observed_at - dt.timedelta(days=29)
        )
    )
    observations = [
        CalendarPriceObservation(
            query_fingerprint=query_fingerprints[day],
            reference_fingerprint=reference_fingerprint,
            route_signature=route_signature,
            travel_date=day,
            leg=leg,
            adults=adults,
            cabin=cabin,
            aggregation_mode=aggregation_mode,
            currency=currency,
            provider=provider,
            normalized_price_amount=price,
            observed_at=observed_at,
            expires_at=expires_at,
            freshness_status="fresh",
            coverage_status=coverage_status_by_day.get(day, "partial"),
            validation_status="observed",
        )
        for day, price in prices_by_day.items()
        if day in query_fingerprints
    ]
    if not observations:
        return
    db.add_all(observations)
    db.commit()
