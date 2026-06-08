import json
import logging
import unicodedata
from datetime import datetime, time, timedelta
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.door_to_door.providers.registry import resolve_provider_runtime
from app.door_to_door.schemas import (
    DoorToDoorChosenOptionIn,
    DoorToDoorChosenOptionOut,
    DoorToDoorFlightOut,
    DoorToDoorHistoryOut,
    DoorToDoorProviderStatusOut,
    DoorToDoorSavedLocationIn,
    DoorToDoorSavedLocationOut,
    DoorToDoorSearchRequest,
    DoorToDoorSearchResponse,
    DoorToDoorSuggestionOut,
    DoorToDoorSuggestionsMetaOut,
    DoorToDoorSuggestionsResponseOut,
    DoorToDoorWarningOut,
)
from app.door_to_door.services.cache_service import DoorToDoorCacheService
from app.door_to_door.services.search_service import DoorToDoorSearchService
from app.infrastructure.airports_catalog import country_code_from_airport, get_airport
from app.infrastructure.db.models import (
    DoorToDoorChosenOption,
    DoorToDoorSavedLocation,
    DoorToDoorSearchHistory,
    FlightWatch,
    PriceSnapshot,
    User,
)
from app.infrastructure.db.session import get_db

router = APIRouter()
MADRID = ZoneInfo("Europe/Madrid")
DEFAULT_FLIGHT_DURATION_MINUTES = 155

SUGGESTIONS = [
    DoorToDoorSuggestionOut(id="seed_airport_only", type="airport_only", label="Solo aeropuerto", subtitle="Terminar al aterrizar sin tramo terrestre", source_type="local_static"),
    DoorToDoorSuggestionOut(id="seed_station", type="station", label="Estación central", subtitle="Ejemplo de punto de transporte", source_type="local_static"),
    DoorToDoorSuggestionOut(id="seed_city", type="city", label="Centro ciudad", subtitle="Ejemplo de destino urbano", source_type="local_static"),
]

cache_service = DoorToDoorCacheService(ttl_seconds=300)
logger = logging.getLogger(__name__)


def _get_watch(db: Session, user: User, watch_id: str) -> FlightWatch:
    watch = db.scalar(select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == user.id))
    if not watch or watch.status == "deleted":
        raise HTTPException(status_code=404, detail="watch_not_found")
    return watch


def _flight_context(db: Session, watch: FlightWatch) -> tuple[DoorToDoorFlightOut, list[DoorToDoorWarningOut]]:
    warnings: list[DoorToDoorWarningOut] = []
    latest = db.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.watch_id == watch.id)
        .order_by(PriceSnapshot.captured_at_utc.desc(), PriceSnapshot.id.desc())
    )
    confidence = "estimated"
    departure_clock = time(hour=14, minute=20)
    using_estimated_schedule = True

    if latest and latest.departure_time_local:
        try:
            hour, minute = latest.departure_time_local.split(":", 1)
            departure_clock = time(hour=int(hour), minute=int(minute))
            confidence = "live"
            using_estimated_schedule = False
        except ValueError:
            confidence = "estimated"

    departure = datetime.combine(watch.travel_date_local, departure_clock, tzinfo=MADRID)
    arrival = departure + timedelta(minutes=DEFAULT_FLIGHT_DURATION_MINUTES)

    if using_estimated_schedule:
        warnings.append(
            DoorToDoorWarningOut(
                code="FLIGHT_TIME_ESTIMATED",
                message="No hay horario completo para este vuelo guardado. Se usa salida conocida y llegada estimada.",
            )
        )

    return (
        DoorToDoorFlightOut(
            origin_airport=watch.origin_iata,
            destination_airport=watch.destination_iata,
            departure_at=departure,
            arrival_at=arrival,
            flight_time_confidence=confidence,
        ),
        warnings,
    )


def _saved_location_out(location: DoorToDoorSavedLocation) -> DoorToDoorSavedLocationOut:
    return DoorToDoorSavedLocationOut(
        id=location.id,
        type=location.location_type,
        label=location.label,
        lat=float(location.lat) if location.lat is not None else None,
        lng=float(location.lng) if location.lng is not None else None,
        updated_at=location.updated_at,
    )


@router.get("/providers/status", response_model=list[DoorToDoorProviderStatusOut])
def providers_status() -> list[DoorToDoorProviderStatusOut]:
    runtime = resolve_provider_runtime()
    return runtime.statuses


