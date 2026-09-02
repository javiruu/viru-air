import calendar as calendar_lib
import datetime as dt
import hashlib
import json
import logging
import math
import statistics
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Literal, TypedDict

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.errors import ApiError, message_for_code
from app.core.idempotency import replay_if_exists, request_hash, store_response
from app.core.time import utc_now_naive
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.api.deps import get_current_user
from app.api.v1.airports import _validate_iata
from app.domain.entities import ProviderFetchResult
from app.domain.schemas import FareComparisonProfile
from app.infrastructure.db.models import FareComparisonExtraData, FareComparisonProfileData, FlightWatch, PriceSnapshot, User
from app.infrastructure.db.session import get_db, SessionLocal
from app.infrastructure.airports_catalog import ExpandedAirportCandidate, get_airport, resolve_seed_airport
from app.infrastructure.providers.flight_provider import MultiSourceFlightProvider
from app.services.quick_search_dedupe import dedupe_ranked_results
from app.services.quick_search_execution import (
    build_cache_source_hash,
    classify_cache_result,
    build_execution_plan,
    execute_plan,
)
from app.services.quick_search_expansion import SideExpansionResult, SideExpansionSummary, expand_search_sides
from app.services.quick_search_planner import PairPlanItem, build_pair_plan
from app.services.quick_search_ai_preference import select_quick_search_ai_preference
from app.services.quick_search_ranking import rank_quick_search_results
from app.services.quick_search_warning_codes import (
    PROVIDER_OUTAGE_WARNING_CODES,
    PROVIDER_TOTAL_OUTAGE_CODES,
    PROVIDER_WARNING_CODES,
    UI_WARNING_CRITICAL_CODES,
    UI_WARNING_PARTIAL_CODES,
    normalize_warning_code,
)
from app.services.fare_memory_config import (
    FARE_MEMORY_NEGATIVE_CACHE_ENABLED,
    FARE_MEMORY_OFFER_CACHE_ENABLED,
    FARE_MEMORY_SEARCH_CACHE_ENABLED,
)
from app.services.fare_memory_logging import log_fare_memory_quick_search_counters
from app.services.quick_search_legacy_compatibility import enforce_quick_search_legacy_alias_policy
from app.services.quick_search_cache_service import (
    build_effective_freshness,
    build_negative_cache_fingerprint,
    deserialize_fetch_result,
    deserialize_exact_search_payload,
    get_exact_search_cache_entry,
    get_fresh_entry,
    get_fresh_negative_cache_entry,
    resolve_negative_cache_result,
    serialize_fetch_result,
    set_negative_cache_entry,
    set_exact_search_cache_entry,
    set_cache_entry,
    prune_expired_entries_async,
)
from app.services.quick_search_negative_cache_write_policy import resolve_negative_cache_write_policy
from app.services.quick_search_popularity import QuickSearchPopularitySignal, record_quick_search_popularity
from app.services.quick_search_provider_singleflight import (
    acquire_quick_search_provider_lock,
    release_quick_search_provider_lock,
)
from app.services.fare_memory import build_freshness_payload, build_search_fingerprint
from app.services.fare_memory_provider_observations import ObservationPersistenceContext, persist_provider_flight_observations
from app.services.quick_search_save_result_observation import handle_saved_result_observation
from app.services.live_flight_tracking import replace_watch_tracked_legs
from app.services.calendar_price_intelligence import (
    CalendarComparableObservation,
    build_calendar_query_fingerprint,
    build_calendar_reference_fingerprint,
    classify_contextual_price,
    convert_calendar_price,
    load_fresh_calendar_reference,
    load_latest_calendar_days,
    record_calendar_prices,
)

router = APIRouter()
logger = logging.getLogger(__name__)
SEED_POOL_CAP = 8
QUICK_SEARCH_MAX_PAIRS_CAP = 400
QUICK_SEARCH_MAX_REQUESTS_CAP = 3000
QUICK_SEARCH_SHARED_CACHE_ENABLED = os.getenv("QUICK_SEARCH_SHARED_CACHE_ENABLED", "false").strip().lower() == "true"
CALENDAR_HINTS_CACHE_TTL_SECONDS = 600
CALENDAR_HINTS_CACHE_MAX_SIZE = 500
_CALENDAR_HINTS_CACHE_LOCK = threading.Lock()
_CALENDAR_HINTS_CACHE: dict[tuple[object, ...], tuple[float, dict[str, Any]]] = {}
CALENDAR_HINTS_GUIDELINE_DEFAULT_LOW_MAX = 90.0
CALENDAR_HINTS_GUIDELINE_DEFAULT_MID_MAX = 150.0

SharedCacheGet = Callable[[str, str, dt.date | str, str], ProviderFetchResult | None]
SharedCacheSet = Callable[[str, str, dt.date | str, str, ProviderFetchResult], None]
ProviderSingleFlightAcquire = Callable[[str, str, dt.date | str, str], str | None]
ProviderSingleFlightRelease = Callable[[str], None]


class QuickSearchSeedPoolContract(TypedDict):
    cap: int
    origin_requested_count: int
    destination_requested_count: int
    origin_requested_iata: list[str]
    destination_requested_iata: list[str]
    origin_count: int
    destination_count: int
    origin_effective_iata: list[str]
    destination_effective_iata: list[str]
    origin_truncated: bool
    destination_truncated: bool


class QuickSearchFilterContract(TypedDict):
    aliases: list[str]
    hard_supported: list[str]
    soft_supported: list[str]
    unsupported: list[str]
    legacy_partial: list[str]
    pending: list[str]
    seed_pool: QuickSearchSeedPoolContract


@dataclass(frozen=True, slots=True)
class FareMemoryCacheCallbacks:
    shared_cache_get: SharedCacheGet | None
    shared_cache_set: SharedCacheSet | None
    negative_cache_get: SharedCacheGet | None
    negative_cache_set: SharedCacheSet | None
    provider_singleflight_acquire: ProviderSingleFlightAcquire | None
    provider_singleflight_release: ProviderSingleFlightRelease | None


def _build_request_provider() -> MultiSourceFlightProvider:
    return MultiSourceFlightProvider()


def _provider_cache_id(provider_ids: list[str]) -> str:
    cleaned = [item.strip().lower() for item in provider_ids if item.strip()]
    return "multi:" + ",".join(cleaned or ["none"])

def _supports_db_session(value: Any) -> bool:
    return all(hasattr(value, attr) for attr in ("scalar", "add", "commit"))


def _normalize_warning_code(code: str) -> str:
    return normalize_warning_code(code)


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


def _filter_ui_warning_codes(codes: list[str]) -> list[str]:
    """
    Policy for the `/quick-search` information rail:
    expose only critical/provider-partial degradation warnings.
    Keep full warning telemetry in `meta.warnings_structured`.
    """
    visible: list[str] = []
    for raw_code in codes:
        code = _normalize_warning_code(raw_code)
        if (code in UI_WARNING_CRITICAL_CODES or code in UI_WARNING_PARTIAL_CODES) and code not in visible:
            visible.append(code)
    return visible


def _build_fare_memory_cache_callbacks(*, shared_cache_enabled: bool, user_currency: str) -> FareMemoryCacheCallbacks:
    if not shared_cache_enabled:
        return FareMemoryCacheCallbacks(
            shared_cache_get=None,
            shared_cache_set=None,
            negative_cache_get=None,
            negative_cache_set=None,
            provider_singleflight_acquire=None,
            provider_singleflight_release=None,
        )

    def _shared_get(o: str, d: str, date: dt.date | str, prov: str) -> ProviderFetchResult | None:
        with SessionLocal() as cache_db:
            entry = get_fresh_entry(
                cache_db,
                origin_iata=o,
                destination_iata=d,
                travel_date=date,
                provider=prov,
                source_hash=build_cache_source_hash(
                    origin_iata=o,
                    destination_iata=d,
                    travel_date=date,
                    provider=prov,
                    currency=user_currency,
                ),
            )
            if entry is None:
                return None
            return deserialize_fetch_result(entry.payload_json, entry.warnings_json)

    def _shared_set(o: str, d: str, date: dt.date | str, prov: str, result: ProviderFetchResult) -> None:
        with SessionLocal() as cache_db:
            payload_json, warnings_json = serialize_fetch_result(result)
            set_cache_entry(
                cache_db,
                origin_iata=o,
                destination_iata=d,
                travel_date=date,
                provider=prov,
                source_hash=build_cache_source_hash(
                    origin_iata=o,
                    destination_iata=d,
                    travel_date=date,
                    provider=prov,
                    currency=user_currency,
                ),
                category=classify_cache_result(
                    flights=result.flights,
                    warnings=result.warnings,
                ),
                payload_json=payload_json,
                warnings_json=warnings_json,
            )

    def _provider_singleflight_acquire(o: str, d: str, date: dt.date | str, prov: str) -> str | None:
        with SessionLocal() as cache_db:
            lease = acquire_quick_search_provider_lock(
                cache_db,
                origin_iata=o,
                destination_iata=d,
                travel_date=date,
                provider=prov,
                currency=user_currency,
            )
            return lease.lock_token if lease is not None else None

    def _provider_singleflight_release(lock_token: str) -> None:
        with SessionLocal() as cache_db:
            release_quick_search_provider_lock(cache_db, lock_token=lock_token)

    negative_cache_get = None
    negative_cache_set = None
    if FARE_MEMORY_NEGATIVE_CACHE_ENABLED:
        def _negative_get(o: str, d: str, date: dt.date | str, prov: str) -> ProviderFetchResult | None:
            with SessionLocal() as cache_db:
                fingerprint = build_negative_cache_fingerprint(
                    origin_iata=o,
                    destination_iata=d,
                    travel_date=date,
                    provider=prov,
                    currency=user_currency,
                )
                entry = get_fresh_negative_cache_entry(
                    cache_db,
                    negative_fingerprint=fingerprint,
                )
                if entry is None:
                    return None
                return resolve_negative_cache_result(entry)

        def _negative_set(o: str, d: str, date: dt.date | str, prov: str, result: ProviderFetchResult) -> None:
            reason, retry_after_at = resolve_negative_cache_write_policy(result)
            with SessionLocal() as cache_db:
                set_negative_cache_entry(
                    cache_db,
                    negative_fingerprint=build_negative_cache_fingerprint(
                        origin_iata=o,
                        destination_iata=d,
                        travel_date=date,
                        provider=prov,
                        currency=user_currency,
                    ),
                    scope="route_date_provider",
                    reason=reason,
                    provider=prov,
                    canonical_request_json=json.dumps(
                        {
                            "origin_iata": o,
                            "destination_iata": d,
                            "travel_date": str(date),
                            "provider": prov,
                            "currency": user_currency,
                        },
                        ensure_ascii=False,
                    ),
                    retry_after_at=retry_after_at,
                )

        negative_cache_get = _negative_get
        negative_cache_set = _negative_set

    return FareMemoryCacheCallbacks(
        shared_cache_get=_shared_get,
        shared_cache_set=_shared_set,
        negative_cache_get=negative_cache_get,
        negative_cache_set=negative_cache_set,
        provider_singleflight_acquire=_provider_singleflight_acquire,
        provider_singleflight_release=_provider_singleflight_release,
    )


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _metric_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _to_optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _collect_result_freshness_metrics(results: list[dict[str, Any]]) -> tuple[int, float]:
    stale_served_count = 0
    age_samples: list[float] = []

    for item in results:
        freshness = item.get("freshness")
        if not isinstance(freshness, dict):
            continue
        if (
            bool(item.get("stale_data"))
            or bool(freshness.get("requires_revalidation"))
            or freshness.get("status") in {"warm", "stale"}
        ):
            stale_served_count += 1
        age_seconds = _to_optional_float(freshness.get("age_seconds"))
        if age_seconds is not None:
            age_samples.append(age_seconds)

    avg_price_age_seconds = round(sum(age_samples) / len(age_samples), 2) if age_samples else 0.0
    return stale_served_count, avg_price_age_seconds


