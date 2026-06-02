from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import HotelCompSet, HotelCompSetMember, HotelProperty


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_km * c


@dataclass
class HotelNearbySuggestion:
    hotel_id: str
    canonical_name: str
    city: str
    country_code: str
    stars: int | None
    distance_km: float


class HotelGeoService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def suggest_for_comp_set(
        self,
        *,
        user_id: str,
        comp_set_id: str,
        radius_km: int = 5,
        limit: int = 6,
    ) -> list[HotelNearbySuggestion]:
        comp_set = self._db.scalar(select(HotelCompSet).where(HotelCompSet.id == comp_set_id))
        if not comp_set:
            raise ValueError("hotel_comp_set_not_found")
        if comp_set.user_id != user_id:
            raise PermissionError("not_allowed")

        anchor = self._db.get(HotelProperty, comp_set.anchor_hotel_id)
        if not anchor:
            raise ValueError("hotel_not_found")
        if anchor.latitude is None or anchor.longitude is None:
            raise ValueError("hotel_comp_set_anchor_missing_coordinates")

        excluded_ids = {
            comp_set.anchor_hotel_id,
            *self._db.scalars(
                select(HotelCompSetMember.hotel_id).where(HotelCompSetMember.comp_set_id == comp_set_id)
            ).all(),
        }

        anchor_lat = float(anchor.latitude)
        anchor_lng = float(anchor.longitude)

        candidates = self._db.scalars(
            select(HotelProperty).where(
                HotelProperty.latitude.is_not(None),
                HotelProperty.longitude.is_not(None),
            )
        ).all()

        suggestions: list[HotelNearbySuggestion] = []
        for candidate in candidates:
            if candidate.id in excluded_ids:
                continue

            distance = round(
                haversine_km(
                    anchor_lat,
                    anchor_lng,
                    float(candidate.latitude),
                    float(candidate.longitude),
                ),
                1,
            )
            if distance > radius_km:
                continue

            suggestions.append(
                HotelNearbySuggestion(
                    hotel_id=candidate.id,
                    canonical_name=candidate.canonical_name,
                    city=candidate.city,
                    country_code=candidate.country_code,
                    stars=candidate.stars,
                    distance_km=distance,
                )
            )

        suggestions.sort(key=lambda item: (item.distance_km, item.canonical_name.lower(), item.hotel_id))
        return suggestions[:limit]