@router.get("/suggestions", response_model=DoorToDoorSuggestionsResponseOut)
async def suggestions(
    q: str = Query(default="", max_length=120),
    session_token: str | None = Query(default=None, max_length=128),
    field: str = Query(default="origin", pattern="^(origin|destination)$"),
    watch_id: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoorToDoorSuggestionsResponseOut:
    query = q.strip().lower()
    typed_fallback = _typed_fallback_suggestion(q)
    static_items = (
        SUGGESTIONS
        if not query
        else [item for item in SUGGESTIONS if query in item.label.lower() or query in item.subtitle.lower()]
    )
    meta = DoorToDoorSuggestionsMetaOut(
        provider_status="fallback_active",
        degraded_reason="provider_disabled",
        used_region_codes=[],
    )
    runtime = resolve_provider_runtime()
    preferred_region_codes: list[str] = []
    context_airport = None
    if watch_id:
        watch = db.scalar(select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id))
        if watch:
            selected_iata = watch.origin_iata if field == "origin" else watch.destination_iata
            airport = get_airport(selected_iata)
            if airport:
                context_airport = airport
                country_code = country_code_from_airport(airport).strip().lower()
                if country_code:
                    preferred_region_codes = [country_code]

    google_items: list[DoorToDoorSuggestionOut] = []
    nominatim_items: list[DoorToDoorSuggestionOut] = []
    google_failed = False
    google_disabled = runtime.google_places_provider is None

    if runtime.google_places_provider is not None:
        try:
            google_items = await runtime.google_places_provider.suggest(
                q,
                limit=8,
                session_token=session_token,
                preferred_region_codes=preferred_region_codes,
            )
        except Exception:
            google_failed = True
            logger.exception(
                "door_to_door_suggestions_provider_error",
                extra={
                    "provider": "google_places",
                    "field": field,
                    "watch_id": watch_id,
                    "query": q,
                    "preferred_region_codes": preferred_region_codes,
                },
            )

    should_use_nominatim = runtime.nominatim_provider is not None and (google_disabled or google_failed or not google_items)
    try:
        if should_use_nominatim and runtime.nominatim_provider is not None:
            nominatim_items = await runtime.nominatim_provider.suggest(
                q,
                limit=8,
                session_token=session_token,
                preferred_region_codes=preferred_region_codes,
            )
    except Exception:
        logger.exception(
            "door_to_door_suggestions_provider_error",
            extra={
                "provider": "nominatim",
                "field": field,
                "watch_id": watch_id,
                "query": q,
                "preferred_region_codes": preferred_region_codes,
            },
        )

    if google_items:
        meta = DoorToDoorSuggestionsMetaOut(
            provider_status="api_live",
            degraded_reason=None,
            used_region_codes=preferred_region_codes,
        )
    elif nominatim_items:
        meta = DoorToDoorSuggestionsMetaOut(
            provider_status="fallback_active",
            degraded_reason="google_unavailable_using_open_data",
            used_region_codes=preferred_region_codes,
        )
    elif google_failed:
        meta = DoorToDoorSuggestionsMetaOut(
            provider_status="provider_error",
            degraded_reason="suggestions_fetch_failed",
            used_region_codes=preferred_region_codes,
        )
    else:
        meta = DoorToDoorSuggestionsMetaOut(
            provider_status="fallback_active",
            degraded_reason="no_results_available",
            used_region_codes=preferred_region_codes,
        )

    merged: list[DoorToDoorSuggestionOut] = []
    seen_place_ids: set[str] = set()
    seen_label_country: set[str] = set()
    seen_coords: set[str] = set()
    if typed_fallback:
        static_items = [typed_fallback, *static_items]
    for item in [*google_items, *nominatim_items, *static_items]:
        if _is_duplicate_suggestion(item, seen_place_ids, seen_label_country, seen_coords):
            continue
        merged.append(item)
    ranked = _rank_suggestions(
        merged,
        query=q,
        preferred_region_codes=preferred_region_codes,
        context_airport=context_airport,
    )
    return DoorToDoorSuggestionsResponseOut(items=ranked[:10], meta=meta)


def _is_duplicate_suggestion(
    item: DoorToDoorSuggestionOut,
    seen_place_ids: set[str],
    seen_label_country: set[str],
    seen_coords: set[str],
) -> bool:
    if item.place_id:
        place_key = item.place_id.strip().lower()
        if place_key in seen_place_ids:
            return True
        seen_place_ids.add(place_key)

    label_country_key = f"{_normalize_text(item.label)}|{_extract_country_key(item)}"
    if label_country_key in seen_label_country:
        return True
    seen_label_country.add(label_country_key)

    if item.lat is not None and item.lng is not None:
        coord_key = f"{round(item.lat, 3)}:{round(item.lng, 3)}"
        if coord_key in seen_coords:
            return True
        seen_coords.add(coord_key)
    return False