def _combine_execution_cache_counters(*metas: dict[str, Any]) -> dict[str, int]:
    keys = (
        "provider_calls",
        "cache_hits",
        "cache_misses",
        "l1_cache_hits",
        "l2_cache_hits",
        "negative_cache_hits",
        "provider_failures",
        "timed_out_units_count",
    )
    combined: dict[str, int] = {}
    for key in keys:
        combined[key] = sum(int(meta.get(key, 0) or 0) for meta in metas)
    combined["provider_calls_avoided"] = combined["cache_hits"]
    return combined


def _enrich_pipeline_counters(response_payload: dict[str, Any]) -> None:
    meta = response_payload.setdefault("meta", {})
    execution_meta = meta.setdefault("execution", {})
    pipeline_counters = meta.setdefault("pipeline_counters", {})
    results = [item for item in response_payload.get("results", []) if isinstance(item, dict)]
    search_cache = meta.get("search_cache")
    exact_search_cache_hit = bool(isinstance(search_cache, dict) and search_cache.get("exact_hit"))
    provider_status = meta.get("provider_status")
    provider_status_items = (
        provider_status.get("providers", [])
        if isinstance(provider_status, dict) and isinstance(provider_status.get("providers"), list)
        else []
    )
    provider_status_error_count = sum(
        int(item.get("errors", 0) or 0) + int(item.get("timeouts", 0) or 0)
        for item in provider_status_items
        if isinstance(item, dict)
    )

    cache_hits = int(execution_meta.get("cache_hits", pipeline_counters.get("cache_hits", 0)) or 0)
    if exact_search_cache_hit and cache_hits < 1:
        cache_hits = 1
        execution_meta["cache_hits"] = 1
    cache_misses = int(execution_meta.get("cache_misses", pipeline_counters.get("cache_misses", 0)) or 0)
    l1_cache_hits = int(execution_meta.get("l1_cache_hits", pipeline_counters.get("l1_cache_hits", 0)) or 0)
    l2_cache_hits = int(execution_meta.get("l2_cache_hits", pipeline_counters.get("l2_cache_hits", 0)) or 0)
    negative_cache_hits = int(
        execution_meta.get("negative_cache_hits", pipeline_counters.get("negative_cache_hits", 0)) or 0
    )
    provider_calls = int(execution_meta.get("provider_calls", 0) or 0)
    provider_failures = max(
        int(execution_meta.get("provider_failures", pipeline_counters.get("provider_failures_count", 0)) or 0),
        provider_status_error_count,
    )
    stale_served_count, avg_price_age_seconds = _collect_result_freshness_metrics(results)
    total_cache_lookups = cache_hits + cache_misses
    provider_error_denominator = max(provider_calls, provider_failures)

    pipeline_counters.update(
        {
            "provider_calls": provider_calls,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "l1_cache_hits": l1_cache_hits,
            "l2_cache_hits": l2_cache_hits,
            "negative_cache_hits": negative_cache_hits,
            "provider_failures_count": provider_failures,
            "final_results_count": int(pipeline_counters.get("final_results_count", len(results)) or len(results)),
            "paginated_results_count": int(
                pipeline_counters.get("paginated_results_count", len(results)) or len(results)
            ),
            "cache_hit_rate": _metric_ratio(cache_hits, total_cache_lookups),
            "cache_miss_rate": _metric_ratio(cache_misses, total_cache_lookups),
            "negative_cache_hit_rate": _metric_ratio(negative_cache_hits, total_cache_lookups),
            "provider_calls_avoided": cache_hits,
            "stale_served_count": stale_served_count,
            "avg_price_age_seconds": avg_price_age_seconds,
            "provider_error_rate": _metric_ratio(provider_failures, provider_error_denominator),
        }
    )


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


def _build_live_tracking_legs(item: Any) -> list[dict[str, Any]]:
    flight_number = (item.flight.flight_number or "").strip().upper()
    departure_clock = (item.flight.departure_time_local or "").strip()
    if not flight_number or not departure_clock:
        return []
    try:
        travel_date = (
            item.travel_date
            if isinstance(item.travel_date, dt.date)
            else dt.date.fromisoformat(str(item.travel_date))
        )
        departure_time = dt.time.fromisoformat(departure_clock)
        departure_at = dt.datetime.combine(travel_date, departure_time)
    except (TypeError, ValueError):
        return []
    return [
        {
            "origin_iata": item.origin,
            "destination_iata": item.destination,
            "dep_ts": departure_at.isoformat(),
            "arr_ts": None,
            "flight_num": flight_number,
            "carrier_code": item.flight.carrier_code,
        }
    ]


def _sort_quick_search_results(results: list[Any], sort_by: str) -> list[Any]:
    if sort_by == "price":
        return sorted(
            results,
            key=lambda item: (
                item.price_value is None,
                float(item.price_value) if item.price_value is not None else math.inf,
                -float(item.final_score or 0),
                str(item.travel_date),
                item.flight.departure_time_local or "",
            ),
        )
    if sort_by == "duration":
        return sorted(
            results,
            key=lambda item: (
                _estimate_duration_minutes(item.origin, item.destination) is None,
                _estimate_duration_minutes(item.origin, item.destination) or math.inf,
                float(item.price_value) if item.price_value is not None else math.inf,
                -float(item.final_score or 0),
                str(item.travel_date),
            ),
        )
    if sort_by == "freshness":
        return sorted(
            results,
            key=lambda item: (
                -item.flight.captured_at.timestamp(),
                float(item.price_value) if item.price_value is not None else math.inf,
                -float(item.final_score or 0),
                str(item.travel_date),
            ),
        )
    return list(results)


class QuickSearchPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    origin_iata: str | list[str] | None = None
    destination_iata: str | list[str] | None = None
    travel_date: dt.date | None = None
    date: dt.date | None = None
    travel_dates: list[dt.date] | None = None
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
    exclude_origins: str | list[str] | None = None
    exclude_destinations: str | list[str] | None = None
    strict_filters: bool | None = None
    strict_mode: bool | None = None
    soft_filters_weight: float | None = None
    flex_days_before: int | None = None
    flex_days_after: int | None = None
    dias_antes: int | None = None
    dias_despues: int | None = None
    sort_by: Literal["ranking", "price", "duration", "freshness"] | None = None


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
    dates: list[dt.date] = Field(default_factory=list, max_length=15)

    @model_validator(mode="after")
    def normalize_exact_dates(self) -> "QuickSearchTravel":
        if self.dates and (self.flex_before or self.flex_after):
            raise ValueError("exact_dates_incompatible_with_flexibility")
        self.dates = sorted(set(self.dates))
        return self


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
    soft_filters_weight: float | None = None


class QuickSearchExecution(BaseModel):
    max_pairs: int = Field(default=48, ge=1, le=QUICK_SEARCH_MAX_PAIRS_CAP)
    max_requests: int = Field(default=480, ge=1, le=QUICK_SEARCH_MAX_REQUESTS_CAP)
    timeout_ms: int = Field(default=8000, ge=1000, le=30000)
    concurrency_limit: int = Field(default=6, ge=1, le=32)


