import json
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.door_to_door.schemas import (
    DoorToDoorChosenOptionIn,
    DoorToDoorChosenOptionOut,
    DoorToDoorFlightOut,
    DoorToDoorHistoryOut,
    DoorToDoorSavedLocationIn,
    DoorToDoorSavedLocationOut,
    DoorToDoorSearchRequest,
    DoorToDoorSearchResponse,
    DoorToDoorSuggestionOut,
)
from app.door_to_door.services.search_service import DoorToDoorSearchService
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
    DoorToDoorSuggestionOut(id="city_almeria", type="city", label="Almería", subtitle="Ciudad de salida frecuente", lat=36.834, lng=-2.463),
    DoorToDoorSuggestionOut(id="station_almeria", type="station", label="Estación de Almería", subtitle="Tren y bus interurbano", lat=36.8402, lng=-2.4576),
    DoorToDoorSuggestionOut(id="airport_agp", type="airport", label="Aeropuerto de Málaga AGP", subtitle="Terminal de salida", lat=36.6749, lng=-4.4991),
    DoorToDoorSuggestionOut(id="airport_tsf", type="airport_only", label="Solo aeropuerto TSF", subtitle="Terminar al aterrizar, sin tramo terrestre", lat=45.6508, lng=12.1978),
    DoorToDoorSuggestionOut(id="city_treviso", type="city", label="Treviso centro", subtitle="Centro urbano desde TSF", lat=45.6669, lng=12.243),
    DoorToDoorSuggestionOut(id="city_venice", type="city", label="Venecia", subtitle="Destino final frecuente desde Treviso", lat=45.4408, lng=12.3155),
    DoorToDoorSuggestionOut(id="city_padua", type="city", label="Padua", subtitle="Ciudad cercana conectada por tren", lat=45.4064, lng=11.8768),
    DoorToDoorSuggestionOut(id="station_treviso", type="station", label="Treviso Centrale", subtitle="Estación principal", lat=45.6595, lng=12.2451),
]


def _get_watch(db: Session, user: User, watch_id: str) -> FlightWatch:
    watch = db.scalar(select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == user.id))
    if not watch or watch.status == "deleted":
        raise HTTPException(status_code=404, detail="watch_not_found")
    return watch


def _flight_context(db: Session, watch: FlightWatch) -> DoorToDoorFlightOut:
    latest = db.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.watch_id == watch.id)
        .order_by(PriceSnapshot.captured_at_utc.desc(), PriceSnapshot.id.desc())
    )
    confidence = "estimated"
    departure_clock = time(hour=14, minute=20)
    if latest and latest.departure_time_local:
        try:
            hour, minute = latest.departure_time_local.split(":", 1)
            departure_clock = time(hour=int(hour), minute=int(minute))
            confidence = "live"
        except ValueError:
            confidence = "estimated"
    departure = datetime.combine(watch.travel_date_local, departure_clock, tzinfo=MADRID)
    arrival = departure + timedelta(minutes=DEFAULT_FLIGHT_DURATION_MINUTES)
    return DoorToDoorFlightOut(
        origin_airport=watch.origin_iata,
        destination_airport=watch.destination_iata,
        departure_at=departure,
        arrival_at=arrival,
        flight_time_confidence=confidence,
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


@router.get("/suggestions", response_model=list[DoorToDoorSuggestionOut])
def suggestions(q: str = Query(default="", max_length=120)) -> list[DoorToDoorSuggestionOut]:
    query = q.strip().lower()
    if not query:
        return SUGGESTIONS
    return [item for item in SUGGESTIONS if query in item.label.lower() or query in item.subtitle.lower()]


@router.post("/search", response_model=DoorToDoorSearchResponse)
async def search_door_to_door(
    payload: DoorToDoorSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoorToDoorSearchResponse:
    watch = _get_watch(db, current_user, payload.flight_watch_id)
    if payload.save_origin_as_default:
        _upsert_saved_location(db, current_user.id, DoorToDoorSavedLocationIn(location=payload.origin))
    service = DoorToDoorSearchService()
    return await service.search(
        db=db,
        user_id=current_user.id,
        request=payload,
        flight=_flight_context(db, watch),
    )


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
        db.scalars(select(DoorToDoorChosenOption).where(DoorToDoorChosenOption.user_id == current_user.id))
    )
    chosen_by_history = {item.history_id: item.option_id for item in chosen_rows if item.history_id}
    return [_history_out(row, chosen_by_history.get(row.id)) for row in rows]


def _history_out(row: DoorToDoorSearchHistory, chosen_option_id: str | None) -> DoorToDoorHistoryOut:
    origin = json.loads(row.origin_json)
    final_destination = json.loads(row.final_destination_json)
    summary = json.loads(row.summary_json)
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
        risk_level=recommended.get("risk_level"),
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