def _normalize_text(value: str) -> str:
    raw = value.strip().lower()
    if not raw:
        return ""
    nfkd_form = unicodedata.normalize("NFKD", raw)
    return "".join(ch for ch in nfkd_form if not unicodedata.combining(ch))


def _extract_country_key(item: DoorToDoorSuggestionOut) -> str:
    subtitle = item.subtitle.strip()
    if not subtitle:
        return ""
    country = subtitle.split(",")[-1].strip()
    normalized = _normalize_text(country)
    if len(normalized) == 2 and normalized.isalpha():
        return normalized
    country_map = {
        "espana": "es",
        "spain": "es",
        "luxembourg": "lu",
        "luxemburgo": "lu",
        "italia": "it",
        "italy": "it",
        "paises bajos": "nl",
        "netherlands": "nl",
    }
    return country_map.get(normalized, normalized)


def _rank_suggestions(
    items: list[DoorToDoorSuggestionOut],
    *,
    query: str,
    preferred_region_codes: list[str],
    context_airport,
) -> list[DoorToDoorSuggestionOut]:
    normalized_query = _normalize_text(query)
    preferred = {code.strip().lower() for code in preferred_region_codes if code}
    type_weight = {
        "city": 0,
        "address": 1,
        "airport": 2,
        "station": 3,
        "saved_location": 4,
        "airport_only": 5,
    }

    def score(item: DoorToDoorSuggestionOut) -> tuple[int, int, int, int, int, str]:
        label_normalized = _normalize_text(item.label)
        exact_match = 0 if normalized_query and label_normalized == normalized_query else 1
        starts_with = 0 if normalized_query and label_normalized.startswith(normalized_query) else 1
        country_match = 0 if preferred and _extract_country_key(item) in preferred else 1
        proximity_score = _distance_score(item, context_airport)
        type_score = type_weight.get(item.type, 9)
        return (exact_match, starts_with, country_match, proximity_score, type_score, label_normalized)

    return sorted(items, key=score)


