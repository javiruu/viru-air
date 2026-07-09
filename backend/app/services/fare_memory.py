from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightOfferCacheEntry, FlightPriceObservation
from app.services.fare_memory_flight_instances import build_flight_instance_fingerprint, derive_carrier_code
from app.services.quick_search_ranking import RankedResult


FRESHNESS_STATUSES = {
    "fresh",
    "warm",
    "stale",
    "expired",
    "negative_fresh",
    "negative_stale",
    "provider_error_fresh",
    "provider_error_stale",
}

_DEFAULT_FRESHNESS_CONFIDENCE: dict[str, float] = {
    "fresh": 0.95,
    "warm": 0.72,
    "stale": 0.38,
    "expired": 0.12,
    "negative_fresh": 0.7,
    "negative_stale": 0.28,
    "provider_error_fresh": 0.22,
    "provider_error_stale": 0.18,
}

_REVALIDATION_REQUIRED_STATUSES = {
    "warm",
    "stale",
    "expired",
    "negative_stale",
    "provider_error_fresh",
    "provider_error_stale",
}


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _fingerprint(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json_dumps(payload).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:24]}"


def _extract_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("Expected a mapping or Pydantic model-like object.")


def _normalize_iata_list(values: Sequence[str] | None, *, fallback: str | None = None) -> list[str]:
    items = list(values or [])
    if fallback:
        items.append(fallback)
    normalized = {str(item).strip().upper() for item in items if str(item).strip()}
    return sorted(normalized)


def _normalize_string_list(values: Sequence[str] | None) -> list[str]:
    return sorted({str(item).strip().upper() for item in (values or []) if str(item).strip()})


