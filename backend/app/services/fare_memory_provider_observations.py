from __future__ import annotations

import datetime as dt
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import ProviderFlight
from app.infrastructure.db.models import FlightOfferCacheEntry, FlightPriceObservation
from app.services.fare_memory import build_offer_fingerprint
from app.services.fare_memory_flight_instances import build_flight_instance_fingerprint, derive_carrier_code
from app.services.fare_memory_observation_dedupe import ObservationCandidate, is_recent_duplicate_observation
from app.services.flight_number_enrichment import normalize_explicit_flight_number


ProviderFlightRow = tuple[str, str, dt.date, ProviderFlight]


@dataclass(frozen=True, slots=True)
class ObservationPersistenceContext:
    search_cache_entry_id: str | None
    observed_at: dt.datetime
    expires_at: dt.datetime | None
    freshness_status: str
    confidence_score: float | None
    validation_status: str


class ProviderOfferPayload(TypedDict):
    provider: str
    carrier: str | None
    carrier_code: str | None
    flight_number: str | None
    origin_airport: str
    destination_airport: str
    departure_at: dt.datetime
    arrival_at: dt.datetime | None
    departure_time_local: str | None
    arrival_time_local: str | None
    duration_minutes: int | None
    stops_count: int
    source_kind: str


def persist_provider_flight_observations(
    db: Session,
    *,
    provider_flights: Sequence[ProviderFlightRow],
    context: ObservationPersistenceContext,
) -> dict[str, int]:
    created_offers = 0
    created_observations = 0
    skipped_incomplete = 0
    skipped_duplicate_offers = 0
    skipped_recent_duplicates = 0
    seen_offer_fingerprints: set[str] = set()

    for row in provider_flights:
        offer_payload = _build_provider_offer_payload(row)
        if offer_payload is None:
            skipped_incomplete += 1
            continue

        offer_fingerprint = build_offer_fingerprint(offer_payload, source_kind="provider")
        flight_instance_fingerprint = build_flight_instance_fingerprint(offer_payload)
        if offer_fingerprint in seen_offer_fingerprints:
            skipped_duplicate_offers += 1
            continue
        seen_offer_fingerprints.add(offer_fingerprint)

        offer = db.scalar(
            select(FlightOfferCacheEntry)
            .where(FlightOfferCacheEntry.offer_fingerprint == offer_fingerprint)
            .limit(1)
        )
        if offer is None:
            offer = FlightOfferCacheEntry(
                offer_fingerprint=offer_fingerprint,
                flight_instance_fingerprint=flight_instance_fingerprint,
                provider=offer_payload["provider"],
                carrier=offer_payload["carrier"],
                carrier_code=offer_payload["carrier_code"],
                flight_number=offer_payload["flight_number"],
                origin_airport=offer_payload["origin_airport"],
                destination_airport=offer_payload["destination_airport"],
                departure_at=offer_payload["departure_at"],
                arrival_at=offer_payload["arrival_at"],
                departure_time_local=offer_payload["departure_time_local"],
                arrival_time_local=offer_payload["arrival_time_local"],
                duration_minutes=offer_payload["duration_minutes"],
                stops_count=offer_payload["stops_count"],
                source_kind=offer_payload["source_kind"],
            )
            db.add(offer)
            db.flush()
            created_offers += 1

        previous_observation = db.scalar(
            select(FlightPriceObservation)
            .where(FlightPriceObservation.offer_id == offer.id)
            .order_by(FlightPriceObservation.observed_at.desc(), FlightPriceObservation.id.desc())
            .limit(1)
        )
        price_amount = float(row[3].price)
        currency = str(row[3].currency or "EUR").strip().upper()
        candidate = ObservationCandidate(
            provider=offer_payload["provider"],
            price_amount=price_amount,
            currency=currency,
            observed_at=context.observed_at,
        )
        if is_recent_duplicate_observation(previous_observation, candidate):
            skipped_recent_duplicates += 1
            continue

        price_changed_since_last_seen = False
        delta_abs: float | None = None
        delta_pct: float | None = None

        if previous_observation is not None and previous_observation.price_amount is not None:
            previous_price = float(previous_observation.price_amount)
            delta_abs = round(price_amount - previous_price, 2)
            price_changed_since_last_seen = abs(delta_abs) > 0.0001
            if previous_price != 0:
                delta_pct = round(delta_abs / previous_price, 4)

        db.add(
            FlightPriceObservation(
                offer_id=offer.id,
                search_cache_entry_id=context.search_cache_entry_id,
                provider=offer_payload["provider"],
                price_amount=price_amount,
                currency=currency,
                observed_at=context.observed_at,
                expires_at=context.expires_at,
                freshness_status=context.freshness_status,
                confidence_score=context.confidence_score,
                validation_status=context.validation_status,
                price_changed_since_last_seen=price_changed_since_last_seen,
                delta_abs=delta_abs,
                delta_pct=delta_pct,
            )
        )
        created_observations += 1

    if created_offers or created_observations:
        db.commit()

    return {
        "offers_created": created_offers,
        "observations_created": created_observations,
        "skipped_incomplete": skipped_incomplete,
        "skipped_duplicate_offers": skipped_duplicate_offers,
        "skipped_recent_duplicates": skipped_recent_duplicates,
    }


def _build_provider_offer_payload(row: ProviderFlightRow) -> ProviderOfferPayload | None:
    origin, destination, travel_date, flight = row
    origin_code = origin.strip().upper()
    destination_code = destination.strip().upper()
    provider = str(flight.source or "").strip().lower()
    price_amount = float(flight.price)

    if len(origin_code) != 3 or len(destination_code) != 3:
        return None
    if not provider or not math.isfinite(price_amount):
        return None

    carrier_code = flight.carrier_code or derive_carrier_code(provider)
    return {
        "provider": provider,
        "carrier": None,
        "carrier_code": carrier_code,
        "flight_number": normalize_explicit_flight_number(
            flight.flight_number,
            carrier_code=carrier_code,
        ),
        "origin_airport": origin_code,
        "destination_airport": destination_code,
        "departure_at": _departure_datetime(travel_date, flight.departure_time_local),
        "arrival_at": None,
        "departure_time_local": (flight.departure_time_local or "").strip() or None,
        "arrival_time_local": None,
        "duration_minutes": None,
        "stops_count": 0,
        "source_kind": "provider",
    }


def _departure_datetime(travel_date: dt.date, departure_time_local: str | None) -> dt.datetime:
    """Build a departure datetime from date + HH:MM string.

    Mirrors fare_memory._departure_datetime_for_ranked_result — kept separate
    because this module receives raw (date, time) tuples rather than RankedResult
    objects, and the overhead of an adapter class outweighs 10 lines of duplication.

    IMPORTANT: if the logic in either function changes, both must be updated
    in sync to avoid behavioral divergence.
    """
    value = (departure_time_local or "").strip()
    if value:
        parts = value.split(":")
        if len(parts) >= 2:
            try:
                hour = int(parts[0])
                minute = int(parts[1])
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return dt.datetime.combine(travel_date, dt.time(hour=hour, minute=minute))
            except ValueError:
                return dt.datetime.combine(travel_date, dt.time.min)
    return dt.datetime.combine(travel_date, dt.time.min)
