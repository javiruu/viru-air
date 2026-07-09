from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Mapping
from typing import Any, TypedDict


_PROVIDER_CARRIER_CODE_BY_PREFIX = {
    "ryanair": "FR",
    "vueling": "VY",
}


class FlightSegmentIdentityPayload(TypedDict):
    carrier_code: str | None
    flight_number: str | None
    origin_airport: str | None
    destination_airport: str | None
    departure_at: str | None
    arrival_at: str | None


class FlightInstanceFingerprintPayload(TypedDict):
    algorithm_version: str
    carrier_code: str | None
    flight_number: str | None
    origin_airport: str | None
    destination_airport: str | None
    departure_at: str | None
    arrival_at: str | None
    departure_time_local: str | None
    arrival_time_local: str | None
    stops_count: int
    segments: list[FlightSegmentIdentityPayload]


def canonicalize_flight_instance_fingerprint_payload(
    offer: Any,
    *,
    algorithm_version: str = "v1",
) -> FlightInstanceFingerprintPayload:
    data = _extract_mapping(offer)
    raw_segments = data.get("segments") or []
    segments: list[FlightSegmentIdentityPayload] = []
    for raw_segment in raw_segments:
        segment = _extract_mapping(raw_segment)
        segments.append(
            {
                "carrier_code": _normalized_upper(segment.get("carrier") or segment.get("carrier_code")),
                "flight_number": _normalized_upper(segment.get("flight_number")),
                "origin_airport": _normalized_upper(segment.get("origin") or segment.get("origin_airport")),
                "destination_airport": _normalized_upper(
                    segment.get("destination") or segment.get("destination_airport")
                ),
                "departure_at": _normalize_datetime_value(segment.get("departure_at")),
                "arrival_at": _normalize_datetime_value(segment.get("arrival_at")),
            }
        )

    stops_count = data.get("stops_count")
    if stops_count is None and segments:
        stops_count = max(0, len(segments) - 1)

    return {
        "algorithm_version": algorithm_version,
        "carrier_code": derive_carrier_code(data.get("provider"), data.get("carrier_code") or data.get("carrier")),
        "flight_number": _normalized_upper(data.get("flight_number")),
        "origin_airport": _normalized_upper(data.get("origin_airport") or data.get("origin")),
        "destination_airport": _normalized_upper(data.get("destination_airport") or data.get("destination")),
        "departure_at": _normalize_datetime_value(data.get("departure_at") or data.get("travel_date")),
        "arrival_at": _normalize_datetime_value(data.get("arrival_at")),
        "departure_time_local": _normalized_text(data.get("departure_time_local")),
        "arrival_time_local": _normalized_text(data.get("arrival_time_local")),
        "stops_count": int(stops_count or 0),
        "segments": segments,
    }


def derive_carrier_code(provider: Any, carrier: Any = None) -> str | None:
    explicit_carrier = _normalized_upper(carrier)
    if explicit_carrier:
        return explicit_carrier

    provider_id = _normalized_text(provider)
    if provider_id is None:
        return None

    normalized_provider = provider_id.lower()
    for provider_prefix, carrier_code in _PROVIDER_CARRIER_CODE_BY_PREFIX.items():
        if normalized_provider == provider_prefix or normalized_provider.startswith(f"{provider_prefix}-"):
            return carrier_code
    return provider_id.upper()


def build_flight_instance_fingerprint(
    offer: Any,
    *,
    algorithm_version: str = "v1",
) -> str:
    payload = canonicalize_flight_instance_fingerprint_payload(
        offer,
        algorithm_version=algorithm_version,
    )
    digest = hashlib.sha256(_stable_json_dumps(payload).encode("utf-8")).hexdigest()
    return f"fsm_flight_{digest[:24]}"


def _extract_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("Expected a mapping or Pydantic model-like object.")


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


def _normalized_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalized_upper(value: Any) -> str | None:
    text = _normalized_text(value)
    return text.upper() if text else None


def _stable_json_dumps(value: FlightInstanceFingerprintPayload) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
