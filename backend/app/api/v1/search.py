import datetime as dt
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.core.errors import ApiError, message_for_code
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.api.v1.airports import _validate_iata
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider
from app.services.quick_search_execution import build_execution_plan, execute_plan
from app.services.quick_search_expansion import expand_search_sides
from app.services.quick_search_planner import build_pair_plan
from app.services.quick_search_ranking import rank_quick_search_results

router = APIRouter()
provider = RyanairPublicProvider()


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
    include_nearby: bool = False
    radius_km: int = Field(default=150, ge=10, le=500)
    max_candidates: int = Field(default=6, ge=1, le=20)

    @field_validator("seed_iata")
    @classmethod
    def validate_seed_iata(cls, value: str) -> str:
        return _validate_iata(value)


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
    soft_filters_weight: float | None = None


class QuickSearchExecution(BaseModel):
    max_pairs: int = Field(default=12, ge=1, le=200)
    max_requests: int = Field(default=120, ge=1, le=1000)
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

        canonical_dict = {
            "origin": {
                "seed_iata": origin_value,
                "include_nearby": (
                    query_overrides.get("include_nearby_origins")
                    if query_overrides.get("include_nearby_origins") is not None
                    else legacy_payload.include_nearby_origins
                    if legacy_payload.include_nearby_origins is not None
                    else legacy_payload.include_nearby_origin
                    if legacy_payload.include_nearby_origin is not None
                    else False
                ),
                "radius_km": (
                    query_overrides.get("radius_km")
                    if query_overrides.get("radius_km") is not None
                    else legacy_payload.radius_km
                    if legacy_payload.radius_km is not None
                    else 150
                ),
                "max_candidates": 6,
            },
            "destination": {
                "seed_iata": destination_value,
                "include_nearby": (
                    query_overrides.get("include_nearby_destinations")
                    if query_overrides.get("include_nearby_destinations") is not None
                    else legacy_payload.include_nearby_destinations
                    if legacy_payload.include_nearby_destinations is not None
                    else legacy_payload.include_nearby_destination
                    if legacy_payload.include_nearby_destination is not None
                    else False
                ),
                "radius_km": (
                    query_overrides.get("radius_km")
                    if query_overrides.get("radius_km") is not None
                    else legacy_payload.radius_km
                    if legacy_payload.radius_km is not None
                    else 150
                ),
                "max_candidates": 6,
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
                "soft_filters_weight": (
                    query_overrides.get("soft_filters_weight")
                    if query_overrides.get("soft_filters_weight") is not None
                    else legacy_payload.soft_filters_weight
                ),
            },
            "execution": {
                "max_pairs": 12,
                "max_requests": 120,
                "timeout_ms": 8000,
            },
        }

    try:
        canonical = QuickSearchCanonicalRequest.model_validate(canonical_dict)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    origin_list = _parse_iata_input(canonical.origin.seed_iata)
    destination_list = _parse_iata_input(canonical.destination.seed_iata)

    filter_support = {
        "supported": ["strict_filters", "departure_window", "exclude_origins", "exclude_destinations"],
        "legacy_partial": ["include_stops", "max_stops", "soft_filters_weight"],
        "pending": ["stop-logic", "soft-ranking-weight"],
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
    origin = _validate_iata(origin_iata)
    destination = _validate_iata(destination_iata)
    if adults < 1 or adults > 9:
        raise HTTPException(status_code=400, detail="adultos_invalidos")
    if date_in and date_in < date_out:
        raise HTTPException(status_code=400, detail="fecha_vuelta_invalida")

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
) -> dict:
    canonical, origin_list, destination_list, filter_contract = _normalize_quick_search_request(
        payload,
        {
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
        },
    )

    travel_date_value = canonical.travel.date
    days_before = canonical.travel.flex_before
    days_after = canonical.travel.flex_after

    include_nearby_origins = canonical.origin.include_nearby
    include_nearby_destinations = canonical.destination.include_nearby
    radius_km_origin = canonical.origin.radius_km
    radius_km_destination = canonical.destination.radius_km

    depart_after = canonical.constraints.departure_window.after if canonical.constraints.departure_window else None
    depart_before = canonical.constraints.departure_window.before if canonical.constraints.departure_window else None
    strict_filters = canonical.constraints.strict_filters
    include_stops = bool(canonical.constraints.include_stops)
    max_stops = canonical.constraints.max_stops or 0
    soft_filters_weight = canonical.constraints.soft_filters_weight if canonical.constraints.soft_filters_weight is not None else 0.6

    max_pairs = canonical.execution.max_pairs

    warnings: list[str] = []
    filters_applied: dict[str, Any] = {}
    relaxed_filters: list[str] = []

    if canonical.execution.timeout_ms != 8000:
        warnings.append("timeout_ms_not_yet_enforced_at_provider_level")

    if max_stops > 0:
        warnings.append("stops_no_disponible_en_modo_rapido")

    exclude_origin_list = canonical.constraints.exclude_origins
    exclude_destination_list = canonical.constraints.exclude_destinations

    # Expansion phase (explicit + side-independent)
    try:
        origin_side, destination_side = expand_search_sides(
            origin_seed_iata=canonical.origin.seed_iata,
            destination_seed_iata=canonical.destination.seed_iata,
            include_nearby_origins=include_nearby_origins,
            include_nearby_destinations=include_nearby_destinations,
            origin_radius_km=radius_km_origin,
            destination_radius_km=radius_km_destination,
            origin_max_candidates=canonical.origin.max_candidates,
            destination_max_candidates=canonical.destination.max_candidates,
            exclude_origins=exclude_origin_list,
            exclude_destinations=exclude_destination_list,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    origin_expanded = origin_side.candidates
    destination_expanded = destination_side.candidates

    origin_candidates = [candidate.expanded_iata for candidate in origin_expanded]
    destination_candidates = [candidate.expanded_iata for candidate in destination_expanded]

    date_candidates = _build_flex_dates(travel_date_value, days_before, days_after)
    pair_plan, pair_plan_stats = build_pair_plan(
        origin_expanded,
        destination_expanded,
        max_pairs=max_pairs,
        max_requests=canonical.execution.max_requests,
        date_count=len(date_candidates),
    )
    if pair_plan_stats["truncated"]:
        warnings.append("limite_combinaciones_alternativas")

    execution_plan = build_execution_plan(
        pair_plan,
        date_candidates,
        max_requests=canonical.execution.max_requests,
    )

    combined, execution_meta, execution_warnings = execute_plan(
        execution_plan,
        concurrency_limit=canonical.execution.concurrency_limit,
        timeout_ms=canonical.execution.timeout_ms,
        fetch_flights=lambda o, d, date_str, timeout: provider.get_flights(o, d, date_str, timeout_ms=timeout),
    )
    pair_count = len(pair_plan)
    warnings.extend(execution_warnings)

    filtered = [
        (origin_code, destination_code, travel_date_item, flight)
        for origin_code, destination_code, travel_date_item, flight in combined
        if _matches_time_window(flight.departure_time_local, depart_after, depart_before)
    ]
    if depart_after or depart_before:
        filters_applied["departure_window"] = {"after": depart_after, "before": depart_before}

    if strict_filters:
        flights_after_filters = filtered
    else:
        flights_after_filters = filtered
        if not flights_after_filters and (depart_after or depart_before):
            flights_after_filters = combined
            relaxed_filters.append("departure_window")

    ranked_results = rank_quick_search_results(flights_after_filters, pair_plan)

    return {
        "query": {
            "origin": canonical.origin.model_dump(),
            "destination": canonical.destination.model_dump(),
            "travel": {
                "date": str(travel_date_value),
                "flex_before": days_before,
                "flex_after": days_after,
                "travel_dates": [str(date_item) for date_item in date_candidates],
            },
            "constraints": {
                "departure_window": {"after": depart_after, "before": depart_before},
                "exclude_origins": exclude_origin_list,
                "exclude_destinations": exclude_destination_list,
                "strict_filters": strict_filters,
                "include_stops": include_stops,
                "max_stops": max_stops,
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
            "contract_version": "quick_search.v2",
            "legacy_aliases_used": filter_contract["aliases"],
            "filter_support": {
                "supported": filter_contract["supported"],
                "legacy_partial": filter_contract["legacy_partial"],
                "pending": filter_contract["pending"],
            },
            "pair_counts": {
                "evaluated": pair_count,
                "total_pairs": pair_plan_stats["total_pairs"],
                "selected_pairs": pair_plan_stats["selected_pairs"],
                "truncated": pair_plan_stats["truncated"],
                "max_pairs": max_pairs,
                "max_pairs_by_requests": pair_plan_stats["max_pairs_by_requests"],
                "max_pairs_scope": "base_pairs_only",
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
            },
        },
        "filters": {
            "applied": filters_applied,
            "relaxed": relaxed_filters,
            "warnings": warnings,
            "discarded": max(0, len(combined) - len(flights_after_filters)),
        },
        "results": [
            {
                "origin": item.origin,
                "destination": item.destination,
                "travel_date": str(item.travel_date),
                "departure_time_local": item.flight.departure_time_local,
                "price": item.flight.price,
                "currency": item.flight.currency,
                "source": item.flight.source,
                "score": item.score_breakdown,
            }
            for item in ranked_results
        ],
    }