def _distance_score(item: DoorToDoorSuggestionOut, airport) -> int:
    if airport is None or item.lat is None or item.lng is None:
        return 99999
    distance_km = _haversine_km(airport.latitude, airport.longitude, item.lat, item.lng)
    return int(distance_km)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    a = sin(d_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return earth_radius_km * c


def _typed_fallback_suggestion(raw_query: str) -> DoorToDoorSuggestionOut | None:
    label = raw_query.strip()
    if len(label) < 2:
        return None
    return DoorToDoorSuggestionOut(
        id=f"typed_{label.lower().replace(' ', '_')[:48]}",
        type="address",
        label=label,
        subtitle="Usar texto escrito (fallback local)",
        source_type="local_static",
    )


@router.post("/search", response_model=DoorToDoorSearchResponse)
async def search_door_to_door(
    payload: DoorToDoorSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoorToDoorSearchResponse:
    watch = _get_watch(db, current_user, payload.flight_watch_id)
    flight, flight_warnings = _flight_context(db, watch)

    if payload.save_origin_as_default:
        _upsert_saved_location(db, current_user.id, DoorToDoorSavedLocationIn(location=payload.origin))

    runtime = resolve_provider_runtime()
    enabled_providers = ",".join(
        sorted(item.name for item in runtime.statuses if item.enabled and item.supports_search)
    )
    runtime_signature = ":".join(
        [
            f"mock={int(runtime.mock_enabled)}",
            f"real={int(runtime.real_enabled)}",
            f"scrapers={int(runtime.scrapers_enabled)}",
            f"search={enabled_providers}",
        ]
    )
    cache_key = (
        f"d2d:{runtime_signature}:{current_user.id}:{payload.flight_watch_id}:"
        f"{payload.model_dump_json(by_alias=True)}"
    )
    cached_response = cache_service.get(cache_key)
    if cached_response:
        return cached_response

    service = DoorToDoorSearchService(
        providers=runtime.providers,
        provider_statuses=runtime.statuses,
        mock_enabled=runtime.mock_enabled,
    )
    response = await service.search(
        db=db,
        user_id=current_user.id,
        request=payload,
        flight=flight,
        bootstrap_warnings=flight_warnings,
    )

    cache_service.set(cache_key, response)
    return response


@router.get("/saved-location", response_model=DoorToDoorSavedLocationOut | None)
def get_saved_location(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoorToDoorSavedLocationOut | None:
    location = db.scalar(select(DoorToDoorSavedLocation).where(DoorToDoorSavedLocation.user_id == current_user.id))
    return _saved_location_out(location) if location else None


@router.put("/saved-location", response_model=DoorToDoorSavedLocationOut)
def put_saved_location(
    payload: DoorToDoorSavedLocationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoorToDoorSavedLocationOut:
    return _saved_location_out(_upsert_saved_location(db, current_user.id, payload))


@router.delete("/saved-location")
def delete_saved_location(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    location = db.scalar(select(DoorToDoorSavedLocation).where(DoorToDoorSavedLocation.user_id == current_user.id))
    if location:
        db.delete(location)
        db.commit()
    return {"status": "ok"}


def _upsert_saved_location(db: Session, user_id: str, payload: DoorToDoorSavedLocationIn) -> DoorToDoorSavedLocation:
    location = db.scalar(select(DoorToDoorSavedLocation).where(DoorToDoorSavedLocation.user_id == user_id))
    if location is None:
        location = DoorToDoorSavedLocation(user_id=user_id, location_type=payload.location.type, label=payload.location.label)
        db.add(location)
    location.location_type = payload.location.type
    location.label = payload.location.label
    location.lat = payload.location.lat
    location.lng = payload.location.lng
    db.commit()
    db.refresh(location)
    return location


@router.get("/history", response_model=list[DoorToDoorHistoryOut])
def list_history(
    watch_id: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DoorToDoorHistoryOut]:
    query = select(DoorToDoorSearchHistory).where(DoorToDoorSearchHistory.user_id == current_user.id)
    if watch_id:
        query = query.where(DoorToDoorSearchHistory.watch_id == watch_id)
    rows = list(db.scalars(query.order_by(DoorToDoorSearchHistory.created_at.desc(), DoorToDoorSearchHistory.id.desc()).limit(20)))
    chosen_rows = list(
        db.scalars(
            select(DoorToDoorChosenOption)
            .where(DoorToDoorChosenOption.user_id == current_user.id)
            .order_by(DoorToDoorChosenOption.chosen_at.desc(), DoorToDoorChosenOption.id.desc())
        )
    )
    chosen_by_history: dict[str, str] = {}
    for item in chosen_rows:
        if not item.history_id or item.history_id in chosen_by_history:
            continue
        chosen_by_history[item.history_id] = item.option_id
    return [_history_out(row, chosen_by_history.get(row.id), current_user.id) for row in rows]


def _safe_json_object(value: str, *, field_name: str, history_id: str, user_id: str) -> dict:
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        logger.warning(
            "door_to_door_history_invalid_json",
            extra={"history_id": history_id, "user_id": user_id, "field": field_name},
        )
        return {}
    if isinstance(parsed, dict):
        return parsed
    logger.warning(
        "door_to_door_history_invalid_json_shape",
        extra={"history_id": history_id, "user_id": user_id, "field": field_name},
    )
    return {}


def _history_out(row: DoorToDoorSearchHistory, chosen_option_id: str | None, user_id: str) -> DoorToDoorHistoryOut:
    origin = _safe_json_object(row.origin_json, field_name="origin_json", history_id=row.id, user_id=user_id)
    final_destination = _safe_json_object(
        row.final_destination_json, field_name="final_destination_json", history_id=row.id, user_id=user_id
    )
    summary = _safe_json_object(row.summary_json, field_name="summary_json", history_id=row.id, user_id=user_id)
    recommended = summary.get("recommended") or {}
    return DoorToDoorHistoryOut(
        id=row.id,
        watch_id=row.watch_id,
        origin_label=origin.get("label", "--"),
        final_destination_label=final_destination.get("label", "--"),
        created_at=row.created_at,
        recommended_option_id=summary.get("recommended_option_id"),
        recommended_label=recommended.get("label"),
        total_price_min=recommended.get("total_price_min"),
        total_price_max=recommended.get("total_price_max"),
        chosen_option_id=chosen_option_id,
    )


@router.post("/history/{history_id}/chosen", response_model=DoorToDoorChosenOptionOut)
def choose_option(
    history_id: str,
    payload: DoorToDoorChosenOptionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoorToDoorChosenOptionOut:
    history = db.scalar(
        select(DoorToDoorSearchHistory).where(
            DoorToDoorSearchHistory.id == history_id,
            DoorToDoorSearchHistory.user_id == current_user.id,
        )
    )
    if not history:
        raise HTTPException(status_code=404, detail="door_to_door_history_not_found")
    chosen = DoorToDoorChosenOption(
        user_id=current_user.id,
        watch_id=history.watch_id,
        history_id=history.id,
        option_id=payload.option_id,
        option_label=payload.option_label,
        option_summary_json=json.dumps(payload.option_summary, ensure_ascii=False),
    )
    db.add(chosen)
    db.commit()
    db.refresh(chosen)
    return DoorToDoorChosenOptionOut(
        id=chosen.id,
        watch_id=chosen.watch_id,
        history_id=chosen.history_id,
        option_id=chosen.option_id,
        option_label=chosen.option_label,
        chosen_at=chosen.chosen_at,
    )




