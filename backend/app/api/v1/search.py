import datetime as dt
import hashlib
import json
import logging
import math
import os
import time
import uuid
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.core.errors import ApiError, message_for_code
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.api.v1.airports import _validate_iata
from app.infrastructure.airports_catalog import get_airport, resolve_seed_airport
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider
from app.services.quick_search_dedupe import dedupe_ranked_results
from app.services.quick_search_execution import build_execution_plan, execute_plan
from app.services.quick_search_expansion import SideExpansionResult, SideExpansionSummary, expand_search_sides
from app.services.quick_search_planner import build_pair_plan
from app.services.quick_search_ranking import rank_quick_search_results

router = APIRouter()
provider = RyanairPublicProvider()
logger = logging.getLogger(__name__)
SEED_POOL_CAP = 8
QUICK_SEARCH_MAX_PAIRS_CAP = 400
QUICK_SEARCH_MAX_REQUESTS_CAP = 3000

_WARNING_CODE_ALIASES: dict[str, str] = {
    "provider_timeout_parcial": "provider_timeout_partial",
    "ryanair_unavailable_parcial": "ryanair_unavailable_partial",
}


def _normalize_warning_code(code: str) -> str:
    return _WARNING_CODE_ALIASES.get(code, code)


def _normalize_warning_codes(codes: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for raw_code in codes:
        code = _normalize_warning_code(raw_code)
        if code in seen:
            continue
        seen.add(code)
        deduped.append(code)
    return deduped


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _build_query_signature(
    *,
    origin_seed_pool: list[str],
    destination_seed_pool: list[str],
    travel_date: dt.date,
    flex_before: int,
    flex_after: int,
    include_nearby_origins: bool,
    include_nearby_destinations: bool,
    radius_km_origin: int,
    radius_km_destination: int,
    depart_after: str | None,
    depart_before: str | None,
    strict_filters: bool,
    include_stops: bool,
    max_stops: int,
    soft_filters_weight: float,
    winning_step: str,
) -> str:
    payload = {
        "origin_seed_pool": origin_seed_pool,
        "destination_seed_pool": destination_seed_pool,
        "travel_date": str(travel_date),
        "flex_before": flex_before,
        "flex_after": flex_after,
        "include_nearby_origins": include_nearby_origins,
        "include_nearby_destinations": include_nearby_destinations,
        "radius_km_origin": radius_km_origin,
        "radius_km_destination": radius_km_destination,
        "depart_after": depart_after,
        "depart_before": depart_before,
        "strict_filters": strict_filters,
        "include_stops": include_stops,
        "max_stops": max_stops,
        "soft_filters_weight": round(float(soft_filters_weight), 4),
        "winning_step": winning_step,
    }
    digest = hashlib.sha256(_stable_json_dumps(payload).encode("utf-8")).hexdigest()
    return f"qsig_{digest[:24]}"


def _error_reason_from_http_exception(exc: HTTPException) -> str:
    if isinstance(exc.detail, str):
        return exc.detail
    if isinstance(exc.detail, list):
        return "validation_error"
    if isinstance(exc.detail, dict) and isinstance(exc.detail.get("code"), str):
        return str(exc.detail["code"])
    return "request_failed"


def _estimate_duration_minutes(origin: str, destination: str) -> int | None:
    origin_airport = get_airport(origin)
    destination_airport = get_airport(destination)
    if not origin_airport or not destination_airport:
        return None
    radius = 6371.0
    phi1 = math.radians(origin_airport.latitude)
    phi2 = math.radians(destination_airport.latitude)
    d_phi = math.radians(destination_airport.latitude - origin_airport.latitude)
    d_lambda = math.radians(destination_airport.longitude - origin_airport.longitude)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    distance_km = radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    flight_hours = distance_km / 780.0 + 0.5
    return max(45, int(flight_hours * 60))


def _risk_label_from_pair_category(category: str | None) -> str:
    if category == "seed-seed":
        return "low"
    if category in {"seed-nearby", "nearby-seed"}:
        return "medium"
    return "high"


class QuickSearchPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    origin_iata: str | list[str] | None = None
    destination_iata: str | list[str] | None = None
    travel_date: dt.date | None = None
    date: dt.date | None = None
    radius_km: int | None = None
    include_stops: bool | None = None
    include_nearby_origin: bool | None = None
    include_nearby_origins: bool | None = None
    include_nearby_destination: bool | None = None
    include_nearby_destinations: bool | None = None
    depart_after: str | None = None
    depart_before: str | None = None
    departure_from: str | None = None
    departure_to: str | None = None
    max_stops: int | None = None
    duration_max_min: int | None = None
    duration_max: int | None = None
    risk_allowed: str | None = None
    risk_filter: str | None = None
    exclude_origins: str | list[str] | None = None
    exclude_destinations: str | list[str] | None = None
    strict_filters: bool | None = None
    strict_mode: bool | None = None
    soft_filters_weight: float | None = None
    flex_days_before: int | None = None
    flex_days_after: int | None = None
    dias_antes: int | None = None
    dias_despues: int | None = None


class QuickSearchSide(BaseModel):
    seed_iata: str
    seed_iata_list: list[str] | None = None
    include_nearby: bool = False
    radius_km: int = Field(default=150, ge=10, le=500)
    max_candidates: int = Field(default=10, ge=1, le=60)

    @field_validator("seed_iata")
    @classmethod
    def validate_seed_iata(cls, value: str) -> str:
        return _validate_iata(value)

    @field_validator("seed_iata_list")
    @classmethod
    def validate_seed_iata_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        for item in value:
            cleaned.append(_validate_iata(item))
        return cleaned


class QuickSearchTravel(BaseModel):
    date: dt.date
    flex_before: int = Field(default=0, ge=0, le=7)
    flex_after: int = Field(default=0, ge=0, le=7)


class QuickSearchDepartureWindow(BaseModel):
    after: str | None = None
    before: str | None = None


class QuickSearchConstraints(BaseModel):
    departure_window: QuickSearchDepartureWindow | None = None
    exclude_origins: list[str] = Field(default_factory=list)
    exclude_destinations: list[str] = Field(default_factory=list)
    strict_filters: bool = True
    include_stops: bool | None = None
    max_stops: int | None = None
    duration_max_min: int | None = None
    risk_allowed: str | None = None
    soft_filters_weight: float | None = None


class QuickSearchExecution(BaseModel):
    max_pairs: int = Field(default=48, ge=1, le=QUICK_SEARCH_MAX_PAIRS_CAP)
    max_requests: int = Field(default=480, ge=1, le=QUICK_SEARCH_MAX_REQUESTS_CAP)
    timeout_ms: int = Field(default=8000, ge=1000, le=30000)
    concurrency_limit: int = Field(default=6, ge=1, le=32)


class QuickSearchCanonicalRequest(BaseModel):
    origin: QuickSearchSide
    destination: QuickSearchSide
    travel: QuickSearchTravel
    constraints: QuickSearchConstraints = Field(default_factory=QuickSearchConstraints)
    execution: QuickSearchExecution = Field(default_factory=QuickSearchExecution)


def _clamp_days(value: int | None, max_days: int = 7) -> int:
    if value is None:
        return 0
    if value < 0:
        return 0
    if value > max_days:
        return max_days
    return value


def _build_flex_dates(base_date: dt.date, days_before: int, days_after: int) -> list[dt.date]:
    if days_before <= 0 and days_after <= 0:
        return [base_date]
    dates: list[dt.date] = []
    for offset in range(-days_before, days_after + 1):
        dates.append(base_date + dt.timedelta(days=offset))
    return dates


def _compute_dynamic_execution_budget(
    *,
    requested_max_pairs: int,
    requested_max_requests: int,
    origin_pool_count: int,
    destination_pool_count: int,
    flex_before: int,
    flex_after: int,
    include_nearby_origins: bool,
    include_nearby_destinations: bool,
) -> tuple[int, int, dict[str, int]]:
    origin_count = max(1, origin_pool_count)
    destination_count = max(1, destination_pool_count)
    pair_complexity = origin_count * destination_count
    date_count = max(1, flex_before + flex_after + 1)
    nearby_sides = int(bool(include_nearby_origins)) + int(bool(include_nearby_destinations))

    pair_multiplier = 6 + (nearby_sides * 4)
    target_pairs = pair_complexity * pair_multiplier
    effective_max_pairs = min(
        QUICK_SEARCH_MAX_PAIRS_CAP,
        max(1, requested_max_pairs, target_pairs),
    )

    request_multiplier = 2 if nearby_sides > 0 else 1
    target_requests = effective_max_pairs * date_count * request_multiplier
    effective_max_requests = min(
        QUICK_SEARCH_MAX_REQUESTS_CAP,
        max(1, requested_max_requests, target_requests),
    )

    return effective_max_pairs, effective_max_requests, {
        "pair_complexity": pair_complexity,
        "date_count": date_count,
        "nearby_sides": nearby_sides,
        "target_pairs": target_pairs,
        "target_requests": target_requests,
    }


def _normalize_radius_km(value: Any, include_nearby: bool, default: int = 150) -> int:
    if value is None:
        return default
    try:
        radius = int(value)
    except (TypeError, ValueError):
        return default

    if radius < 10:
        # Defensive compatibility: old clients used radius=0 as sentinel for "nearby off".
        # Canonical v2 expects radius always within [10, 500], so normalize only when nearby is off.
        return default if not include_nearby else radius

    if radius > 500:
        return 500

    return radius


def _time_to_minutes(value: str | None) -> int | None:
    if not value:
        return None
    parts = value.split(":")
    if len(parts) < 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour * 60 + minute


def _matches_time_window(
    departure: str | None,
    after_value: str | None,
    before_value: str | None,
) -> bool:
    if not after_value and not before_value:
        return True
    dep_minutes = _time_to_minutes(departure)
    if dep_minutes is None:
        return False
    after_minutes = _time_to_minutes(after_value)
    before_minutes = _time_to_minutes(before_value)
    if after_minutes is None and before_minutes is None:
        return True
    if after_minutes is None:
        return dep_minutes <= before_minutes
    if before_minutes is None:
        return dep_minutes >= after_minutes
    if after_minutes <= before_minutes:
        return after_minutes <= dep_minutes <= before_minutes
    return dep_minutes >= after_minutes or dep_minutes <= before_minutes


def _normalize_iata_list(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        items = [str(item).strip().upper() for item in value]
    else:
        items = [item.strip().upper() for item in value.split(",")]
    return [item for item in items if item]


def _seed_priority_key(iata: str) -> tuple[int, str]:
    try:
        airport = resolve_seed_airport(iata)
        return (0 if airport.is_primary else 1, iata)
    except ValueError:
        return (1, iata)


def _normalize_seed_pool(
    seed_iata: str,
    seed_iata_list: list[str] | None,
    *,
    cap: int,
) -> tuple[list[str], bool]:
    raw_codes: list[str] = []
    raw_codes.extend(_parse_iata_input(seed_iata))
    if seed_iata_list:
        raw_codes.extend(_parse_iata_input(seed_iata_list))

    deduped: list[str] = []
    seen: set[str] = set()
    for code in raw_codes:
        if code in seen:
            continue
        seen.add(code)
        deduped.append(code)

    if not deduped:
        raise HTTPException(status_code=400, detail="iata_invalido")

    deduped.sort(key=_seed_priority_key)
    effective = deduped[: max(1, cap)]
    truncated = len(deduped) > len(effective)
    return effective, truncated


def _required_error(field: str) -> ApiError:
    return ApiError(
        status=422,
        code="validation_error",
        message=message_for_code("validation_error"),
        details=[{"loc": ["body", field], "msg": "Field required", "type": "missing"}],
    )


def _parse_iata_input(value: str | list[str]) -> list[str]:
    codes = _normalize_iata_list(value)
    if not codes:
        raise HTTPException(status_code=400, detail="iata_invalido")
    cleaned: list[str] = []
    for code in codes:
        if len(code) != 3 or not code.isalpha():
            raise HTTPException(status_code=400, detail="iata_invalido")
        cleaned.append(code.upper())
    return cleaned


def _normalize_quick_search_request(
    payload_dict: dict[str, Any] | None,
    query_overrides: dict[str, Any],
) -> tuple[QuickSearchCanonicalRequest, list[str], list[str], dict[str, list[str]]]:
    payload_dict = payload_dict or {}
    legacy_payload = QuickSearchPayload.model_validate(payload_dict)

    is_canonical = isinstance(payload_dict.get("origin"), dict) and isinstance(payload_dict.get("destination"), dict)
    legacy_aliases_used: list[str] = []

    if is_canonical:
        canonical_dict = {
            "origin": payload_dict.get("origin"),
            "destination": payload_dict.get("destination"),
            "travel": payload_dict.get("travel"),
            "constraints": payload_dict.get("constraints") or {},
            "execution": payload_dict.get("execution") or {},
        }

        # query params still override canonical body for compatibility with existing clients
        if query_overrides.get("origin_iata"):
            canonical_dict["origin"] = {**(canonical_dict.get("origin") or {}), "seed_iata": query_overrides["origin_iata"]}
            legacy_aliases_used.append("query.origin_iata")
        if query_overrides.get("destination_iata"):
            canonical_dict["destination"] = {**(canonical_dict.get("destination") or {}), "seed_iata": query_overrides["destination_iata"]}
            legacy_aliases_used.append("query.destination_iata")
        if query_overrides.get("travel_date"):
            canonical_dict["travel"] = {**(canonical_dict.get("travel") or {}), "date": query_overrides["travel_date"]}
            legacy_aliases_used.append("query.travel_date")
    else:
        origin_value = query_overrides.get("origin_iata") or legacy_payload.origin_iata
        destination_value = query_overrides.get("destination_iata") or legacy_payload.destination_iata
        travel_date_value = query_overrides.get("travel_date") or legacy_payload.travel_date or legacy_payload.date

        if legacy_payload.include_nearby_origin is not None:
            legacy_aliases_used.append("include_nearby_origin")
        if legacy_payload.include_nearby_destination is not None:
            legacy_aliases_used.append("include_nearby_destination")
        if legacy_payload.strict_mode is not None:
            legacy_aliases_used.append("strict_mode")
        if legacy_payload.departure_from:
            legacy_aliases_used.append("departure_from")
        if legacy_payload.departure_to:
            legacy_aliases_used.append("departure_to")
        if legacy_payload.date:
            legacy_aliases_used.append("date")
        if legacy_payload.dias_antes is not None or legacy_payload.dias_despues is not None:
            legacy_aliases_used.append("dias_antes/dias_despues")

        include_nearby_origins_value = (
            query_overrides.get("include_nearby_origins")
            if query_overrides.get("include_nearby_origins") is not None
            else legacy_payload.include_nearby_origins
            if legacy_payload.include_nearby_origins is not None
            else legacy_payload.include_nearby_origin
            if legacy_payload.include_nearby_origin is not None
            else False
        )
        include_nearby_destinations_value = (
            query_overrides.get("include_nearby_destinations")
            if query_overrides.get("include_nearby_destinations") is not None
            else legacy_payload.include_nearby_destinations
            if legacy_payload.include_nearby_destinations is not None
            else legacy_payload.include_nearby_destination
            if legacy_payload.include_nearby_destination is not None
            else False
        )
        raw_radius_km = (
            query_overrides.get("radius_km")
            if query_overrides.get("radius_km") is not None
            else legacy_payload.radius_km
            if legacy_payload.radius_km is not None
            else 150
        )

        canonical_dict = {
            "origin": {
                "seed_iata": origin_value[0] if isinstance(origin_value, list) and origin_value else origin_value,
                "seed_iata_list": origin_value if isinstance(origin_value, list) else None,
                "include_nearby": include_nearby_origins_value,
                "radius_km": _normalize_radius_km(raw_radius_km, include_nearby_origins_value),
                "max_candidates": 10,
            },
            "destination": {
                "seed_iata": destination_value[0] if isinstance(destination_value, list) and destination_value else destination_value,
                "seed_iata_list": destination_value if isinstance(destination_value, list) else None,
                "include_nearby": include_nearby_destinations_value,
                "radius_km": _normalize_radius_km(raw_radius_km, include_nearby_destinations_value),
                "max_candidates": 10,
            },
            "travel": {
                "date": travel_date_value,
                "flex_before": _clamp_days(
                    query_overrides.get("flex_days_before")
                    if query_overrides.get("flex_days_before") is not None
                    else legacy_payload.flex_days_before
                    if legacy_payload.flex_days_before is not None
                    else legacy_payload.dias_antes
                    if legacy_payload.dias_antes is not None
                    else 0
                ),
                "flex_after": _clamp_days(
                    query_overrides.get("flex_days_after")
                    if query_overrides.get("flex_days_after") is not None
                    else legacy_payload.flex_days_after
                    if legacy_payload.flex_days_after is not None
                    else legacy_payload.dias_despues
                    if legacy_payload.dias_despues is not None
                    else 0
                ),
            },
            "constraints": {
                "departure_window": {
                    "after": query_overrides.get("depart_after") or legacy_payload.depart_after or legacy_payload.departure_from,
                    "before": query_overrides.get("depart_before") or legacy_payload.depart_before or legacy_payload.departure_to,
                },
                "exclude_origins": _normalize_iata_list(
                    query_overrides.get("exclude_origins") if query_overrides.get("exclude_origins") is not None else legacy_payload.exclude_origins
                ),
                "exclude_destinations": _normalize_iata_list(
                    query_overrides.get("exclude_destinations")
                    if query_overrides.get("exclude_destinations") is not None
                    else legacy_payload.exclude_destinations
                ),
                "strict_filters": (
                    query_overrides.get("strict_filters")
                    if query_overrides.get("strict_filters") is not None
                    else legacy_payload.strict_filters
                    if legacy_payload.strict_filters is not None
                    else legacy_payload.strict_mode
                    if legacy_payload.strict_mode is not None
                    else True
                ),
                "include_stops": (
                    query_overrides.get("include_stops")
                    if query_overrides.get("include_stops") is not None
                    else legacy_payload.include_stops
                ),
                "max_stops": (
                    query_overrides.get("max_stops")
                    if query_overrides.get("max_stops") is not None
                    else legacy_payload.max_stops
                ),
                "duration_max_min": (
                    payload_dict.get("duration_max_min")
                    if payload_dict.get("duration_max_min") is not None
                    else payload_dict.get("duration_max")
                    if payload_dict.get("duration_max") is not None
                    else legacy_payload.duration_max_min
                    if legacy_payload.duration_max_min is not None
                    else legacy_payload.duration_max
                ),
                "risk_allowed": (
                    payload_dict.get("risk_allowed")
                    if payload_dict.get("risk_allowed") is not None
                    else payload_dict.get("risk_filter")
                    if payload_dict.get("risk_filter") is not None
                    else legacy_payload.risk_allowed
                    if legacy_payload.risk_allowed is not None
                    else legacy_payload.risk_filter
                ),
                "soft_filters_weight": (
                    query_overrides.get("soft_filters_weight")
                    if query_overrides.get("soft_filters_weight") is not None
                    else legacy_payload.soft_filters_weight
                ),
            },
            "execution": {
                "max_pairs": 48,
                "max_requests": 480,
                "timeout_ms": 8000,
            },
        }

    origin_side_dict = dict(canonical_dict.get("origin") or {})
    destination_side_dict = dict(canonical_dict.get("destination") or {})

    origin_requested_candidates = list(
        dict.fromkeys(
            _normalize_iata_list(origin_side_dict.get("seed_iata"))
            + _normalize_iata_list(origin_side_dict.get("seed_iata_list"))
        )
    )
    destination_requested_candidates = list(
        dict.fromkeys(
            _normalize_iata_list(destination_side_dict.get("seed_iata"))
            + _normalize_iata_list(destination_side_dict.get("seed_iata_list"))
        )
    )

    for side_dict in (origin_side_dict, destination_side_dict):
        side_candidates = _normalize_iata_list(side_dict.get("seed_iata"))
        side_candidates.extend(_normalize_iata_list(side_dict.get("seed_iata_list")))
        if side_candidates:
            side_dict["seed_iata"] = side_candidates[0]
            if len(side_candidates) > 1:
                side_dict["seed_iata_list"] = side_candidates
        elif "seed_iata_list" in side_dict:
            side_dict.pop("seed_iata_list", None)

    include_nearby_origin = bool(origin_side_dict.get("include_nearby", False))
    include_nearby_destination = bool(destination_side_dict.get("include_nearby", False))

    origin_side_dict["radius_km"] = _normalize_radius_km(origin_side_dict.get("radius_km"), include_nearby_origin)
    destination_side_dict["radius_km"] = _normalize_radius_km(destination_side_dict.get("radius_km"), include_nearby_destination)

    canonical_dict["origin"] = origin_side_dict
    canonical_dict["destination"] = destination_side_dict

    try:
        canonical = QuickSearchCanonicalRequest.model_validate(canonical_dict)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    origin_list, origin_seed_pool_truncated = _normalize_seed_pool(
        canonical.origin.seed_iata,
        canonical.origin.seed_iata_list,
        cap=SEED_POOL_CAP,
    )
    destination_list, destination_seed_pool_truncated = _normalize_seed_pool(
        canonical.destination.seed_iata,
        canonical.destination.seed_iata_list,
        cap=SEED_POOL_CAP,
    )
    canonical.origin.seed_iata = origin_list[0]
    canonical.origin.seed_iata_list = origin_list
    canonical.destination.seed_iata = destination_list[0]
    canonical.destination.seed_iata_list = destination_list

    filter_support = {
        "hard_supported": ["strict_filters", "departure_window", "exclude_origins", "exclude_destinations"],
        "soft_supported": ["soft_filters_weight", "seed_distance_penalty", "pair_category_bias"],
        "unsupported": ["include_stops", "max_stops", "duration_max_min", "risk_allowed"],
        "legacy_partial": ["include_stops", "max_stops"],
        "pending": ["stop-logic", "duration-filter", "risk-model"],
        "seed_pool": {
            "cap": SEED_POOL_CAP,
            "origin_requested_count": len(origin_requested_candidates),
            "destination_requested_count": len(destination_requested_candidates),
            "origin_requested_iata": origin_requested_candidates,
            "destination_requested_iata": destination_requested_candidates,
            "origin_count": len(origin_list),
            "destination_count": len(destination_list),
            "origin_effective_iata": origin_list,
            "destination_effective_iata": destination_list,
            "origin_truncated": origin_seed_pool_truncated,
            "destination_truncated": destination_seed_pool_truncated,
        },
    }

    return canonical, origin_list, destination_list, {"aliases": legacy_aliases_used, **filter_support}


@router.get("/deeplink")
def deeplink(
    origin_iata: str,
    destination_iata: str,
    date_out: dt.date,
    date_in: dt.date | None = None,
    adults: int = 1,
    teens: int = 0,
    children: int = 0,
    infants: int = 0,
    locale: str = "es-es",
) -> dict:
    normalized_payload = {
        "origin_iata": origin_iata.strip().upper(),
        "destination_iata": destination_iata.strip().upper(),
        "date_out": str(date_out),
        "date_in": str(date_in) if date_in else None,
        "adults": adults,
        "teens": teens,
        "children": children,
        "infants": infants,
        "locale": locale,
    }
    try:
        origin = _validate_iata(origin_iata)
        destination = _validate_iata(destination_iata)
        normalized_payload["origin_iata"] = origin
        normalized_payload["destination_iata"] = destination
        if adults < 1 or adults > 9:
            raise HTTPException(status_code=400, detail="adultos_invalidos")
        if date_in and date_in < date_out:
            raise HTTPException(status_code=400, detail="fecha_vuelta_invalida")
    except HTTPException as exc:
        reason = _error_reason_from_http_exception(exc)
        logger.warning("deeplink_rejected reason=%s payload=%s", reason, normalized_payload)
        raise ApiError(
            status=exc.status_code,
            code="deeplink_invalid_request",
            message="Deep-link request rejected by backend validation.",
            details=[{"reason": reason, "normalized_payload": normalized_payload}],
        ) from exc

    is_return = "true" if date_in else "false"
    base = f"https://www.ryanair.com/{locale}/trip/flights/select"

    full_params = {
        "adults": str(adults),
        "teens": str(teens),
        "children": str(children),
        "infants": str(infants),
        "dateOut": str(date_out),
        "dateIn": str(date_in or ""),
        "isConnectedFlight": "false",
        "discount": "0",
        "promoCode": "",
        "isReturn": is_return,
        "originIata": origin,
        "destinationIata": destination,
        "originMac": "",
        "destinationMac": "",
        "tpAdults": str(adults),
        "tpTeens": str(teens),
        "tpChildren": str(children),
        "tpInfants": str(infants),
        "tpStartDate": str(date_out),
        "tpEndDate": str(date_in or ""),
        "tpDiscount": "0",
        "tpPromoCode": "",
        "tpOriginIata": origin,
        "tpDestinationIata": destination,
        "tpOriginMac": "",
        "tpDestinationMac": "",
    }

    minimal_params = {
        "adults": str(adults),
        "teens": str(teens),
        "children": str(children),
        "infants": str(infants),
        "dateOut": str(date_out),
        "dateIn": str(date_in or ""),
        "isReturn": is_return,
        "originIata": origin,
        "destinationIata": destination,
    }

    def encode(params: dict[str, str]) -> str:
        from urllib.parse import urlencode

        return f"{base}?{urlencode(params)}"

    return {
        "status": "ok",
        "origin_iata": origin,
        "destination_iata": destination,
        "date_out": str(date_out),
        "date_in": str(date_in) if date_in else None,
        "url": encode(full_params),
        "fallback_url": encode(minimal_params),
        "strategy": "full",
    }


@router.post("/quick")
def quick_search(
    payload: dict[str, Any] | None = Body(default=None),
    origin_iata: str | None = Query(default=None),
    destination_iata: str | None = Query(default=None),
    travel_date: dt.date | None = Query(default=None),
    radius_km: int | None = Query(default=None),
    include_stops: bool | None = Query(default=None),
    include_nearby_origins: bool | None = Query(default=None),
    include_nearby_destinations: bool | None = Query(default=None),
    depart_after: str | None = Query(default=None),
    depart_before: str | None = Query(default=None),
    max_stops: int | None = Query(default=None),
    exclude_origins: str | None = Query(default=None),
    exclude_destinations: str | None = Query(default=None),
    strict_filters: bool | None = Query(default=None),
    soft_filters_weight: float | None = Query(default=None),
    flex_days_before: int | None = Query(default=None),
    flex_days_after: int | None = Query(default=None),
    debug: bool = Query(default=False),
) -> dict:
    query_trace_id = f"qs_{uuid.uuid4().hex[:12]}"
    is_debug_allowed = os.getenv("APP_ENV", "local") == "local"
    debug_mode = bool(debug and is_debug_allowed)

    t0 = time.perf_counter()
    phase_ms: dict[str, int] = {}
    warnings_structured: list[dict[str, Any]] = []
    warnings_structured_seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()

    def _phase_start() -> float:
        return time.perf_counter()

    def _phase_end(name: str, started_at: float) -> None:
        phase_ms[name] = int((time.perf_counter() - started_at) * 1000)

    def _warn(code: str, **meta: Any) -> None:
        code = _normalize_warning_code(code)
        normalized_meta = tuple(sorted((str(key), repr(value)) for key, value in meta.items()))
        dedupe_key = (code, normalized_meta)
        if dedupe_key in warnings_structured_seen:
            return
        warnings_structured_seen.add(dedupe_key)
        warnings_structured.append({"code": code, "meta": meta})

    started = _phase_start()
    query_overrides = {
        "origin_iata": origin_iata,
        "destination_iata": destination_iata,
        "travel_date": travel_date,
        "radius_km": radius_km,
        "include_stops": include_stops,
        "include_nearby_origins": include_nearby_origins,
        "include_nearby_destinations": include_nearby_destinations,
        "depart_after": depart_after,
        "depart_before": depart_before,
        "max_stops": max_stops,
        "exclude_origins": exclude_origins,
        "exclude_destinations": exclude_destinations,
        "strict_filters": strict_filters,
        "soft_filters_weight": soft_filters_weight,
        "flex_days_before": flex_days_before,
        "flex_days_after": flex_days_after,
    }
    try:
        canonical, origin_list, destination_list, filter_contract = _normalize_quick_search_request(
            payload,
            query_overrides,
        )
    except HTTPException as exc:
        reason = _error_reason_from_http_exception(exc)
        detail_item = {
            "query_trace_id": query_trace_id,
            "reason": reason,
            "raw_payload": payload or {},
            "query_overrides": {
                key: (str(value) if isinstance(value, dt.date) else value)
                for key, value in query_overrides.items()
                if value is not None
            },
        }
        logger.warning(
            "quick_search_normalization_rejected trace=%s reason=%s payload=%s query=%s",
            query_trace_id,
            reason,
            payload or {},
            detail_item["query_overrides"],
        )
        raise ApiError(
            status=exc.status_code,
            code="quick_search_invalid_request",
            message="Quick-search request rejected during request normalization.",
            details=[detail_item],
        ) from exc
    _phase_end("request_normalization_ms", started)

    travel_date_value = canonical.travel.date
    origin_seed_pool = list(origin_list)
    destination_seed_pool = list(destination_list)
    requested_days_before = canonical.travel.flex_before
    requested_days_after = canonical.travel.flex_after

    requested_include_nearby_origins = canonical.origin.include_nearby
    requested_include_nearby_destinations = canonical.destination.include_nearby
    requested_radius_km_origin = canonical.origin.radius_km
    requested_radius_km_destination = canonical.destination.radius_km

    requested_depart_after = canonical.constraints.departure_window.after if canonical.constraints.departure_window else None
    requested_depart_before = canonical.constraints.departure_window.before if canonical.constraints.departure_window else None
    strict_filters = canonical.constraints.strict_filters
    include_stops = bool(canonical.constraints.include_stops)
    max_stops = canonical.constraints.max_stops or 0
    duration_max_min = canonical.constraints.duration_max_min
    risk_allowed = canonical.constraints.risk_allowed
    soft_filters_weight = canonical.constraints.soft_filters_weight if canonical.constraints.soft_filters_weight is not None else 0.6

    max_pairs_dynamic_base, max_requests_dynamic_base, budget_signals = _compute_dynamic_execution_budget(
        requested_max_pairs=canonical.execution.max_pairs,
        requested_max_requests=canonical.execution.max_requests,
        origin_pool_count=len(origin_seed_pool),
        destination_pool_count=len(destination_seed_pool),
        flex_before=requested_days_before,
        flex_after=requested_days_after,
        include_nearby_origins=requested_include_nearby_origins,
        include_nearby_destinations=requested_include_nearby_destinations,
    )

    warnings: list[str] = []
    filters_applied: dict[str, Any] = {}
    relaxed_filters: list[str] = []

    if canonical.execution.timeout_ms != 8000:
        warnings.append("timeout_ms_not_yet_enforced_at_provider_level")
        _warn("timeout_ms_non_default", timeout_ms=canonical.execution.timeout_ms)

    if include_stops or max_stops > 0:
        warnings.append("stops_no_disponible_en_modo_rapido")
        _warn("unsupported_filter", filter="include_stops/max_stops", include_stops=include_stops, max_stops=max_stops)
        if strict_filters:
            _warn("strict_filter_not_enforceable", filter="include_stops/max_stops")
        else:
            _warn("degraded_filter_application", filter="include_stops/max_stops", mode="soft")

    if duration_max_min is not None:
        _warn("provider_missing_field_for_filter", filter="duration_max_min", value=duration_max_min)
        if strict_filters:
            _warn("strict_filter_not_enforceable", filter="duration_max_min")
        else:
            _warn("degraded_filter_application", filter="duration_max_min", mode="soft")

    if risk_allowed not in (None, "", "all"):
        _warn("unsupported_filter", filter="risk_allowed", value=risk_allowed)
        if strict_filters:
            _warn("strict_filter_not_enforceable", filter="risk_allowed")
        else:
            _warn("degraded_filter_application", filter="risk_allowed", mode="soft")

    exclude_origin_list = canonical.constraints.exclude_origins
    exclude_destination_list = canonical.constraints.exclude_destinations
    country_scope_multi_seed_mode = len(origin_seed_pool) > 1 or len(destination_seed_pool) > 1

    if len(origin_seed_pool) > 1:
        _warn("country_scope_multi_seed_applied", side="origin", seed_count=len(origin_seed_pool))
    if len(destination_seed_pool) > 1:
        _warn("country_scope_multi_seed_applied", side="destination", seed_count=len(destination_seed_pool))
    if filter_contract.get("seed_pool", {}).get("origin_truncated"):
        _warn(
            "country_scope_seed_pool_truncated",
            side="origin",
            cap=filter_contract["seed_pool"]["cap"],
            effective_count=filter_contract["seed_pool"]["origin_count"],
        )
    if filter_contract.get("seed_pool", {}).get("destination_truncated"):
        _warn(
            "country_scope_seed_pool_truncated",
            side="destination",
            cap=filter_contract["seed_pool"]["cap"],
            effective_count=filter_contract["seed_pool"]["destination_count"],
        )

    def _phase_add(name: str, elapsed_ms: int) -> None:
        phase_ms[name] = phase_ms.get(name, 0) + elapsed_ms

    def _candidate_rank_key(candidate: Any) -> tuple[int, float, str, str]:
        return (
            0 if getattr(candidate, "is_seed", False) else 1,
            float(getattr(candidate, "distance_km", 0.0)),
            str(getattr(candidate, "seed_iata", "")),
            str(getattr(candidate, "expanded_iata", "")),
        )

    def _merge_side_results(
        *,
        side: str,
        seed_pool: list[str],
        include_nearby: bool,
        radius_km: int,
        max_candidates: int,
        exclusions: list[str],
        results: list[SideExpansionResult],
    ) -> SideExpansionResult:
        merged_by_iata: dict[str, Any] = {}
        for result in results:
            for candidate in result.candidates:
                existing = merged_by_iata.get(candidate.expanded_iata)
                if existing is None or _candidate_rank_key(candidate) < _candidate_rank_key(existing):
                    merged_by_iata[candidate.expanded_iata] = candidate

        merged_candidates = sorted(merged_by_iata.values(), key=_candidate_rank_key)
        limited = merged_candidates[: max(1, max_candidates)]
        return SideExpansionResult(
            side=side,
            candidates=limited,
            summary=SideExpansionSummary(
                side=side,
                seed_iata=seed_pool[0],
                include_nearby_applied=include_nearby,
                radius_km_effective=radius_km,
                max_candidates_effective=max(1, max_candidates),
                exclusions_applied=sorted({code.strip().upper() for code in exclusions if code}),
                total_candidates_before_limit=len(merged_candidates),
                total_candidates_after_limit=len(limited),
            ),
        )

    def _run_pass(
        *,
        step: str,
        origin_seed_pool_pass: list[str],
        destination_seed_pool_pass: list[str],
        days_before: int,
        days_after: int,
        include_nearby_origins: bool,
        include_nearby_destinations: bool,
        radius_km_origin: int,
        radius_km_destination: int,
        depart_after: str | None,
        depart_before: str | None,
        max_pairs_override: int | None = None,
        max_requests_override: int | None = None,
    ) -> dict[str, Any]:
        max_pairs_effective = max(1, max_pairs_override if max_pairs_override is not None else max_pairs_dynamic_base)
        max_requests_effective = max(
            1,
            max_requests_override if max_requests_override is not None else max_requests_dynamic_base,
        )
        if max_pairs_override is None:
            max_pairs_effective = max(1, max_pairs_dynamic_base)
        started = _phase_start()
        try:
            origin_results: list[SideExpansionResult] = []
            destination_results: list[SideExpansionResult] = []

            for origin_seed in origin_seed_pool_pass:
                origin_side_item, _ = expand_search_sides(
                    origin_seed_iata=origin_seed,
                    destination_seed_iata=destination_seed_pool_pass[0],
                    include_nearby_origins=include_nearby_origins,
                    include_nearby_destinations=include_nearby_destinations,
                    origin_radius_km=radius_km_origin,
                    destination_radius_km=radius_km_destination,
                    origin_max_candidates=canonical.origin.max_candidates,
                    destination_max_candidates=canonical.destination.max_candidates,
                    exclude_origins=exclude_origin_list,
                    exclude_destinations=exclude_destination_list,
                )
                origin_results.append(origin_side_item)

            for destination_seed in destination_seed_pool_pass:
                _, destination_side_item = expand_search_sides(
                    origin_seed_iata=origin_seed_pool_pass[0],
                    destination_seed_iata=destination_seed,
                    include_nearby_origins=include_nearby_origins,
                    include_nearby_destinations=include_nearby_destinations,
                    origin_radius_km=radius_km_origin,
                    destination_radius_km=radius_km_destination,
                    origin_max_candidates=canonical.origin.max_candidates,
                    destination_max_candidates=canonical.destination.max_candidates,
                    exclude_origins=exclude_origin_list,
                    exclude_destinations=exclude_destination_list,
                )
                destination_results.append(destination_side_item)

            origin_target_max_candidates = min(24, max(1, canonical.origin.max_candidates * len(origin_seed_pool_pass)))
            destination_target_max_candidates = min(24, max(1, canonical.destination.max_candidates * len(destination_seed_pool_pass)))
            origin_side = _merge_side_results(
                side="origin",
                seed_pool=origin_seed_pool_pass,
                include_nearby=include_nearby_origins,
                radius_km=radius_km_origin,
                max_candidates=origin_target_max_candidates,
                exclusions=exclude_origin_list,
                results=origin_results,
            )
            destination_side = _merge_side_results(
                side="destination",
                seed_pool=destination_seed_pool_pass,
                include_nearby=include_nearby_destinations,
                radius_km=radius_km_destination,
                max_candidates=destination_target_max_candidates,
                exclusions=exclude_destination_list,
                results=destination_results,
            )
        except ValueError as exc:
            reason = str(exc)
            detail_item = {
                "query_trace_id": query_trace_id,
                "reason": reason,
                "canonical_request": canonical.model_dump(mode="json"),
                "rescue_step": step,
            }
            if ":" in reason:
                reason_code, rejected_value = reason.split(":", 1)
                detail_item["reason_code"] = reason_code
                detail_item["rejected_value"] = rejected_value
            logger.warning(
                "quick_search_rejected trace=%s reason=%s canonical=%s step=%s",
                query_trace_id,
                reason,
                canonical.model_dump(mode="json"),
                step,
            )
            raise ApiError(
                status=400,
                code="quick_search_invalid_request",
                message="Quick-search request rejected by backend validation.",
                details=[detail_item],
            ) from exc
        _phase_add("nearby_expansion_ms", int((time.perf_counter() - started) * 1000))

        origin_expanded = origin_side.candidates
        destination_expanded = destination_side.candidates

        if include_nearby_origins and len(origin_expanded) <= 1:
            _warn("no_nearby_candidates_found", side="origin", seed_iata=canonical.origin.seed_iata)
        if include_nearby_destinations and len(destination_expanded) <= 1:
            _warn("no_nearby_candidates_found", side="destination", seed_iata=canonical.destination.seed_iata)

        date_candidates = _build_flex_dates(travel_date_value, days_before, days_after)

        started = _phase_start()
        pair_plan, pair_plan_stats = build_pair_plan(
            origin_expanded,
            destination_expanded,
            max_pairs=max_pairs_effective,
            max_requests=max_requests_effective,
            date_count=len(date_candidates),
        )
        if pair_plan_stats["truncated"]:
            warnings.append("limite_combinaciones_alternativas")
            warnings.append("pair_cap_reached")
            _warn("max_pairs_truncated", max_pairs=max_pairs_effective, total_pairs=pair_plan_stats["total_pairs"])
        _phase_add("pair_planning_ms", int((time.perf_counter() - started) * 1000))

        started = _phase_start()
        execution_plan = build_execution_plan(
            pair_plan,
            date_candidates,
            max_requests=max_requests_effective,
        )
        _phase_add("execution_planning_ms", int((time.perf_counter() - started) * 1000))

        started = _phase_start()
        combined, execution_meta, execution_warnings = execute_plan(
            execution_plan,
            concurrency_limit=canonical.execution.concurrency_limit,
            timeout_ms=canonical.execution.timeout_ms,
            fetch_flights=lambda o, d, date_str, timeout: provider.get_flights(o, d, date_str, timeout_ms=timeout),
        )
        _phase_add("provider_fetch_ms", int((time.perf_counter() - started) * 1000))

        normalized_execution_warnings = _normalize_warning_codes(execution_warnings)
        warning_codes = list(normalized_execution_warnings)
        warnings.extend(normalized_execution_warnings)
        for code in normalized_execution_warnings:
            _warn(code)
        if any(code.endswith("_partial") for code in normalized_execution_warnings) and combined:
            _warn("provider_partial_results_served", count=len(combined))
            warning_codes.append("provider_partial_results_served")
        if execution_meta.get("truncated_by_max_requests"):
            warnings.append("request_cap_reached")
            _warn(
                "max_requests_reached",
                requested_units_count=execution_meta.get("requested_units_count"),
                skipped_units_count=execution_meta.get("skipped_units_count"),
            )
        if execution_meta.get("timed_out_units_count", 0):
            _warn("provider_timeout_partial", count=execution_meta.get("timed_out_units_count"))
            warning_codes.append("provider_timeout_partial")
        if execution_meta.get("provider_failures", 0):
            _warn("provider_error_partial", count=execution_meta.get("provider_failures"))
            warning_codes.append("provider_error_partial")

        filtered = [
            (origin_code, destination_code, travel_date_item, flight)
            for origin_code, destination_code, travel_date_item, flight in combined
            if _matches_time_window(flight.departure_time_local, depart_after, depart_before)
        ]

        pass_filters_applied: dict[str, Any] = {}
        pass_relaxed_filters: list[str] = []
        if depart_after or depart_before:
            pass_filters_applied["departure_window"] = {"after": depart_after, "before": depart_before}

        if strict_filters:
            flights_after_filters = filtered
        else:
            flights_after_filters = filtered
            if not flights_after_filters and (depart_after or depart_before):
                flights_after_filters = combined
                pass_relaxed_filters.append("departure_window")

        started = _phase_start()
        ranked_results = rank_quick_search_results(
            flights_after_filters,
            pair_plan,
            soft_filters_weight=soft_filters_weight,
        )
        _phase_add("ranking_ms", int((time.perf_counter() - started) * 1000))

        started = _phase_start()
        deduped = dedupe_ranked_results(ranked_results)
        _phase_add("dedupe_ms", int((time.perf_counter() - started) * 1000))

        return {
            "step": step,
            "origin_side": origin_side,
            "destination_side": destination_side,
            "origin_expanded": origin_expanded,
            "destination_expanded": destination_expanded,
            "date_candidates": date_candidates,
            "pair_plan": pair_plan,
            "pair_plan_stats": pair_plan_stats,
            "execution_plan": execution_plan,
            "execution_meta": execution_meta,
            "combined": combined,
            "flights_after_filters": flights_after_filters,
            "filters_applied": pass_filters_applied,
            "relaxed_filters": pass_relaxed_filters,
            "warning_codes": list(dict.fromkeys(warning_codes)),
            "deduped": deduped,
            "max_pairs_effective": max_pairs_effective,
            "max_requests_effective": max_requests_effective,
            "expansion_cap_reached": (
                origin_side.summary.total_candidates_before_limit > origin_side.summary.total_candidates_after_limit
                or destination_side.summary.total_candidates_before_limit > destination_side.summary.total_candidates_after_limit
            ),
        }

    pass_1 = _run_pass(
        step="pass_1_exact",
        origin_seed_pool_pass=origin_seed_pool,
        destination_seed_pool_pass=destination_seed_pool,
        days_before=requested_days_before,
        days_after=requested_days_after,
        include_nearby_origins=requested_include_nearby_origins,
        include_nearby_destinations=requested_include_nearby_destinations,
        radius_km_origin=requested_radius_km_origin,
        radius_km_destination=requested_radius_km_destination,
        depart_after=requested_depart_after,
        depart_before=requested_depart_before,
    )

    degradation_signal_codes = {
        "ryanair_availability_failed_partial",
        "ryanair_fares_failed_partial",
        "ryanair_unavailable_partial",
        "provider_error_partial",
    }
    pass_1_has_degradation = any(code in degradation_signal_codes for code in pass_1["warning_codes"])

    rescue_attempted = False
    rescue_pass_summaries: list[dict[str, Any]] = [
        {
            "step": pass_1["step"],
            "result_count": len(pass_1["deduped"].results),
            "warnings": pass_1["warning_codes"],
            "max_pairs_effective": pass_1["max_pairs_effective"],
            "max_requests_effective": pass_1["max_requests_effective"],
        }
    ]
    selected_pass = pass_1

    rescue_step_config_by_name: dict[str, dict[str, Any]] = {}
    should_rescue_for_country_scope = len(pass_1["deduped"].results) == 0 and country_scope_multi_seed_mode
    if len(pass_1["deduped"].results) == 0 and (pass_1_has_degradation or should_rescue_for_country_scope):
        rescue_attempted = True
        warnings.append("rescue_mode_applied")
        _warn("rescue_mode_applied")

        budget_boost_max_requests = min(QUICK_SEARCH_MAX_REQUESTS_CAP, max_requests_dynamic_base * 2)
        budget_boost_max_pairs = min(QUICK_SEARCH_MAX_PAIRS_CAP, max_pairs_dynamic_base * 2)
        rescue_steps: list[dict[str, Any]] = []
        rescue_steps.append(
            {
                "step": "pass_2_rescue_budget_boost",
                "days_before": requested_days_before,
                "days_after": requested_days_after,
                "include_nearby_origins": requested_include_nearby_origins,
                "include_nearby_destinations": requested_include_nearby_destinations,
                "radius_km_origin": requested_radius_km_origin,
                "radius_km_destination": requested_radius_km_destination,
                "depart_after": requested_depart_after,
                "depart_before": requested_depart_before,
                "max_pairs_override": budget_boost_max_pairs,
                "max_requests_override": budget_boost_max_requests,
            }
        )
        if requested_days_before == 0 and requested_days_after == 0:
            rescue_steps.append(
                {
                    "step": "pass_3_rescue_date",
                    "days_before": 1,
                    "days_after": 1,
                    "include_nearby_origins": requested_include_nearby_origins,
                    "include_nearby_destinations": requested_include_nearby_destinations,
                    "radius_km_origin": requested_radius_km_origin,
                    "radius_km_destination": requested_radius_km_destination,
                    "depart_after": requested_depart_after,
                    "depart_before": requested_depart_before,
                    "max_pairs_override": None,
                    "max_requests_override": None,
                }
            )
        rescue_steps.append(
            {
                "step": "pass_4_rescue_nearby",
                "days_before": requested_days_before,
                "days_after": requested_days_after,
                "include_nearby_origins": True,
                "include_nearby_destinations": True,
                "radius_km_origin": max(150, requested_radius_km_origin),
                "radius_km_destination": max(150, requested_radius_km_destination),
                "depart_after": requested_depart_after,
                "depart_before": requested_depart_before,
                "max_pairs_override": None,
                "max_requests_override": None,
            }
        )
        rescue_steps.append(
            {
                "step": "pass_5_rescue_time_window",
                "days_before": 1 if requested_days_before == 0 and requested_days_after == 0 else requested_days_before,
                "days_after": 1 if requested_days_before == 0 and requested_days_after == 0 else requested_days_after,
                "include_nearby_origins": True,
                "include_nearby_destinations": True,
                "radius_km_origin": max(150, requested_radius_km_origin),
                "radius_km_destination": max(150, requested_radius_km_destination),
                "depart_after": None,
                "depart_before": None,
                "max_pairs_override": None,
                "max_requests_override": None,
            }
        )

        rescue_step_config_by_name = {item["step"]: item for item in rescue_steps}

        for config in rescue_steps:
            candidate_pass = _run_pass(
                step=config["step"],
                origin_seed_pool_pass=origin_seed_pool,
                destination_seed_pool_pass=destination_seed_pool,
                days_before=config["days_before"],
                days_after=config["days_after"],
                include_nearby_origins=config["include_nearby_origins"],
                include_nearby_destinations=config["include_nearby_destinations"],
                radius_km_origin=config["radius_km_origin"],
                radius_km_destination=config["radius_km_destination"],
                depart_after=config["depart_after"],
                depart_before=config["depart_before"],
                max_pairs_override=config["max_pairs_override"],
                max_requests_override=config["max_requests_override"],
            )
            rescue_pass_summaries.append(
                {
                    "step": candidate_pass["step"],
                    "result_count": len(candidate_pass["deduped"].results),
                    "warnings": candidate_pass["warning_codes"],
                    "max_pairs_effective": candidate_pass["max_pairs_effective"],
                    "max_requests_effective": candidate_pass["max_requests_effective"],
                }
            )
            if len(candidate_pass["deduped"].results) > 0:
                selected_pass = candidate_pass
                break

    origin_side = selected_pass["origin_side"]
    destination_side = selected_pass["destination_side"]
    origin_expanded = selected_pass["origin_expanded"]
    destination_expanded = selected_pass["destination_expanded"]
    date_candidates = selected_pass["date_candidates"]
    pair_plan = selected_pass["pair_plan"]
    pair_plan_stats = selected_pass["pair_plan_stats"]
    execution_plan = selected_pass["execution_plan"]
    execution_meta = selected_pass["execution_meta"]
    combined = selected_pass["combined"]
    flights_after_filters = selected_pass["flights_after_filters"]
    deduped = selected_pass["deduped"]
    filters_applied = selected_pass["filters_applied"]
    relaxed_filters = selected_pass["relaxed_filters"]
    pair_count = len(pair_plan)

    rescue_winning_step: str | None = None
    rescue_auto_relaxed: list[str] = []
    if rescue_attempted and selected_pass["step"] != "pass_1_exact" and len(deduped.results) > 0:
        rescue_winning_step = selected_pass["step"]
        step_config = rescue_step_config_by_name.get(selected_pass["step"])
        if step_config:
            if step_config["days_before"] != requested_days_before or step_config["days_after"] != requested_days_after:
                rescue_auto_relaxed.append("date_flex_auto")
            if (
                step_config["include_nearby_origins"] != requested_include_nearby_origins
                or step_config["include_nearby_destinations"] != requested_include_nearby_destinations
                or step_config["radius_km_origin"] != requested_radius_km_origin
                or step_config["radius_km_destination"] != requested_radius_km_destination
            ):
                rescue_auto_relaxed.append("nearby_auto")
            if step_config["depart_after"] != requested_depart_after or step_config["depart_before"] != requested_depart_before:
                rescue_auto_relaxed.append("departure_window_auto")

    relaxed_filters = list(dict.fromkeys(relaxed_filters + rescue_auto_relaxed))

    origin_scope_iata = {candidate.expanded_iata for candidate in origin_expanded}
    destination_scope_iata = {candidate.expanded_iata for candidate in destination_expanded}
    scoped_ranked_results = [
        item
        for item in deduped.results
        if item.origin in origin_scope_iata and item.destination in destination_scope_iata
    ]
    out_of_scope_discarded = max(0, len(deduped.results) - len(scoped_ranked_results))
    if out_of_scope_discarded > 0:
        warnings.append("result_out_of_scope_discarded")
        _warn(
            "result_out_of_scope_discarded",
            step=selected_pass["step"],
            discarded_count=out_of_scope_discarded,
        )

    signature_origin_seed_pool = filter_contract.get("seed_pool", {}).get("origin_requested_iata") or origin_seed_pool
    signature_destination_seed_pool = filter_contract.get("seed_pool", {}).get("destination_requested_iata") or destination_seed_pool
    query_signature = _build_query_signature(
        origin_seed_pool=signature_origin_seed_pool,
        destination_seed_pool=signature_destination_seed_pool,
        travel_date=travel_date_value,
        flex_before=requested_days_before,
        flex_after=requested_days_after,
        include_nearby_origins=requested_include_nearby_origins,
        include_nearby_destinations=requested_include_nearby_destinations,
        radius_km_origin=requested_radius_km_origin,
        radius_km_destination=requested_radius_km_destination,
        depart_after=requested_depart_after,
        depart_before=requested_depart_before,
        strict_filters=strict_filters,
        include_stops=include_stops,
        max_stops=max_stops,
        soft_filters_weight=soft_filters_weight,
        winning_step=selected_pass["step"],
    )

    planned_route_scope = {
        "winning_step": selected_pass["step"],
        "origin_seed_pool_effective": list(origin_seed_pool),
        "destination_seed_pool_effective": list(destination_seed_pool),
        "origin_expanded_iata": sorted(origin_scope_iata),
        "destination_expanded_iata": sorted(destination_scope_iata),
        "origin_expanded_count": len(origin_scope_iata),
        "destination_expanded_count": len(destination_scope_iata),
    }
    seed_pool_trace = {
        **filter_contract.get("seed_pool", {}),
        "winning_step": selected_pass["step"],
        "origin_scope_count": len(origin_scope_iata),
        "destination_scope_count": len(destination_scope_iata),
    }

    warnings = _normalize_warning_codes(warnings)
    phase_ms["total_search_ms"] = int((time.perf_counter() - t0) * 1000)
    requested_date_candidates = _build_flex_dates(travel_date_value, requested_days_before, requested_days_after)

    warning_codes_set = set(warnings)
    availability_failed = bool(
        warning_codes_set
        & {
            "ryanair_availability_failed_partial",
            "ryanair_availability_failed",
        }
    )
    fares_failed = bool(
        warning_codes_set
        & {
            "ryanair_fares_failed_partial",
            "ryanair_fares_failed",
        }
    )
    provider_total_outage = "ryanair_provider_unavailable_total" in warning_codes_set
    partial_results_served = bool(scoped_ranked_results) and (availability_failed or fares_failed)
    if provider_total_outage:
        provider_overall_status = "total_outage"
    elif availability_failed or fares_failed:
        provider_overall_status = "partial_degraded"
    else:
        provider_overall_status = "ok"
    provider_status = {
        "provider": "ryanair",
        "availability": {"status": "failed" if availability_failed else "ok"},
        "fares": {"status": "failed" if fares_failed else "ok"},
        "overall": provider_overall_status,
        "partial_results_served": partial_results_served,
        "total_outage": provider_total_outage,
    }

    logger.info(
        "quick_search trace=%s results=%s planned_pairs=%s requested_units=%s rescue=%s winning_step=%s",
        query_trace_id,
        len(scoped_ranked_results),
        pair_plan_stats["total_pairs"],
        execution_meta.get("requested_units_count", 0),
        rescue_attempted,
        rescue_winning_step,
    )

    debug_payload: dict[str, Any] | None = None
    if debug_mode:
        debug_payload = {
            "trace": {"query_trace_id": query_trace_id, "app_env": os.getenv("APP_ENV", "local")},
            "warnings_structured": warnings_structured,
            "expanded": {
                "origins": [candidate.__dict__ for candidate in origin_expanded],
                "destinations": [candidate.__dict__ for candidate in destination_expanded],
            },
            "planned_pairs": [pair.__dict__ for pair in pair_plan],
            "execution_units": [
                {
                    "origin_iata": unit.origin_iata,
                    "destination_iata": unit.destination_iata,
                    "travel_date": str(unit.travel_date),
                    "pair_reason": unit.pair_reason,
                    "pair_priority_score": unit.pair_priority_score,
                }
                for unit in execution_plan.units
            ],
            "rescue": {
                "attempted": rescue_attempted,
                "applied_steps": [item["step"] for item in rescue_pass_summaries if item["step"] != "pass_1_exact"],
                "winning_step": rescue_winning_step,
                "pass_summaries": rescue_pass_summaries,
            },
            "query_signature": query_signature,
            "planned_route_scope": planned_route_scope,
        }

    return {
        "query": {
            "origin": canonical.origin.model_dump(),
            "destination": canonical.destination.model_dump(),
            "travel": {
                "date": str(travel_date_value),
                "flex_before": requested_days_before,
                "flex_after": requested_days_after,
                "travel_dates": [str(date_item) for date_item in requested_date_candidates],
            },
            "constraints": {
                "departure_window": {"after": requested_depart_after, "before": requested_depart_before},
                "exclude_origins": exclude_origin_list,
                "exclude_destinations": exclude_destination_list,
                "strict_filters": strict_filters,
                "include_stops": include_stops,
                "max_stops": max_stops,
                "duration_max_min": duration_max_min,
                "risk_allowed": risk_allowed,
                "soft_filters_weight": soft_filters_weight,
            },
            "execution": canonical.execution.model_dump(),
            "expanded_origins": [
                {
                    "seed_iata": candidate.seed_iata,
                    "expanded_iata": candidate.expanded_iata,
                    "is_seed": candidate.is_seed,
                    "distance_km": candidate.distance_km,
                    "candidate_reason": candidate.candidate_reason,
                    "source_of_expansion": candidate.source_of_expansion,
                    "side": "origin",
                }
                for candidate in origin_expanded
            ],
            "expanded_destinations": [
                {
                    "seed_iata": candidate.seed_iata,
                    "expanded_iata": candidate.expanded_iata,
                    "is_seed": candidate.is_seed,
                    "distance_km": candidate.distance_km,
                    "candidate_reason": candidate.candidate_reason,
                    "source_of_expansion": candidate.source_of_expansion,
                    "side": "destination",
                }
                for candidate in destination_expanded
            ],
        },
        "meta": {
            "query_trace_id": query_trace_id,
            "query_signature": query_signature,
            "contract_version": "quick_search.v2",
            "legacy_aliases_used": filter_contract["aliases"],
            "filter_support": {
                "hard_supported": filter_contract["hard_supported"],
                "soft_supported": filter_contract["soft_supported"],
                "unsupported": filter_contract["unsupported"],
                "legacy_partial": filter_contract["legacy_partial"],
                "pending": filter_contract["pending"],
                "seed_pool": seed_pool_trace,
            },
            "rescue": {
                "attempted": rescue_attempted,
                "applied_steps": [item["step"] for item in rescue_pass_summaries if item["step"] != "pass_1_exact"],
                "winning_step": rescue_winning_step,
                "pass_summaries": rescue_pass_summaries,
            },
            "planned_route_scope": planned_route_scope,
            "pair_counts": {
                "evaluated": pair_count,
                "total_pairs": pair_plan_stats["total_pairs"],
                "selected_pairs": pair_plan_stats["selected_pairs"],
                "truncated": pair_plan_stats["truncated"],
                "max_pairs": selected_pass["max_pairs_effective"],
                "max_pairs_by_requests": pair_plan_stats["max_pairs_by_requests"],
                "max_pairs_scope": "base_pairs_only",
            },
            "truncation_signals": {
                "expansion_cap": bool(selected_pass.get("expansion_cap_reached")),
                "pair_cap": bool(pair_plan_stats["truncated"]),
                "request_cap": bool(execution_meta.get("truncated_by_max_requests")),
            },
            "execution_budget": {
                "requested": canonical.execution.model_dump(),
                "effective": {
                    "max_pairs": selected_pass["max_pairs_effective"],
                    "max_requests": selected_pass["max_requests_effective"],
                },
                "dynamic_signals": budget_signals,
                "caps": {
                    "max_pairs_cap": QUICK_SEARCH_MAX_PAIRS_CAP,
                    "max_requests_cap": QUICK_SEARCH_MAX_REQUESTS_CAP,
                },
            },
            "planned_pairs": [
                {
                    "origin_iata": pair.origin_iata,
                    "destination_iata": pair.destination_iata,
                    "origin_seed_iata": pair.origin_seed_iata,
                    "destination_seed_iata": pair.destination_seed_iata,
                    "origin_is_seed": pair.origin_is_seed,
                    "destination_is_seed": pair.destination_is_seed,
                    "origin_distance_from_seed_km": pair.origin_distance_from_seed_km,
                    "destination_distance_from_seed_km": pair.destination_distance_from_seed_km,
                    "pair_priority_score": pair.pair_priority_score,
                    "pair_reason": pair.pair_reason,
                }
                for pair in pair_plan
            ],
            "expansion": {
                "origin": {
                    "side": origin_side.summary.side,
                    "seed_iata": origin_side.summary.seed_iata,
                    "include_nearby_applied": origin_side.summary.include_nearby_applied,
                    "radius_km_effective": origin_side.summary.radius_km_effective,
                    "max_candidates_effective": origin_side.summary.max_candidates_effective,
                    "exclusions_applied": origin_side.summary.exclusions_applied,
                    "total_candidates_before_limit": origin_side.summary.total_candidates_before_limit,
                    "total_candidates_after_limit": origin_side.summary.total_candidates_after_limit,
                },
                "destination": {
                    "side": destination_side.summary.side,
                    "seed_iata": destination_side.summary.seed_iata,
                    "include_nearby_applied": destination_side.summary.include_nearby_applied,
                    "radius_km_effective": destination_side.summary.radius_km_effective,
                    "max_candidates_effective": destination_side.summary.max_candidates_effective,
                    "exclusions_applied": destination_side.summary.exclusions_applied,
                    "total_candidates_before_limit": destination_side.summary.total_candidates_before_limit,
                    "total_candidates_after_limit": destination_side.summary.total_candidates_after_limit,
                },
            },
            "execution": execution_meta,
            "pipeline_metrics": phase_ms,
            "pipeline_counters": {
                "origin_candidates_count": len(origin_expanded),
                "destination_candidates_count": len(destination_expanded),
                "planned_pairs_count": pair_plan_stats["total_pairs"],
                "executed_pairs_count": execution_meta.get("executed_pairs_count", 0),
                "skipped_pairs_count": execution_meta.get("skipped_pairs_count", 0),
                "requested_units_count": execution_meta.get("requested_units_count", 0),
                "provider_failures_count": execution_meta.get("provider_failures", 0),
                "timeout_count": execution_meta.get("timed_out_units_count", 0),
                "cache_hits": execution_meta.get("cache_hits", 0),
                "cache_misses": execution_meta.get("cache_misses", 0),
                "final_results_count": len(scoped_ranked_results),
            },
            "filters_engine": {
                "strict_mode_effective": strict_filters,
                "unsupported_filters_ignored": [
                    item["meta"].get("filter")
                    for item in warnings_structured
                    if item.get("code") in {"unsupported_filter", "provider_missing_field_for_filter"}
                ],
                "hard_filters_applied": ["exclude_origins", "exclude_destinations", "departure_window"],
                "soft_filters_applied": ["seed_distance_penalty", "pair_category_bias", "soft_filters_weight"],
            },
            "provider_status": provider_status,
            "warnings_structured": warnings_structured,
            "ranking": {
                "version": "quick_ranking.v1",
                "signals": [
                    "price_component",
                    "origin_seed_penalty",
                    "destination_seed_penalty",
                    "distance_penalty_total",
                    "pair_category",
                ],
                "tie_breakers": [
                    "final_score",
                    "price",
                    "distance_penalty_total",
                    "travel_date",
                    "departure_time_local",
                ],
                "dedupe": deduped.meta,
            },
            "debug": debug_payload,

        },
        "filters": {
            "applied": filters_applied,
            "relaxed": relaxed_filters,
            "warnings": warnings,
            "discarded": max(0, len(combined) - len(flights_after_filters)) + out_of_scope_discarded,
        },
        "results": [
            {
                "result_id": f"{item.origin}-{item.destination}-{item.travel_date}-{idx}",
                "origin": item.origin,
                "destination": item.destination,
                "travel_date": str(item.travel_date),
                "departure_time_local": item.flight.departure_time_local,
                "price": item.flight.price,
                "price_total": item.flight.price,
                "currency": item.flight.currency,
                "source": item.flight.source,
                "duration_total_min": _estimate_duration_minutes(item.origin, item.destination),
                "risk_label": _risk_label_from_pair_category(item.pair_category),
                "ranking_score": item.final_score,
                "stale_data": False,
                "freshness_ts": item.flight.captured_at.isoformat(),
                "itinerary_type": "direct",
                "legs": [],
                "score": item.score_breakdown,
                "origin_seed_iata": item.origin_seed_iata,
                "destination_seed_iata": item.destination_seed_iata,
                "origin_iata_used": item.origin,
                "destination_iata_used": item.destination,
                "origin_is_seed": item.origin_is_seed,
                "destination_is_seed": item.destination_is_seed,
                "origin_distance_from_seed_km": item.origin_distance_from_seed_km,
                "destination_distance_from_seed_km": item.destination_distance_from_seed_km,
                "pair_category": item.pair_category,
                "discovery_explanation": item.discovery_explanation,
                "query_trace_id": query_trace_id,
                "selected_from_pair_id": f"{item.origin}->{item.destination}",
                "candidate_reason": "seed" if item.origin_is_seed and item.destination_is_seed else "expanded",
            }
            for idx, item in enumerate(scoped_ranked_results)
        ],
    }
