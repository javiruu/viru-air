from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import AppearancePreferenceIn, PreferenceIn, RegionPreferenceIn
from app.infrastructure.db.models import (
    User,
    UserPreference,
    UserPreferenceAppearance,
    UserPreferenceRegion,
)
from app.infrastructure.db.session import get_db

router = APIRouter()


@router.get("")
def get_preferences(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    pref = db.scalar(select(UserPreference).where(UserPreference.user_id == current_user.id))
    if not pref:
        return {
            "default_radius_km": 150,
            "include_stops_default": False,
            "include_nearby_origins_default": False,
            "include_nearby_destinations_default": False,
            "avoid_departure_before": None,
            "depart_before_default": None,
            "strict_filters_default": True,
            "preferred_currency": "EUR",
            "language": current_user.locale,
        }
    return {
        "default_radius_km": pref.default_radius_km,
        "include_stops_default": pref.include_stops_default,
        "include_nearby_origins_default": pref.include_nearby_origins_default,
        "include_nearby_destinations_default": pref.include_nearby_destinations_default,
        "avoid_departure_before": pref.avoid_departure_before,
        "depart_before_default": pref.depart_before_default,
        "strict_filters_default": pref.strict_filters_default,
        "preferred_currency": pref.preferred_currency,
        "language": pref.language,
    }


@router.get("/search")
def get_search_preferences(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    return get_preferences(db=db, current_user=current_user)


@router.put("")
def set_preferences(
    payload: PreferenceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    pref = db.scalar(select(UserPreference).where(UserPreference.user_id == current_user.id))
    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)
    pref.default_radius_km = payload.default_radius_km
    pref.include_stops_default = payload.include_stops_default
    pref.include_nearby_origins_default = payload.include_nearby_origins_default
    pref.include_nearby_destinations_default = payload.include_nearby_destinations_default
    pref.avoid_departure_before = payload.avoid_departure_before
    pref.depart_before_default = payload.depart_before_default
    pref.strict_filters_default = payload.strict_filters_default
    pref.preferred_currency = payload.preferred_currency
    pref.language = payload.language
    db.commit()
    return {"status": "ok"}


@router.put("/search")
def set_search_preferences(
    payload: PreferenceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return set_preferences(payload=payload, db=db, current_user=current_user)


@router.get("/appearance")
def get_appearance_preferences(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    pref = db.scalar(select(UserPreferenceAppearance).where(UserPreferenceAppearance.user_id == current_user.id))
    if not pref:
        return {
            "theme": "system",
            "density": "comfortable",
            "reduce_motion": False,
            "high_contrast": False,
        }
    return {
        "theme": pref.theme,
        "density": pref.density,
        "reduce_motion": pref.reduce_motion,
        "high_contrast": pref.high_contrast,
    }


@router.put("/appearance")
def set_appearance_preferences(
    payload: AppearancePreferenceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    pref = db.scalar(select(UserPreferenceAppearance).where(UserPreferenceAppearance.user_id == current_user.id))
    if not pref:
        pref = UserPreferenceAppearance(user_id=current_user.id)
        db.add(pref)
    pref.theme = payload.theme
    pref.density = payload.density
    pref.reduce_motion = payload.reduce_motion
    pref.high_contrast = payload.high_contrast
    db.commit()
    return {"status": "ok"}


@router.get("/region")
def get_region_preferences(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    pref = db.scalar(select(UserPreferenceRegion).where(UserPreferenceRegion.user_id == current_user.id))
    if not pref:
        return {
            "language": current_user.locale,
            "region": "ES",
            "time_format": "24h",
            "decimal_separator": ",",
            "currency": "EUR",
        }
    return {
        "language": pref.language,
        "region": pref.region,
        "time_format": pref.time_format,
        "decimal_separator": pref.decimal_separator,
        "currency": pref.currency,
    }


@router.put("/region")
def set_region_preferences(
    payload: RegionPreferenceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    pref = db.scalar(select(UserPreferenceRegion).where(UserPreferenceRegion.user_id == current_user.id))
    if not pref:
        pref = UserPreferenceRegion(user_id=current_user.id)
        db.add(pref)
    pref.language = payload.language
    pref.region = payload.region
    pref.time_format = payload.time_format
    pref.decimal_separator = payload.decimal_separator
    pref.currency = payload.currency
    current_user.locale = payload.language
    db.commit()
    return {"status": "ok"}