class QuickSearchPagination(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: Literal["ranking", "price", "duration", "freshness"] = "ranking"


class QuickSearchCanonicalRequest(BaseModel):
    origin: QuickSearchSide
    destination: QuickSearchSide
    travel: QuickSearchTravel
    constraints: QuickSearchConstraints = Field(default_factory=QuickSearchConstraints)
    execution: QuickSearchExecution = Field(default_factory=QuickSearchExecution)
    pagination: QuickSearchPagination = Field(default_factory=QuickSearchPagination)


class QuickSearchSaveLegIn(BaseModel):
    flight_number: str | None = Field(default=None, max_length=32)
    carrier_code: str | None = Field(default=None, max_length=16)
    origin_iata: str = Field(min_length=3, max_length=3)
    destination_iata: str = Field(min_length=3, max_length=3)
    departure_at: dt.datetime | None = None
    arrival_at: dt.datetime | None = None

    @field_validator("origin_iata", "destination_iata")
    @classmethod
    def validate_leg_iata(cls, value: str) -> str:
        return _validate_iata(value)

    @field_validator("flight_number", "carrier_code")
    @classmethod
    def normalize_leg_identity(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class QuickSearchSaveResultIn(BaseModel):
    origin_iata: str = Field(min_length=3, max_length=3)
    destination_iata: str = Field(min_length=3, max_length=3)
    travel_date: dt.date
    price_total: float | None = Field(default=None, ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    freshness_status: str | None = Field(default=None, max_length=40)
    requires_revalidation: bool | None = None
    validation_status: str | None = Field(default=None, max_length=40)
    group_id: str | None = Field(default=None, max_length=36)
    fare_profile: FareComparisonProfile | None = None
    legs: list[QuickSearchSaveLegIn] | None = Field(default=None, max_length=8)

    @field_validator("origin_iata", "destination_iata")
    @classmethod
    def validate_save_iata(cls, value: str) -> str:
        return _validate_iata(value)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return str(value).upper().strip()

    @model_validator(mode="after")
    def validate_tracking_leg_chain(self):
        if not self.legs:
            return self
        if self.legs[0].origin_iata != self.origin_iata:
            raise ValueError("tracking legs must start at the saved route origin")
        if self.legs[-1].destination_iata != self.destination_iata:
            raise ValueError("tracking legs must end at the saved route destination")
        for current, following in zip(self.legs, self.legs[1:], strict=False):
            if current.destination_iata != following.origin_iata:
                raise ValueError("tracking legs must form a continuous route")
        first_departure = self.legs[0].departure_at
        if first_departure is not None and first_departure.date() != self.travel_date:
            raise ValueError("first tracking leg must depart on the saved travel date")
        return self


class QuickSearchGuidelineThresholdsIn(BaseModel):
    low_max: float = Field(ge=0)
    mid_max: float = Field(gt=0)
    currency: Literal["EUR", "USD", "GBP"] = "EUR"

    @model_validator(mode="after")
    def validate_order(self):
        if self.mid_max <= self.low_max:
            raise ValueError("guideline_mid_max_invalid")
        return self


class QuickSearchCalendarHintsIn(BaseModel):
    origin_iata: str | list[str]
    destination_iata: str | list[str]
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    adults: int = Field(default=1, ge=1, le=9)
    currency: Literal["EUR", "USD", "GBP"] = "EUR"
    leg: Literal["outbound", "return"] = "outbound"
    cabin: Literal["economy"] = "economy"
    aggregation_mode: Literal["min", "median", "fixed_route"] = "min"
    bucket_mode: Literal["contextual", "monthly_terciles", "guidelines"] = "contextual"
    guideline_thresholds: QuickSearchGuidelineThresholdsIn | None = None

    @field_validator("origin_iata", "destination_iata", mode="before")
    @classmethod
    def validate_iata_scope(cls, value: str | list[str]) -> str | list[str]:
        if isinstance(value, list):
            if not value:
                raise ValueError("iata_scope_empty")
            return [_validate_iata(str(item)) for item in value]
        return _validate_iata(str(value))

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        if not re.match(r"^\d{4}-\d{2}$", value):
            raise ValueError("month_must_match_yyyy_mm")
        try:
            dt.date.fromisoformat(f"{value}-01")
        except ValueError as exc:
            raise ValueError("month_invalid") from exc
        return value


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


def _build_month_dates(month_iso: str) -> list[dt.date]:
    year, month = month_iso.split("-")
    year_int = int(year)
    month_int = int(month)
    total_days = calendar_lib.monthrange(year_int, month_int)[1]
    return [dt.date(year_int, month_int, day) for day in range(1, total_days + 1)]


def _bucketize_day_prices_terciles(day_min_prices: dict[dt.date, float]) -> dict[dt.date, str]:
    if not day_min_prices:
        return {}

    sorted_values = sorted(day_min_prices.values())
    total_values = len(sorted_values)
    if total_values == 1:
        only_day = next(iter(day_min_prices.keys()))
        return {only_day: "low"}
    if total_values == 2:
        ordered_days = sorted(day_min_prices.items(), key=lambda item: (item[1], item[0].isoformat()))
        return {
            ordered_days[0][0]: "low",
            ordered_days[1][0]: "high" if ordered_days[1][1] > ordered_days[0][1] else "low",
        }

    low_index = max(0, math.ceil(total_values / 3) - 1)
    mid_index = max(0, math.ceil((2 * total_values) / 3) - 1)
    low_threshold = sorted_values[low_index]
    mid_threshold = sorted_values[mid_index]

    buckets: dict[dt.date, str] = {}
    for day, price in day_min_prices.items():
        if price <= low_threshold:
            buckets[day] = "low"
        elif price <= mid_threshold:
            buckets[day] = "mid"
        else:
            buckets[day] = "high"
    return buckets


def _bucketize_day_prices_guidelines(
    day_min_prices: dict[dt.date, float],
    *,
    low_max: float,
    mid_max: float,
) -> dict[dt.date, str]:
    buckets: dict[dt.date, str] = {}
    for day, price in day_min_prices.items():
        if price <= low_max:
            buckets[day] = "low"
        elif price <= mid_max:
            buckets[day] = "mid"
        else:
            buckets[day] = "high"
    return buckets


def _resolve_guideline_thresholds(
    payload: QuickSearchCalendarHintsIn,
    *,
    target_currency: str,
) -> dict[str, Any] | None:
    if payload.bucket_mode != "guidelines":
        return None
    thresholds = payload.guideline_thresholds
    if thresholds is None:
        low_max = CALENDAR_HINTS_GUIDELINE_DEFAULT_LOW_MAX
        mid_max = CALENDAR_HINTS_GUIDELINE_DEFAULT_MID_MAX
        currency = "EUR"
    else:
        low_max = float(thresholds.low_max)
        mid_max = float(thresholds.mid_max)
        currency = str(thresholds.currency).strip().upper()
    if low_max < 0:
        low_max = 0.0
    if mid_max <= low_max:
        mid_max = max(low_max + 1.0, CALENDAR_HINTS_GUIDELINE_DEFAULT_MID_MAX)
    if currency not in {"EUR", "USD", "GBP"}:
        currency = "EUR"
    normalized_low_max = convert_calendar_price(low_max, currency, target_currency)
    normalized_mid_max = convert_calendar_price(mid_max, currency, target_currency)
    if normalized_low_max is None or normalized_mid_max is None:
        return None
    return {
        "low_max": normalized_low_max,
        "mid_max": normalized_mid_max,
        "currency": target_currency,
    }


def _bucketize_day_prices_by_mode(
    day_min_prices: dict[dt.date, float],
    *,
    bucket_mode: Literal["contextual", "monthly_terciles", "guidelines"],
    guideline_thresholds: dict[str, Any] | None,
) -> dict[dt.date, str]:
    if bucket_mode == "guidelines" and guideline_thresholds:
        return _bucketize_day_prices_guidelines(
            day_min_prices,
            low_max=float(guideline_thresholds["low_max"]),
            mid_max=float(guideline_thresholds["mid_max"]),
        )
    return _bucketize_day_prices_terciles(day_min_prices)


def _normalize_calendar_hint_iata_pool(value: str | list[str]) -> list[str]:
    raw_items = [value] if isinstance(value, str) else list(value)
    deduped: list[str] = []
    seen: set[str] = set()
    for raw in raw_items:
        code = _validate_iata(str(raw))
        try:
            resolve_seed_airport(code)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if code in seen:
            continue
        seen.add(code)
        deduped.append(code)
    if not deduped:
        raise HTTPException(status_code=422, detail="iata_scope_empty")
    return deduped


def _resolve_calendar_scope_mode(origin_pool: list[str], destination_pool: list[str]) -> str:
    origin_country_scope = len(origin_pool) > 1
    destination_country_scope = len(destination_pool) > 1
    if origin_country_scope and destination_country_scope:
        return "country_country"
    if origin_country_scope or destination_country_scope:
        return "country_mixed"
    return "iata"


def _build_calendar_scope_signature(origin_pool: list[str], destination_pool: list[str]) -> str:
    origin_key = ",".join(sorted(origin_pool))
    destination_key = ",".join(sorted(destination_pool))
    return f"o:{origin_key}|d:{destination_key}"


def _calendar_observation_route_signature(scope_signature: str) -> str:
    return hashlib.sha256(scope_signature.encode("utf-8")).hexdigest()


def _prioritize_iata_pool(pool: list[str], *, max_size: int) -> list[str]:
    unique = list(dict.fromkeys(pool))

    def sort_key(iata: str) -> tuple[int, str, str, str]:
        airport = get_airport(iata)
        is_primary = bool(airport and airport.is_primary)
        country = (airport.country if airport else "") or ""
        city = (airport.city if airport else "") or ""
        return (0 if is_primary else 1, country, city, iata)

    ordered = sorted(unique, key=sort_key)
    return ordered[: max(1, max_size)]


def _pick_calendar_anchor_dates(month_dates: list[dt.date], *, max_dates: int = 6) -> list[dt.date]:
    if len(month_dates) <= max_dates:
        return month_dates
    if max_dates <= 1:
        return [month_dates[0]]
    last_index = len(month_dates) - 1
    indices = {
        int(round((position / (max_dates - 1)) * last_index))
        for position in range(max_dates)
    }
    return [month_dates[index] for index in sorted(indices)]


def _to_scope_candidates(pool: list[str], side: str) -> list[ExpandedAirportCandidate]:
    return [
        ExpandedAirportCandidate(
            seed_iata=iata,
            expanded_iata=iata,
            is_seed=True,
            distance_km=0.0,
            candidate_reason="calendar_hint_scope",
            source_of_expansion=f"calendar_hint_scope:{side}",
        )
        for iata in pool
    ]


def _build_pair_day_prices(
    rows: list[tuple[str, str, dt.date, Any]],
    *,
    target_currency: str,
) -> tuple[dict[tuple[str, str], dict[dt.date, float]], dict[str, int], dict[dt.date, dict[str, int]]]:
    pair_prices: dict[tuple[str, str], dict[dt.date, float]] = {}
    quality_counters = {
        "invalid_price_count": 0,
        "travel_date_mismatch_count": 0,
        "currency_excluded_count": 0,
    }
    quality_by_day: dict[dt.date, dict[str, int]] = {}

    def increment_quality(day: dt.date, key: str) -> None:
        quality_counters[key] += 1
        day_counters = quality_by_day.setdefault(day, {
            "invalid_price_count": 0,
            "travel_date_mismatch_count": 0,
            "currency_excluded_count": 0,
        })
        day_counters[key] += 1

    for origin_iata, destination_iata, travel_date, flight in rows:
        flight_travel_date = getattr(flight, "travel_date", None)
        if flight_travel_date is not None and str(flight_travel_date) != travel_date.isoformat():
            increment_quality(travel_date, "travel_date_mismatch_count")
            continue
        pair_key = (origin_iata, destination_iata)
        by_day = pair_prices.setdefault(pair_key, {})
        try:
            price = float(flight.price)
        except (TypeError, ValueError):
            increment_quality(travel_date, "invalid_price_count")
            continue
        if not math.isfinite(price) or price <= 0:
            increment_quality(travel_date, "invalid_price_count")
            continue
        normalized_price = convert_calendar_price(price, str(flight.currency or ""), target_currency)
        if normalized_price is None:
            increment_quality(travel_date, "currency_excluded_count")
            continue
        current = by_day.get(travel_date)
        if current is None or normalized_price < current:
            by_day[travel_date] = normalized_price
    return pair_prices, quality_counters, quality_by_day


def _rank_pairs_adaptive(
    candidate_pairs: list[tuple[str, str]],
    pair_prices_by_day: dict[tuple[str, str], dict[dt.date, float]],
) -> list[tuple[str, str]]:
    def score(pair: tuple[str, str]) -> tuple[int, float, float, str, str]:
        prices = sorted(pair_prices_by_day.get(pair, {}).values())
        coverage = len(prices)
        if coverage == 0:
            return (0, float("inf"), float("inf"), pair[0], pair[1])
        median_price = float(statistics.median(prices))
        best_price = float(prices[0])
        # higher coverage first, then cheaper prices
        return (-coverage, median_price, best_price, pair[0], pair[1])

    return sorted(candidate_pairs, key=score)


def _rank_airport_pool_adaptive(
    pool: list[str],
    *,
    side: Literal["origin", "destination"],
    pair_prices_by_day: dict[tuple[str, str], dict[dt.date, float]],
) -> list[str]:
    rows: list[tuple[int, float, str]] = []
    for iata in pool:
        coverage = 0
        best_price = float("inf")
        for (origin_iata, destination_iata), prices_by_day in pair_prices_by_day.items():
            matches = origin_iata == iata if side == "origin" else destination_iata == iata
            if not matches:
                continue
            coverage += len(prices_by_day)
            if prices_by_day:
                best_price = min(best_price, min(prices_by_day.values()))
        rows.append((-coverage, best_price, iata))
    rows.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[2] for item in rows]


def _combine_ranked_pool(
    prioritized_pool: list[str],
    adaptive_ranked_pool: list[str],
    *,
    limit: int,
) -> list[str]:
    out: list[str] = []
    for iata in adaptive_ranked_pool + prioritized_pool:
        if iata in out:
            continue
        out.append(iata)
        if len(out) >= max(1, limit):
            break
    return out


def _aggregate_day_prices(
    selected_pairs: list[tuple[str, str]],
    pair_prices_by_day: dict[tuple[str, str], dict[dt.date, float]],
    month_dates: list[dt.date],
    aggregation_mode: Literal["min", "median", "fixed_route"],
) -> dict[dt.date, float]:
    aggregated: dict[dt.date, float] = {}
    for day in month_dates:
        prices = [
            pair_prices_by_day[pair][day]
            for pair in selected_pairs
            if pair in pair_prices_by_day and day in pair_prices_by_day[pair]
        ]
        if not prices:
            continue
        if aggregation_mode == "median":
            aggregated[day] = float(statistics.median(prices))
        else:
            aggregated[day] = float(min(prices))
    return aggregated


def _to_pair_plan_items(pairs: list[tuple[str, str]]) -> list[PairPlanItem]:
    items: list[PairPlanItem] = []
    for index, (origin_iata, destination_iata) in enumerate(pairs):
        items.append(
            PairPlanItem(
                origin_iata=origin_iata,
                destination_iata=destination_iata,
                origin_seed_iata=origin_iata,
                destination_seed_iata=destination_iata,
                origin_is_seed=True,
                destination_is_seed=True,
                origin_distance_from_seed_km=0.0,
                destination_distance_from_seed_km=0.0,
                pair_priority_score=float(index),
                pair_reason="seed-seed",
            )
        )
    return items


def _calendar_hints_cache_get(cache_key: tuple[object, ...]) -> dict[str, Any] | None:
    now = time.time()
    with _CALENDAR_HINTS_CACHE_LOCK:
        cached = _CALENDAR_HINTS_CACHE.get(cache_key)
        if not cached:
            return None
        created_at, payload = cached
        if now - created_at > CALENDAR_HINTS_CACHE_TTL_SECONDS:
            _CALENDAR_HINTS_CACHE.pop(cache_key, None)
            return None
        return payload


def _calendar_hints_cache_set(cache_key: tuple[object, ...], payload: dict[str, Any]) -> None:
    with _CALENDAR_HINTS_CACHE_LOCK:
        # Evict oldest entries (FIFO) if at capacity
        while len(_CALENDAR_HINTS_CACHE) >= CALENDAR_HINTS_CACHE_MAX_SIZE:
            oldest_key = next(iter(_CALENDAR_HINTS_CACHE))
            _CALENDAR_HINTS_CACHE.pop(oldest_key, None)
        _CALENDAR_HINTS_CACHE[cache_key] = (time.time(), payload)


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
        return True
    after_minutes = _time_to_minutes(after_value)
    before_minutes = _time_to_minutes(before_value)
    if after_minutes is None and before_minutes is None:
        return True
    if after_minutes is None:
        assert before_minutes is not None
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


def _fare_profile_data(profile: FareComparisonProfile) -> FareComparisonProfileData:
    extras: list[FareComparisonExtraData] = [
        {"kind": extra.kind, "selected": extra.selected}
        for extra in profile.extras
    ]
    return {
        "travelers": profile.travelers,
        "airline_id": profile.airline_id,
        "flight_count": profile.flight_count,
        "extras": extras,
    }


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
) -> tuple[QuickSearchCanonicalRequest, list[str], list[str], QuickSearchFilterContract]:
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
            "pagination": payload_dict.get("pagination") or {},
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
        if query_overrides.get("page") is not None:
            canonical_dict["pagination"] = {**(canonical_dict.get("pagination") or {}), "page": query_overrides["page"]}
            legacy_aliases_used.append("query.page")
        if query_overrides.get("page_size") is not None:
            canonical_dict["pagination"] = {**(canonical_dict.get("pagination") or {}), "page_size": query_overrides["page_size"]}
            legacy_aliases_used.append("query.page_size")
        if query_overrides.get("sort_by") is not None:
            canonical_dict["pagination"] = {**(canonical_dict.get("pagination") or {}), "sort_by": query_overrides["sort_by"]}
            legacy_aliases_used.append("query.sort_by")
    else:
        legacy_aliases_used.append("payload.flat")
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
                "radius_km": _normalize_radius_km(raw_radius_km, bool(include_nearby_origins_value)),
                "max_candidates": 40 if origin_value == "ANY" else 10,
            },
            "destination": {
                "seed_iata": destination_value[0] if isinstance(destination_value, list) and destination_value else destination_value,
                "seed_iata_list": destination_value if isinstance(destination_value, list) else None,
                "include_nearby": include_nearby_destinations_value,
                "radius_km": _normalize_radius_km(raw_radius_km, bool(include_nearby_destinations_value)),
                "max_candidates": 40 if destination_value == "ANY" else 10,
            },
            "travel": {
                "date": travel_date_value,
                "dates": legacy_payload.travel_dates or [],
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
            "pagination": {
                "page": query_overrides.get("page") if query_overrides.get("page") is not None else payload_dict.get("page", 1),
                "page_size": (
                    query_overrides.get("page_size")
                    if query_overrides.get("page_size") is not None
                    else payload_dict.get("page_size", 10)
                ),
                "sort_by": (
                    query_overrides.get("sort_by")
                    if query_overrides.get("sort_by") is not None
                    else payload_dict.get("sort_by")
                    if payload_dict.get("sort_by") is not None
                    else legacy_payload.sort_by
                    if legacy_payload.sort_by is not None
                    else "ranking"
                ),
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

    filter_contract: QuickSearchFilterContract = {
        "aliases": legacy_aliases_used,
        "hard_supported": ["strict_filters", "departure_window", "exclude_origins", "exclude_destinations"],
        "soft_supported": ["soft_filters_weight", "seed_distance_penalty", "pair_category_bias"],
        "unsupported": ["include_stops", "max_stops", "duration_max_min"],
        "legacy_partial": ["include_stops", "max_stops"],
        "pending": ["stop-logic", "duration-filter"],
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

    return canonical, origin_list, destination_list, filter_contract


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


@router.post("/quick/calendar-hints")
def quick_search_calendar_hints(
    payload: QuickSearchCalendarHintsIn = Body(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    month_dates = _build_month_dates(payload.month)
    if not month_dates:
        return {
            "days": [],
            "meta": {
                "currency": "EUR",
                "cache_ttl_sec": CALENDAR_HINTS_CACHE_TTL_SECONDS,
                "cache_hit": False,
                "partial": False,
            },
        }

    origin_pool = _normalize_calendar_hint_iata_pool(payload.origin_iata)
    destination_pool = _normalize_calendar_hint_iata_pool(payload.destination_iata)
    scope_mode = _resolve_calendar_scope_mode(origin_pool, destination_pool)
    bucket_mode_effective: Literal["contextual", "monthly_terciles", "guidelines"] = payload.bucket_mode
    cache_currency = payload.currency
    guideline_thresholds_effective = _resolve_guideline_thresholds(
        payload,
        target_currency=cache_currency,
    )
    aggregation_mode_effective: Literal["min", "median", "fixed_route"] = (
        "min" if scope_mode == "iata" else payload.aggregation_mode
    )

    cache_scope_signature = _build_calendar_scope_signature(origin_pool, destination_pool)
    cache_bucket_signature = (
        f"{bucket_mode_effective}:{_stable_json_dumps(guideline_thresholds_effective)}"
        if guideline_thresholds_effective
        else bucket_mode_effective
    )
    request_provider = _build_request_provider()
    provider_ids = request_provider.provider_ids()
    provider_cache_id = _provider_cache_id(provider_ids)
    cache_callbacks = _build_fare_memory_cache_callbacks(
        shared_cache_enabled=QUICK_SEARCH_SHARED_CACHE_ENABLED and _supports_db_session(db),
        user_currency=cache_currency,
    )
    cache_key = (
        cache_scope_signature,
        payload.month,
        payload.adults,
        cache_currency,
        aggregation_mode_effective,
        cache_bucket_signature,
        provider_cache_id,
        payload.leg,
        payload.cabin.strip().lower(),
    )
    cached_payload = _calendar_hints_cache_get(cache_key)
    if cached_payload:
        cached_copy = dict(cached_payload)
        cached_meta = dict(cached_copy.get("meta", {}))
        cached_meta["cache_hit"] = True
        cached_copy["meta"] = cached_meta
        return cached_copy

    origin_scope = tuple(origin_pool)
    destination_scope = tuple(destination_pool)
    provider_scope = tuple(provider_ids)
    reference_fingerprint = build_calendar_reference_fingerprint(
        origin_scope=origin_scope,
        destination_scope=destination_scope,
        leg=payload.leg,
        adults=payload.adults,
        currency=cache_currency,
        provider_set=provider_scope,
        aggregation_mode=aggregation_mode_effective,
        cabin=payload.cabin,
    )
    query_fingerprints = {
        day: build_calendar_query_fingerprint(
            origin_scope=origin_scope,
            destination_scope=destination_scope,
            travel_date=day,
            leg=payload.leg,
            adults=payload.adults,
            currency=cache_currency,
            provider_set=provider_scope,
            aggregation_mode=aggregation_mode_effective,
            cabin=payload.cabin,
        )
        for day in month_dates
    }
    now = utc_now_naive()
    calendar_observations_available = True
    try:
        historical_reference = load_fresh_calendar_reference(
            db,
            reference_fingerprint=reference_fingerprint,
            now=now,
        )
        latest_known_by_day = load_latest_calendar_days(db, query_fingerprints=query_fingerprints)
    except (OperationalError, ProgrammingError):
        db.rollback()
        logger.warning("calendar_observations_unavailable")
        historical_reference = []
        latest_known_by_day = {}
        calendar_observations_available = False
    reused_fresh_observations = {
        day: stored
        for day, stored in latest_known_by_day.items()
        if stored.freshness_status == "fresh" and stored.expires_at is not None and stored.expires_at > now
    }
    reused_fresh_prices = {day: stored.price for day, stored in reused_fresh_observations.items()}
    provider_days = [day for day in month_dates if day not in reused_fresh_prices]

    prioritized_origin_pool = _prioritize_iata_pool(origin_pool, max_size=12 if len(origin_pool) > 1 else 1)
    prioritized_destination_pool = _prioritize_iata_pool(
        destination_pool,
        max_size=12 if len(destination_pool) > 1 else 1,
    )
    origin_candidates = _to_scope_candidates(prioritized_origin_pool, "origin")
    destination_candidates = _to_scope_candidates(prioritized_destination_pool, "destination")
    candidate_pairs = [
        (origin_iata, destination_iata)
        for origin_iata in prioritized_origin_pool
        for destination_iata in prioritized_destination_pool
        if origin_iata != destination_iata
    ]
    if not candidate_pairs:
        raise HTTPException(status_code=422, detail="calendar_hints_scope_has_no_valid_pairs")

    anchor_pair_prices_by_day: dict[tuple[str, str], dict[dt.date, float]] = {}
    anchor_execution_meta: dict[str, Any] = {}
    anchor_warnings: list[str] = []
    anchor_quality_counters = {
        "invalid_price_count": 0,
        "travel_date_mismatch_count": 0,
        "currency_excluded_count": 0,
    }
    anchor_quality_by_day: dict[dt.date, dict[str, int]] = {}
    ranked_pairs = candidate_pairs
    if scope_mode == "iata":
        ranked_origin_pool = prioritized_origin_pool[:1]
        ranked_destination_pool = prioritized_destination_pool[:1]
        selected_pairs = candidate_pairs[:1]
    elif provider_days:
        anchor_dates = _pick_calendar_anchor_dates(provider_days)
        anchor_pair_cap = min(24, len(candidate_pairs))
        anchor_planned_pairs, _anchor_pair_meta = build_pair_plan(
            origin_candidates,
            destination_candidates,
            max_pairs=max(1, anchor_pair_cap),
            max_requests=max(1, anchor_pair_cap * max(1, len(anchor_dates))),
            date_count=max(1, len(anchor_dates)),
        )
        anchor_execution_plan = build_execution_plan(
            anchor_planned_pairs,
            anchor_dates,
            max_requests=max(1, anchor_pair_cap * max(1, len(anchor_dates))),
        )
        anchor_rows, anchor_execution_meta, anchor_warnings = execute_plan(
            anchor_execution_plan,
            concurrency_limit=3,
            timeout_ms=5000,
            fetch_flights=lambda origin, destination, travel_date, timeout_ms: request_provider.get_flights(
                origin,
                destination,
                travel_date,
                timeout_ms,
            ),
            shared_cache_get=cache_callbacks.shared_cache_get,
            shared_cache_set=cache_callbacks.shared_cache_set,
            negative_cache_get=cache_callbacks.negative_cache_get,
            negative_cache_set=cache_callbacks.negative_cache_set,
            provider_singleflight_acquire=cache_callbacks.provider_singleflight_acquire,
            provider_singleflight_release=cache_callbacks.provider_singleflight_release,
            cache_provider_id=provider_cache_id,
        )
        anchor_pair_prices_by_day, anchor_quality_counters, anchor_quality_by_day = _build_pair_day_prices(
            anchor_rows,
            target_currency=cache_currency,
        )
        origin_ranked_adaptive = _rank_airport_pool_adaptive(
            prioritized_origin_pool,
            side="origin",
            pair_prices_by_day=anchor_pair_prices_by_day,
        )
        destination_ranked_adaptive = _rank_airport_pool_adaptive(
            prioritized_destination_pool,
            side="destination",
            pair_prices_by_day=anchor_pair_prices_by_day,
        )
        ranked_origin_pool = _combine_ranked_pool(
            prioritized_origin_pool,
            origin_ranked_adaptive,
            limit=8,
        )
        ranked_destination_pool = _combine_ranked_pool(
            prioritized_destination_pool,
            destination_ranked_adaptive,
            limit=8,
        )
        ranked_candidate_pairs = [
            (origin_iata, destination_iata)
            for origin_iata in ranked_origin_pool
            for destination_iata in ranked_destination_pool
            if origin_iata != destination_iata
        ]
        if not ranked_candidate_pairs:
            ranked_candidate_pairs = candidate_pairs[:1]
        ranked_pairs = _rank_pairs_adaptive(ranked_candidate_pairs, anchor_pair_prices_by_day)
        route_cap = 1 if aggregation_mode_effective == "fixed_route" else min(6, len(ranked_pairs))
        selected_pairs = ranked_pairs[: max(1, route_cap)]

    else:
        ranked_origin_pool = prioritized_origin_pool[:8]
        ranked_destination_pool = prioritized_destination_pool[:8]
        ranked_pairs = [
            (origin_iata, destination_iata)
            for origin_iata in ranked_origin_pool
            for destination_iata in ranked_destination_pool
            if origin_iata != destination_iata
        ]
        route_cap = 1 if aggregation_mode_effective == "fixed_route" else min(6, len(ranked_pairs))
        selected_pairs = ranked_pairs[: max(1, route_cap)]

    full_month_execution_plan = build_execution_plan(
        _to_pair_plan_items(selected_pairs),
        provider_days,
        max_requests=max(1, len(selected_pairs) * max(1, len(provider_days))),
    )
    full_rows, full_execution_meta, full_warnings = execute_plan(
        full_month_execution_plan,
        concurrency_limit=3,
        timeout_ms=6000,
        fetch_flights=lambda origin, destination, travel_date, timeout_ms: request_provider.get_flights(
            origin,
            destination,
            travel_date,
            timeout_ms,
        ),
        shared_cache_get=cache_callbacks.shared_cache_get,
        shared_cache_set=cache_callbacks.shared_cache_set,
        negative_cache_get=cache_callbacks.negative_cache_get,
        negative_cache_set=cache_callbacks.negative_cache_set,
        provider_singleflight_acquire=cache_callbacks.provider_singleflight_acquire,
        provider_singleflight_release=cache_callbacks.provider_singleflight_release,
        cache_provider_id=provider_cache_id,
    )
    pair_prices_by_day, full_quality_counters, full_quality_by_day = _build_pair_day_prices(
        full_rows,
        target_currency=cache_currency,
    )
    day_aggregated_prices = _aggregate_day_prices(
        selected_pairs,
        pair_prices_by_day,
        month_dates,
        aggregation_mode_effective,
    )
    newly_observed_prices = dict(day_aggregated_prices)
    day_aggregated_prices = {**reused_fresh_prices, **day_aggregated_prices}

    rescue_execution_meta: dict[str, Any] = {}
    rescue_warnings: list[str] = []
    rescue_quality_counters = {
        "invalid_price_count": 0,
        "travel_date_mismatch_count": 0,
        "currency_excluded_count": 0,
    }
    rescue_quality_by_day: dict[dt.date, dict[str, int]] = {}
    rescue_candidates: list[tuple[str, str]] = []
    if scope_mode != "iata" and aggregation_mode_effective != "fixed_route":
        missing_days = [day for day in month_dates if day not in day_aggregated_prices]
        rescue_candidates = [pair for pair in ranked_pairs if pair not in selected_pairs]
        rescue_pairs = rescue_candidates[:2]
        if missing_days and rescue_pairs:
            rescue_plan = build_execution_plan(
                _to_pair_plan_items(rescue_pairs),
                missing_days,
                max_requests=len(rescue_pairs) * len(missing_days),
            )
            rescue_rows, rescue_execution_meta, rescue_warnings = execute_plan(
                rescue_plan,
                concurrency_limit=3,
                timeout_ms=6000,
                fetch_flights=lambda origin, destination, travel_date, timeout_ms: request_provider.get_flights(
                    origin,
                    destination,
                    travel_date,
                    timeout_ms,
                ),
                shared_cache_get=cache_callbacks.shared_cache_get,
                shared_cache_set=cache_callbacks.shared_cache_set,
                negative_cache_get=cache_callbacks.negative_cache_get,
                negative_cache_set=cache_callbacks.negative_cache_set,
                provider_singleflight_acquire=cache_callbacks.provider_singleflight_acquire,
                provider_singleflight_release=cache_callbacks.provider_singleflight_release,
                cache_provider_id=provider_cache_id,
            )
            rescue_pair_prices, rescue_quality_counters, rescue_quality_by_day = _build_pair_day_prices(
                rescue_rows,
                target_currency=cache_currency,
            )
            pair_prices_by_day.update(rescue_pair_prices)
            selected_pairs.extend(rescue_pairs)
            rescued_prices = _aggregate_day_prices(
                selected_pairs,
                pair_prices_by_day,
                month_dates,
                aggregation_mode_effective,
            )
            newly_observed_prices.update(rescued_prices)
            day_aggregated_prices = {**reused_fresh_prices, **rescued_prices}

    currency_excluded_days = {
        day
        for quality_by_day in (anchor_quality_by_day, full_quality_by_day, rescue_quality_by_day)
        for day, counters in quality_by_day.items()
        if counters["currency_excluded_count"] > 0
    }
    timed_out_days = {
        dt.date.fromisoformat(day)
        for execution_meta in (anchor_execution_meta, full_execution_meta, rescue_execution_meta)
        for day in execution_meta.get("timed_out_dates", [])
    }
    provider_failed_days = {
        dt.date.fromisoformat(day)
        for execution_meta in (anchor_execution_meta, full_execution_meta, rescue_execution_meta)
        for day in execution_meta.get("failed_dates", [])
    }
    incomplete_current_days = currency_excluded_days | timed_out_days | provider_failed_days
    reference_by_day = {
        observation.travel_date: observation
        for observation in historical_reference
        if observation.travel_date is not None
    }
    reference_by_day.update(
        {
            day: CalendarComparableObservation(price=price, observed_at=now, travel_date=day)
            for day, price in day_aggregated_prices.items()
            if day not in incomplete_current_days
            and (
                day not in reused_fresh_observations
                or reused_fresh_observations[day].coverage_status == "available"
            )
        }
    )
    reference_observations = list(reference_by_day.values())
    contextual_classifications = {
        day: classify_contextual_price(price, reference_observations)
        for day, price in day_aggregated_prices.items()
    }
    bucket_by_day: dict[dt.date, str]
    if bucket_mode_effective == "contextual":
        bucket_by_day = {
            day: classification.bucket
            for day, classification in contextual_classifications.items()
            if classification.bucket is not None
        }
    else:
        bucket_by_day = _bucketize_day_prices_by_mode(
            day_aggregated_prices,
            bucket_mode=bucket_mode_effective,
            guideline_thresholds=guideline_thresholds_effective,
        )

    all_quality_counters = {
        key: anchor_quality_counters[key] + full_quality_counters[key] + rescue_quality_counters[key]
        for key in full_quality_counters
    }
    partial = (
        bool(anchor_warnings or full_warnings or rescue_warnings)
        or int(anchor_execution_meta.get("provider_failures", 0)) > 0
        or int(anchor_execution_meta.get("timed_out_units_count", 0)) > 0
        or int(full_execution_meta.get("provider_failures", 0)) > 0
        or int(full_execution_meta.get("timed_out_units_count", 0)) > 0
        or int(rescue_execution_meta.get("provider_failures", 0)) > 0
        or int(rescue_execution_meta.get("timed_out_units_count", 0)) > 0
    )
    days_payload: list[dict[str, Any]] = []
    for day in month_dates:
        min_price = day_aggregated_prices.get(day)
        if min_price is None:
            stored_price = latest_known_by_day.get(day)
            if stored_price is not None:
                days_payload.append(
                    {
                        "date": day.isoformat(),
                        "min_price": round(stored_price.price, 2),
                        "bucket": "none",
                        "data_quality": "stale",
                        "no_data_reason": "stale_reference",
                        "reference_sample_size": len(reference_observations),
                    }
                )
                continue
            no_data_reason = "no_fare_data"
            if day in currency_excluded_days:
                no_data_reason = "incompatible_currency"
            elif day in timed_out_days:
                no_data_reason = "provider_timeout"
            elif day in provider_failed_days:
                no_data_reason = "provider_unavailable"
            elif rescue_candidates[2:]:
                no_data_reason = "coverage_limited"
            days_payload.append(
                {
                    "date": day.isoformat(),
                    "min_price": None,
                    "bucket": "none",
                    "data_quality": "unavailable",
                    "no_data_reason": no_data_reason,
                    "reference_sample_size": len(reference_observations),
                }
            )
            continue
        classification = contextual_classifications[day]
        days_payload.append(
            {
                "date": day.isoformat(),
                "min_price": round(min_price, 2),
                "bucket": bucket_by_day.get(day, "none"),
                "data_quality": (
                    reused_fresh_observations[day].coverage_status
                    if day in reused_fresh_observations
                    else "partial" if day in incomplete_current_days else "available"
                ),
                "no_data_reason": classification.reason if bucket_mode_effective == "contextual" else None,
                "reference_sample_size": classification.reference_sample_size,
            }
        )

    coverage = {
        "days_total": len(month_dates),
        "days_priced": sum(day["min_price"] is not None for day in days_payload),
        "days_reused": len(reused_fresh_prices),
        "days_stale": sum(day["data_quality"] == "stale" for day in days_payload),
        "days_unavailable": sum(day["data_quality"] == "unavailable" for day in days_payload),
    }
    quality_metrics = {
        **all_quality_counters,
        "classification_without_reference_count": sum(
            day["no_data_reason"] == "insufficient_reference" for day in days_payload
        ),
        "provider_failure_count": sum(
            int(execution_meta.get("provider_failures", 0))
            for execution_meta in (anchor_execution_meta, full_execution_meta, rescue_execution_meta)
        ),
    }

    if calendar_observations_available:
        try:
            record_calendar_prices(
                db,
                query_fingerprints=query_fingerprints,
                reference_fingerprint=reference_fingerprint,
                route_signature=_calendar_observation_route_signature(cache_scope_signature),
                prices_by_day=newly_observed_prices,
                coverage_status_by_day={
                    day: "partial" if day in incomplete_current_days else "available"
                    for day in newly_observed_prices
                },
                leg=payload.leg,
                adults=payload.adults,
                cabin=payload.cabin,
                currency=cache_currency,
                aggregation_mode=aggregation_mode_effective,
                provider=provider_cache_id,
                observed_at=now,
                expires_at=now + dt.timedelta(hours=24),
            )
        except (OperationalError, ProgrammingError):
            db.rollback()
            logger.warning("calendar_observations_write_unavailable")
            calendar_observations_available = False
    response_payload: dict[str, Any] = {
        "days": days_payload,
        "meta": {
            "currency": cache_currency,
            "cache_ttl_sec": CALENDAR_HINTS_CACHE_TTL_SECONDS,
            "cache_hit": False,
            "partial": partial,
            "scope_mode": scope_mode,
            "ranked_airports": {
                "origin": ranked_origin_pool,
                "destination": ranked_destination_pool,
                "origin_count": len(ranked_origin_pool),
                "destination_count": len(ranked_destination_pool),
            },
            "ranked_routes_count": len(selected_pairs),
            "aggregation_mode": aggregation_mode_effective,
            "bucket_mode": bucket_mode_effective,
            "guideline_thresholds_effective": guideline_thresholds_effective,
            "provider_set": provider_ids,
            "provider_cache_id": provider_cache_id,
            "classification": {
                "mode": bucket_mode_effective,
                "reference_sample_size": len(reference_observations),
                "reference_window_days": 30,
            },
            "coverage": coverage,
            "quality": quality_metrics,
            "calendar_observations_available": calendar_observations_available,
            "execution": _combine_execution_cache_counters(
                anchor_execution_meta,
                full_execution_meta,
                rescue_execution_meta,
            ),
        },
    }
    _calendar_hints_cache_set(cache_key, response_payload)
    return response_payload


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
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: Literal["ranking", "price", "duration", "freshness"] | None = Query(default=None),
    debug: bool = Query(default=False),
    db: Session = Depends(get_db),
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
        "page": page,
        "page_size": page_size,
        "sort_by": sort_by,
    }
    
    user_currency = "EUR"
    if payload and isinstance(payload, dict):
        user_currency = str(payload.get("currency", "EUR")).upper().strip()
    shared_cache_enabled = QUICK_SEARCH_SHARED_CACHE_ENABLED and _supports_db_session(db)
    request_provider = _build_request_provider()
    provider_ids = request_provider.provider_ids()
    provider_cache_id = _provider_cache_id(provider_ids)

    cache_callbacks = _build_fare_memory_cache_callbacks(
        shared_cache_enabled=shared_cache_enabled,
        user_currency=user_currency,
    )
        
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
        if exc.status_code == 422 and reason == "validation_error":
            details = exc.detail if isinstance(exc.detail, list) else [detail_item]
            raise ApiError(
                status=422,
                code="validation_error",
                message=message_for_code("validation_error"),
                details=details,
            ) from exc
        raise ApiError(
            status=exc.status_code,
            code="quick_search_invalid_request",
            message="Quick-search request rejected during request normalization.",
            details=[detail_item],
        ) from exc
    _phase_end("request_normalization_ms", started)

    enforce_quick_search_legacy_alias_policy(filter_contract["aliases"])

    travel_date_value = canonical.travel.date
    search_fingerprint = build_search_fingerprint(
        canonical,
        currency=user_currency,
        provider_set=provider_ids,
    )
    if _supports_db_session(db):
        record_quick_search_popularity(
            db,
            QuickSearchPopularitySignal(
                origin_iata=canonical.origin.seed_iata,
                destination_iata=canonical.destination.seed_iata,
                travel_date=travel_date_value,
                currency=user_currency,
            ),
        )

    if shared_cache_enabled and FARE_MEMORY_SEARCH_CACHE_ENABLED:
        exact_cache_entry = get_exact_search_cache_entry(
            db,
            origin_iata=canonical.origin.seed_iata,
            destination_iata=canonical.destination.seed_iata,
            travel_date=travel_date_value,
            search_fingerprint=search_fingerprint,
        )
        if exact_cache_entry is not None:
            exact_payload = deserialize_exact_search_payload(exact_cache_entry.payload_json)
            exact_freshness = build_effective_freshness(exact_cache_entry)
            meta = exact_payload.setdefault("meta", {})
            meta["query_trace_id"] = query_trace_id
            meta["search_fingerprint"] = search_fingerprint
            execution_meta = meta.setdefault("execution", {})
            execution_meta["exact_search_cache_hit"] = True
            execution_meta["provider_calls"] = 0
            execution_meta["cache_misses"] = 0
            execution_meta["l1_cache_hits"] = 0
            execution_meta["l2_cache_hits"] = 0
            execution_meta["cache_hits"] = max(1, int(execution_meta.get("cache_hits", 0)))
            execution_meta["provider_set"] = provider_ids
            execution_meta["provider_cache_id"] = provider_cache_id
            meta["search_cache"] = {
                "exact_hit": True,
                "search_fingerprint": search_fingerprint,
                "freshness": exact_freshness,
                "requires_revalidation": bool(exact_freshness["requires_revalidation"]),
                "provider": "search_exact",
                "provider_set": provider_ids,
            }
            _enrich_pipeline_counters(exact_payload)
            log_fare_memory_quick_search_counters(
                query_trace_id=query_trace_id,
                pipeline_counters=meta.get("pipeline_counters", {}),
            )
            return exact_payload

    origin_seed_pool = list(origin_list)
    destination_seed_pool = list(destination_list)
    requested_days_before = canonical.travel.flex_before
    requested_days_after = canonical.travel.flex_after
    requested_exact_dates = canonical.travel.dates

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

    exclude_origin_list = canonical.constraints.exclude_origins
    exclude_destination_list = canonical.constraints.exclude_destinations
    country_scope_multi_seed_mode = len(origin_seed_pool) > 1 or len(destination_seed_pool) > 1
    filter_seed_pool = filter_contract["seed_pool"]

    if len(origin_seed_pool) > 1:
        _warn("country_scope_multi_seed_applied", side="origin", seed_count=len(origin_seed_pool))
    if len(destination_seed_pool) > 1:
        _warn("country_scope_multi_seed_applied", side="destination", seed_count=len(destination_seed_pool))
    if filter_seed_pool["origin_truncated"]:
        _warn(
            "country_scope_seed_pool_truncated",
            side="origin",
            cap=filter_seed_pool["cap"],
            effective_count=filter_seed_pool["origin_count"],
        )
    if filter_seed_pool["destination_truncated"]:
        _warn(
            "country_scope_seed_pool_truncated",
            side="destination",
            cap=filter_seed_pool["cap"],
            effective_count=filter_seed_pool["destination_count"],
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

        date_candidates = requested_exact_dates or _build_flex_dates(travel_date_value, days_before, days_after)

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
        logger.info(
            "quick_search_provider_fetch_start trace=%s step=%s provider_set=%s units=%s concurrency_limit=%s timeout_ms=%s",
            query_trace_id,
            step,
            provider_ids,
            len(execution_plan.units),
            canonical.execution.concurrency_limit,
            canonical.execution.timeout_ms,
        )
        combined, execution_meta, execution_warnings = execute_plan(
            execution_plan,
            concurrency_limit=canonical.execution.concurrency_limit,
            timeout_ms=canonical.execution.timeout_ms,
            fetch_flights=lambda o, d, date_str, timeout: request_provider.get_flights(
                o,
                d,
                date_str,
                timeout_ms=timeout,
                currency=user_currency,
            ),
            shared_cache_get=cache_callbacks.shared_cache_get,
            shared_cache_set=cache_callbacks.shared_cache_set,
            negative_cache_get=cache_callbacks.negative_cache_get,
            negative_cache_set=cache_callbacks.negative_cache_set,
            provider_singleflight_acquire=cache_callbacks.provider_singleflight_acquire,
            provider_singleflight_release=cache_callbacks.provider_singleflight_release,
            cache_provider_id=provider_cache_id,
        )
        execution_meta["provider_set"] = provider_ids
        execution_meta["provider_cache_id"] = provider_cache_id
        _phase_add("provider_fetch_ms", int((time.perf_counter() - started) * 1000))

        normalized_execution_warnings = _normalize_warning_codes(execution_warnings)
        warning_codes = list(normalized_execution_warnings)
        warnings.extend(normalized_execution_warnings)
        for code in normalized_execution_warnings:
            _warn(code)
        for event in execution_meta.get("warnings_structured_events", []):
            _warn(
                event.get("code", "provider_error_partial"),
                provider=event.get("provider"),
                severity=event.get("severity", "warning"),
                **(event.get("meta") or {}),
            )
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
        if not combined and execution_meta.get("provider_failures", 0):
            _warn("provider_total_outage", count=execution_meta.get("provider_failures"))
            warning_codes.append("provider_total_outage")

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
            strict_filters=strict_filters,
            max_stops=max_stops,
            include_stops=include_stops,
            duration_max_min=duration_max_min,
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
        "provider_timeout_partial",
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
                "days_before": requested_days_before,
                "days_after": requested_days_after,
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
    pagination_sort_by = canonical.pagination.sort_by
    sorted_scoped_results = _sort_quick_search_results(scoped_ranked_results, pagination_sort_by)
    total_results_count = len(sorted_scoped_results)
    pagination_page = max(1, int(canonical.pagination.page))
    pagination_page_size = max(1, int(canonical.pagination.page_size))
    pagination_total_pages = max(1, math.ceil(total_results_count / pagination_page_size)) if total_results_count > 0 else 1
    pagination_page_effective = min(pagination_page, pagination_total_pages)
    pagination_start = (pagination_page_effective - 1) * pagination_page_size
    pagination_end = pagination_start + pagination_page_size
    paginated_ranked_results = sorted_scoped_results[pagination_start:pagination_end]
    out_of_scope_discarded = max(0, len(deduped.results) - len(scoped_ranked_results))
    if out_of_scope_discarded > 0:
        warnings.append("result_out_of_scope_discarded")
        _warn(
            "result_out_of_scope_discarded",
            step=selected_pass["step"],
            discarded_count=out_of_scope_discarded,
        )

    signature_origin_seed_pool = filter_seed_pool["origin_requested_iata"] or origin_seed_pool
    signature_destination_seed_pool = filter_seed_pool["destination_requested_iata"] or destination_seed_pool
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
        **filter_seed_pool,
        "winning_step": selected_pass["step"],
        "origin_scope_count": len(origin_scope_iata),
        "destination_scope_count": len(destination_scope_iata),
    }

    warnings = _normalize_warning_codes(warnings)
    ui_warning_codes = _filter_ui_warning_codes(warnings)
    phase_ms["total_search_ms"] = int((time.perf_counter() - t0) * 1000)
    requested_date_candidates = requested_exact_dates or _build_flex_dates(
        travel_date_value,
        requested_days_before,
        requested_days_after,
    )

    warning_codes_set = set(warnings)
    provider_status_entries = execution_meta.get("provider_statuses", [])
    provider_total_outage = bool(warning_codes_set & PROVIDER_TOTAL_OUTAGE_CODES)
    partial_results_served = bool(scoped_ranked_results) and bool(
        warning_codes_set & degradation_signal_codes
    )
    if provider_total_outage:
        provider_overall_status = "total_outage"
    elif warning_codes_set & degradation_signal_codes:
        provider_overall_status = "partial_degraded"
    else:
        provider_overall_status = "ok"
    providers_aggregated = [
        {
            "id": item.get("id"),
            "status": item.get("status", "ok"),
            "degraded": item.get("status", "ok") != "ok",
            "errors": int(item.get("errors", 0)),
            "timeouts": int(item.get("timeouts", 0)),
            "results_count": int(item.get("results_count", 0)),
        }
        for item in provider_status_entries
    ]
    known_provider_ids = provider_ids
    known_ids_set = {item.get("id") for item in providers_aggregated}
    for provider_id in known_provider_ids:
        if provider_id in known_ids_set:
            continue
        providers_aggregated.append(
            {
                "id": provider_id,
                "status": "ok",
                "degraded": False,
                "errors": 0,
                "timeouts": 0,
                "results_count": 0,
            }
        )
    ryanair_item = next((item for item in providers_aggregated if item.get("id") == "ryanair"), None)
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
    provider_status = {
        "provider": "ryanair",
        "availability": {"status": "failed" if availability_failed else "ok"},
        "fares": {"status": "failed" if fares_failed else "ok"},
        "overall": provider_overall_status,
        "partial_results_served": partial_results_served,
        "total_outage": provider_total_outage,
        "providers": providers_aggregated,
        "overall_status": provider_overall_status,
        "legacy": {
            "provider": "ryanair",
            "overall": provider_overall_status,
            "errors": int((ryanair_item or {}).get("errors", 0)),
            "timeouts": int((ryanair_item or {}).get("timeouts", 0)),
        },
    }

    exact_cache_category = "empty"
    if paginated_ranked_results:
        exact_cache_category = "degraded" if any(code in PROVIDER_WARNING_CODES for code in warnings) else "ready"
    elif any(code in PROVIDER_OUTAGE_WARNING_CODES for code in warnings):
        exact_cache_category = "degraded"

    result_freshness_status = "fresh" if exact_cache_category == "ready" else "warm"
    result_validation_status = "revalidated" if exact_cache_category == "ready" else "provider_partial"
    result_confidence_score = 0.95 if exact_cache_category == "ready" else 0.4

    serialized_results: list[dict[str, Any]] = []
    for idx, item in enumerate(paginated_ranked_results):
        item_freshness = build_freshness_payload(
            status=result_freshness_status,
            observed_at=item.flight.captured_at,
            expires_at=None,
            source="provider_live",
            now=utc_now_naive(),
            confidence_score=result_confidence_score,
            validation_status=result_validation_status,
        )
        serialized_results.append(
            {
                "result_id": f"{item.origin}-{item.destination}-{item.travel_date}-{pagination_start + idx}",
                "origin": item.origin,
                "destination": item.destination,
                "travel_date": str(item.travel_date),
                "departure_time_local": item.flight.departure_time_local,
                "price": item.price_value,
                "price_total": item.price_value,
                "currency": item.flight.currency,
                "source": item.flight.source,
                "duration_total_min": _estimate_duration_minutes(item.origin, item.destination),
                "ranking_score": item.final_score,
                "stale_data": bool(item_freshness["requires_revalidation"]),
                "freshness_ts": item.flight.captured_at.isoformat(),
                "freshness": item_freshness,
                "deeplink_url": item.flight.deeplink_url,
                "itinerary_type": "direct",
                "legs": _build_live_tracking_legs(item),
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
                "ai_preferred": False,
                "ai_preferred_reason": None,
            }
        )
    ai_preference = select_quick_search_ai_preference(
        serialized_results,
        query_context={
            "origin_seed_pool": signature_origin_seed_pool,
            "destination_seed_pool": signature_destination_seed_pool,
            "travel_date": str(travel_date_value),
            "winning_step": selected_pass["step"],
            "strict_filters": strict_filters,
        },
    )
    if ai_preference.enabled and ai_preference.preferred_result_id:
        for item in serialized_results:
            if item["result_id"] == ai_preference.preferred_result_id:
                item["ai_preferred"] = True
                item["ai_preferred_reason"] = ai_preference.reason
                break

    logger.info(
        "quick_search trace=%s results=%s planned_pairs=%s requested_units=%s rescue=%s winning_step=%s warnings=%s provider_statuses=%s concurrency_limit=%s l1_hits=%s l2_hits=%s provider_calls=%s ai_source=%s ai_preferred_result_id=%s ai_fallback=%s ai_failure_reason=%s",
        query_trace_id,
        len(serialized_results),
        pair_plan_stats["total_pairs"],
        execution_meta.get("requested_units_count", 0),
        rescue_attempted,
        rescue_winning_step,
        warnings,
        execution_meta.get("provider_statuses", []),
        canonical.execution.concurrency_limit,
        execution_meta.get("l1_cache_hits", 0),
        execution_meta.get("l2_cache_hits", 0),
        execution_meta.get("provider_calls", 0),
        ai_preference.source,
        ai_preference.preferred_result_id,
        ai_preference.fallback_used,
        ai_preference.failure_reason,
    )

    # Fase 13: Lazy pruning of expired cache entries (probabilistic, ~10% of requests).
    # Runs in a daemon thread to avoid blocking the HTTP response TTFB.
    if shared_cache_enabled and hash(query_trace_id) % 10 == 0:
        prune_expired_entries_async(batch_size=200)

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
            "ai_preference": {
                "enabled": ai_preference.enabled,
                "source": ai_preference.source,
                "preferred_result_id": ai_preference.preferred_result_id,
                "fallback_used": ai_preference.fallback_used,
                "failure_reason": ai_preference.failure_reason,
            },
        }

    response_payload: dict[str, Any] = {
        "query": {
            "origin": canonical.origin.model_dump(),
            "destination": canonical.destination.model_dump(),
            "travel": {
                "date": str(travel_date_value),
                "flex_before": requested_days_before,
                "flex_after": requested_days_after,
                "dates": [str(date_item) for date_item in requested_exact_dates],
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
                "l1_cache_hits": execution_meta.get("l1_cache_hits", 0),
                "l2_cache_hits": execution_meta.get("l2_cache_hits", 0),
                "negative_cache_hits": execution_meta.get("negative_cache_hits", 0),
                "final_results_count": total_results_count,
                "paginated_results_count": len(paginated_ranked_results),
            },
            "pagination": {
                "page": pagination_page_effective,
                "page_size": pagination_page_size,
                "sort_by": pagination_sort_by,
                "total_results": total_results_count,
                "total_pages": pagination_total_pages,
                "has_next": pagination_page_effective < pagination_total_pages,
                "has_prev": pagination_page_effective > 1,
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
            "ai_preference": {
                "enabled": ai_preference.enabled,
                "source": ai_preference.source,
                "preferred_result_id": ai_preference.preferred_result_id,
                "fallback_used": ai_preference.fallback_used,
            },
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
            "warnings": ui_warning_codes,
            "discarded": max(0, len(combined) - len(flights_after_filters)) + out_of_scope_discarded,
        },
        "results": serialized_results,
    }

    response_payload["meta"]["search_fingerprint"] = search_fingerprint
    response_payload["meta"]["provider_set"] = provider_ids
    response_payload["meta"]["provider_cache_id"] = provider_cache_id
    live_search_cache_freshness = build_freshness_payload(
        status=result_freshness_status,
        observed_at=utc_now_naive(),
        expires_at=None,
        source="search_live",
        now=utc_now_naive(),
        confidence_score=0.95 if exact_cache_category == "ready" else 0.72 if exact_cache_category == "empty" else 0.4,
        validation_status="revalidated" if exact_cache_category == "ready" else "provider_partial",
    )
    response_payload["meta"]["search_cache"] = {
        "exact_hit": False,
        "search_fingerprint": search_fingerprint,
        "freshness": live_search_cache_freshness,
        "requires_revalidation": bool(live_search_cache_freshness["requires_revalidation"]),
        "provider": "search_exact",
        "provider_set": provider_ids,
    }

    exact_cache_entry = None
    if shared_cache_enabled and FARE_MEMORY_SEARCH_CACHE_ENABLED:
        exact_cache_entry = set_exact_search_cache_entry(
            db,
            origin_iata=canonical.origin.seed_iata,
            destination_iata=canonical.destination.seed_iata,
            travel_date=travel_date_value,
            search_fingerprint=search_fingerprint,
            canonical_request_json=json.dumps(canonical.model_dump(mode="json"), ensure_ascii=False),
            provider_set_json=json.dumps(provider_ids, ensure_ascii=False),
            response_payload=response_payload,
            category=exact_cache_category,
            confidence_score=0.95 if exact_cache_category == "ready" else 0.72 if exact_cache_category == "empty" else 0.4,
        )
        exact_cache_freshness = build_effective_freshness(exact_cache_entry)
        response_payload["meta"]["search_cache"]["freshness"] = exact_cache_freshness
        response_payload["meta"]["search_cache"]["requires_revalidation"] = bool(exact_cache_freshness["requires_revalidation"])

    _enrich_pipeline_counters(response_payload)
    log_fare_memory_quick_search_counters(
        query_trace_id=query_trace_id,
        pipeline_counters=response_payload.get("meta", {}).get("pipeline_counters", {}),
    )

    if combined and _supports_db_session(db) and FARE_MEMORY_OFFER_CACHE_ENABLED:
        observation_observed_at = exact_cache_entry.captured_at_utc if exact_cache_entry is not None else utc_now_naive()
        observation_expires_at = exact_cache_entry.expires_at_utc if exact_cache_entry is not None else None
        observation_freshness_status = "fresh" if exact_cache_category == "ready" else "warm"
        observation_confidence_score = 0.95 if exact_cache_category == "ready" else 0.4
        observation_validation_status = "revalidated" if exact_cache_category == "ready" else "provider_partial"
        persist_provider_flight_observations(
            db,
            provider_flights=combined,
            context=ObservationPersistenceContext(
                search_cache_entry_id=exact_cache_entry.id if exact_cache_entry is not None else None,
                observed_at=observation_observed_at,
                expires_at=observation_expires_at,
                freshness_status=observation_freshness_status,
                confidence_score=observation_confidence_score,
                validation_status=observation_validation_status,
            ),
        )

    return response_payload


def get_saved_result_snapshot(db: Session, watch: FlightWatch) -> dict | None:
    """Return the latest snapshot for a watch as a JSON-safe dict, or None."""
    latest = db.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.watch_id == watch.id)
        .order_by(PriceSnapshot.captured_at_utc.desc(), PriceSnapshot.id.desc())
        .limit(1)
    )
    if latest is None:
        return None
    return {
        "captured_at_utc": latest.captured_at_utc.isoformat() if latest.captured_at_utc else None,
        "raw_price": float(latest.raw_price) if latest.raw_price is not None else None,
        "raw_currency": latest.raw_currency,
        "departure_time_local": latest.departure_time_local,
        "provider": latest.provider,
    }


@router.post("/save-result")
def save_result(
    payload: QuickSearchSaveResultIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    endpoint = "POST:/api/v1/search/save-result"
    req_hash = request_hash(payload.model_dump(mode="json"))
    replay = replay_if_exists(
        db,
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        req_hash=req_hash,
    )
    if replay:
        _, body = replay
        return body

    if payload.origin_iata == payload.destination_iata:
        raise HTTPException(status_code=400, detail="origin_equals_destination")

    existing = db.scalar(
        select(FlightWatch).where(
            FlightWatch.user_id == current_user.id,
            FlightWatch.origin_iata == payload.origin_iata,
            FlightWatch.destination_iata == payload.destination_iata,
            FlightWatch.travel_date_local == payload.travel_date,
            FlightWatch.status != "deleted",
        )
    )
    if existing:
        if payload.group_id and existing.group_id != payload.group_id:
            existing.group_id = payload.group_id
        if payload.fare_profile is not None:
            existing.fare_profile = _fare_profile_data(payload.fare_profile)
        tracking_identity = replace_watch_tracked_legs(db, existing, payload.legs)
        handle_saved_result_observation(db, existing, payload)
        body = {
            "watch_id": existing.id,
            "created_or_existing": "existing",
            "tracking_identity": tracking_identity,
            "snapshot": get_saved_result_snapshot(db, existing),
        }
        store_response(
            db,
            user_id=current_user.id,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            req_hash=req_hash,
            response_status=200,
            response_body=body,
        )
        db.commit()
        return body

    watch = FlightWatch(
        user_id=current_user.id,
        origin_iata=payload.origin_iata,
        destination_iata=payload.destination_iata,
        travel_date_local=payload.travel_date,
        target_price=payload.price_total,
        group_id=payload.group_id,
        fare_profile=_fare_profile_data(payload.fare_profile) if payload.fare_profile else None,
    )
    db.add(watch)
    db.flush()
    tracking_identity = replace_watch_tracked_legs(db, watch, payload.legs)
    handle_saved_result_observation(db, watch, payload)
    body = {
        "watch_id": watch.id,
        "created_or_existing": "created",
        "tracking_identity": tracking_identity,
        "snapshot": get_saved_result_snapshot(db, watch),
    }
    store_response(
        db,
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        req_hash=req_hash,
        response_status=200,
        response_body=body,
    )
    db.commit()
    db.refresh(watch)
    return body