def _normalize_datetime_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        normalized = value.astimezone(dt.UTC) if value.tzinfo else value.replace(tzinfo=dt.UTC)
        return normalized.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if isinstance(value, dt.date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def canonicalize_search_fingerprint_payload(
    canonical_request: Any,
    *,
    currency: str = "EUR",
    provider_set: Sequence[str] | None = None,
    locale: str | None = None,
    locale_affects_data: bool = False,
    algorithm_version: str = "v1",
) -> dict[str, Any]:
    request = _extract_mapping(canonical_request)
    origin = _extract_mapping(request.get("origin") or {})
    destination = _extract_mapping(request.get("destination") or {})
    travel = _extract_mapping(request.get("travel") or {})
    constraints = _extract_mapping(request.get("constraints") or {})
    execution = _extract_mapping(request.get("execution") or {})

    normalized: dict[str, Any] = {
        "algorithm_version": algorithm_version,
        "origin": {
            "seed_pool": _normalize_iata_list(origin.get("seed_iata_list"), fallback=origin.get("seed_iata")),
            "include_nearby": bool(origin.get("include_nearby", False)),
            "radius_km": int(origin.get("radius_km", 150)) if origin.get("include_nearby", False) else None,
            "max_candidates": int(origin.get("max_candidates", 10)),
        },
        "destination": {
            "seed_pool": _normalize_iata_list(destination.get("seed_iata_list"), fallback=destination.get("seed_iata")),
            "include_nearby": bool(destination.get("include_nearby", False)),
            "radius_km": int(destination.get("radius_km", 150)) if destination.get("include_nearby", False) else None,
            "max_candidates": int(destination.get("max_candidates", 10)),
        },
        "travel": {
            "date": _normalize_datetime_value(travel.get("date")),
            "flex_before": int(travel.get("flex_before", 0)),
            "flex_after": int(travel.get("flex_after", 0)),
        },
        "constraints": {
            "departure_window": {
                "after": ((constraints.get("departure_window") or {}).get("after") if isinstance(constraints.get("departure_window"), Mapping) else None),
                "before": ((constraints.get("departure_window") or {}).get("before") if isinstance(constraints.get("departure_window"), Mapping) else None),
            },
            "exclude_origins": _normalize_string_list(constraints.get("exclude_origins")),
            "exclude_destinations": _normalize_string_list(constraints.get("exclude_destinations")),
            "strict_filters": bool(constraints.get("strict_filters", True)),
            "include_stops": bool(constraints.get("include_stops", False)),
            "max_stops": int(constraints.get("max_stops", 0) or 0),
            "soft_filters_weight": round(float(constraints.get("soft_filters_weight", 0.6) or 0.6), 4),
        },
        "execution": {
            "max_pairs": int(execution.get("max_pairs", 48)),
            "max_requests": int(execution.get("max_requests", 480)),
        },
        "currency": str(currency).strip().upper() or "EUR",
        "provider_set": sorted({str(item).strip().lower() for item in (provider_set or ["multi"]) if str(item).strip()}),
    }
    if locale_affects_data and locale:
        normalized["locale"] = str(locale).strip().lower()
    return normalized


def build_search_fingerprint(
    canonical_request: Any,
    *,
    currency: str = "EUR",
    provider_set: Sequence[str] | None = None,
    locale: str | None = None,
    locale_affects_data: bool = False,
    algorithm_version: str = "v1",
) -> str:
    payload = canonicalize_search_fingerprint_payload(
        canonical_request,
        currency=currency,
        provider_set=provider_set,
        locale=locale,
        locale_affects_data=locale_affects_data,
        algorithm_version=algorithm_version,
    )
    return _fingerprint("fsm_search", payload)


def canonicalize_offer_fingerprint_payload(
    offer: Any,
    *,
    source_kind: str = "provider",
    algorithm_version: str = "v1",
) -> dict[str, Any]:
    data = _extract_mapping(offer)
    raw_segments = data.get("segments") or []
    segments = []
    for raw_segment in raw_segments:
        segment = _extract_mapping(raw_segment)
        segments.append(
            {
                "carrier": str(segment.get("carrier", "")).strip().upper() or None,
                "flight_number": str(segment.get("flight_number", "")).strip().upper() or None,
                "origin": str(segment.get("origin", "")).strip().upper() or None,
                "destination": str(segment.get("destination", "")).strip().upper() or None,
                "departure_at": _normalize_datetime_value(segment.get("departure_at")),
                "arrival_at": _normalize_datetime_value(segment.get("arrival_at")),
            }
        )

    provider_ids = sorted(
        {
            str(item).strip()
            for item in (
                data.get("provider_offer_id"),
                data.get("deeplink_signature"),
                data.get("booking_url_hash"),
            )
            if item is not None and str(item).strip()
        }
    )

    stops_count = data.get("stops_count")
    if stops_count is None and segments:
        stops_count = max(0, len(segments) - 1)

    return {
        "algorithm_version": algorithm_version,
        "provider": str(data.get("provider", "")).strip().lower() or None,
        "carrier": str(data.get("carrier", "")).strip().upper() or None,
        "flight_number": str(data.get("flight_number", "")).strip().upper() or None,
        "origin_airport": str(data.get("origin_airport") or data.get("origin") or "").strip().upper() or None,
        "destination_airport": str(data.get("destination_airport") or data.get("destination") or "").strip().upper() or None,
        "departure_at": _normalize_datetime_value(data.get("departure_at") or data.get("travel_date")),
        "arrival_at": _normalize_datetime_value(data.get("arrival_at")),
        "stops_count": int(stops_count or 0),
        "source_kind": str(source_kind or data.get("source_kind") or "provider").strip().lower(),
        "segments": segments,
        "provider_ids": provider_ids,
    }


def build_offer_fingerprint(
    offer: Any,
    *,
    source_kind: str = "provider",
    algorithm_version: str = "v1",
) -> str:
    payload = canonicalize_offer_fingerprint_payload(
        offer,
        source_kind=source_kind,
        algorithm_version=algorithm_version,
    )
    return _fingerprint("fsm_offer", payload)


def _departure_datetime_for_ranked_result(item: RankedResult) -> dt.datetime:
    departure_time_local = (item.flight.departure_time_local or "").strip()
    if departure_time_local:
        parts = departure_time_local.split(":")
        if len(parts) >= 2:
            try:
                hour = int(parts[0])
                minute = int(parts[1])
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return dt.datetime.combine(item.travel_date, dt.time(hour=hour, minute=minute))
            except ValueError:
                pass
    return dt.datetime.combine(item.travel_date, dt.time.min)


def build_ranked_result_offer_payload(item: RankedResult) -> dict[str, Any]:
    departure_time_local = (item.flight.departure_time_local or "").strip() or None
    return {
        "provider": item.flight.source,
        "carrier": None,
        "carrier_code": derive_carrier_code(item.flight.source),
        "flight_number": None,
        "origin_airport": item.origin,
        "destination_airport": item.destination,
        "departure_at": _departure_datetime_for_ranked_result(item),
        "arrival_at": None,
        "departure_time_local": departure_time_local,
        "arrival_time_local": None,
        "duration_minutes": None,
        "stops_count": 0,
        "source_kind": "provider",
    }


def persist_ranked_result_observations(
    db: Session,
    *,
    ranked_results: Sequence[RankedResult],
    search_cache_entry_id: str | None,
    observed_at: dt.datetime,
    expires_at: dt.datetime | None,
    freshness_status: str,
    confidence_score: float | None,
    validation_status: str,
) -> dict[str, int]:
    created_offers = 0
    created_observations = 0

    for item in ranked_results:
        offer_payload = build_ranked_result_offer_payload(item)
        offer_fingerprint = build_offer_fingerprint(offer_payload, source_kind="provider")
        flight_instance_fingerprint = build_flight_instance_fingerprint(offer_payload)
        offer = db.scalar(
            select(FlightOfferCacheEntry)
            .where(FlightOfferCacheEntry.offer_fingerprint == offer_fingerprint)
            .limit(1)
        )
        if offer is None:
            offer = FlightOfferCacheEntry(
                offer_fingerprint=offer_fingerprint,
                flight_instance_fingerprint=flight_instance_fingerprint,
                provider=str(offer_payload["provider"]).strip().lower(),
                carrier=offer_payload["carrier"],
                carrier_code=offer_payload["carrier_code"],
                flight_number=offer_payload["flight_number"],
                origin_airport=str(offer_payload["origin_airport"]).strip().upper(),
                destination_airport=str(offer_payload["destination_airport"]).strip().upper(),
                departure_at=offer_payload["departure_at"],
                arrival_at=offer_payload["arrival_at"],
                departure_time_local=offer_payload["departure_time_local"],
                arrival_time_local=offer_payload["arrival_time_local"],
                duration_minutes=offer_payload["duration_minutes"],
                stops_count=int(offer_payload["stops_count"] or 0),
                source_kind=str(offer_payload["source_kind"]).strip().lower() or "provider",
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

        price_amount = float(item.flight.price)
        price_changed_since_last_seen = False
        delta_abs: float | None = None
        delta_pct: float | None = None

        if previous_observation is not None and previous_observation.price_amount is not None:
            previous_price = float(previous_observation.price_amount)
            delta_abs = round(price_amount - previous_price, 2)
            price_changed_since_last_seen = abs(delta_abs) > 0.0001
            if previous_price != 0:
                delta_pct = round(delta_abs / previous_price, 4)

        observation = FlightPriceObservation(
            offer_id=offer.id,
            search_cache_entry_id=search_cache_entry_id,
            provider=str(item.flight.source).strip().lower(),
            price_amount=price_amount,
            currency=str(item.flight.currency or "EUR").strip().upper(),
            observed_at=observed_at,
            expires_at=expires_at,
            freshness_status=freshness_status,
            confidence_score=confidence_score,
            validation_status=validation_status,
            price_changed_since_last_seen=price_changed_since_last_seen,
            delta_abs=delta_abs,
            delta_pct=delta_pct,
        )
        db.add(observation)
        created_observations += 1

    if created_offers or created_observations:
        db.commit()

    return {
        "offers_created": created_offers,
        "observations_created": created_observations,
    }


def build_freshness_payload(
    *,
    status: str,
    observed_at: dt.datetime,
    expires_at: dt.datetime | None,
    source: str,
    now: dt.datetime | None = None,
    confidence_score: float | None = None,
    validation_status: str = "observed",
) -> dict[str, Any]:
    if status not in FRESHNESS_STATUSES:
        raise ValueError(f"Unsupported freshness status: {status}")

    reference_now = now or dt.datetime.now(dt.UTC).replace(tzinfo=None)
    observed = observed_at.astimezone(dt.UTC).replace(tzinfo=None) if observed_at.tzinfo else observed_at
    expires = (
        expires_at.astimezone(dt.UTC).replace(tzinfo=None)
        if expires_at is not None and expires_at.tzinfo
        else expires_at
    )
    age_seconds = max(0, int((reference_now - observed).total_seconds()))
    resolved_confidence = confidence_score
    if resolved_confidence is None:
        resolved_confidence = _DEFAULT_FRESHNESS_CONFIDENCE[status]

    return {
        "status": status,
        "observed_at": _normalize_datetime_value(observed),
        "expires_at": _normalize_datetime_value(expires),
        "age_seconds": age_seconds,
        "confidence_score": round(float(resolved_confidence), 2),
        "source": str(source).strip(),
        "requires_revalidation": status in _REVALIDATION_REQUIRED_STATUSES,
        "validation_status": validation_status,
    }
