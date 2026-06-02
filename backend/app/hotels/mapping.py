from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hotels.contracts import ProviderHotelRecord
from app.hotels.geo import haversine_km
from app.hotels.normalization import HotelNormalizationService
from app.infrastructure.db.models import HotelProperty


@dataclass
class HotelMappingResult:
    hotel: HotelProperty
    confidence_score: float
    is_ambiguous: bool
    matched_existing: bool


class HotelMappingService:
    HIGH_CONFIDENCE_THRESHOLD = 0.80
    MEDIUM_CONFIDENCE_THRESHOLD = 0.55

    def __init__(self, db: Session) -> None:
        self._db = db

    def map_or_create(self, record: ProviderHotelRecord) -> HotelMappingResult:
        normalized_name = HotelNormalizationService.normalize_text(record.raw_name)
        normalized_city = HotelNormalizationService.normalize_city(record.city)
        country_code = HotelNormalizationService.normalize_country_code(record.country_code)

        candidates = self._db.scalars(
            select(HotelProperty).where(HotelProperty.country_code == country_code)
        ).all()

        best_candidate: HotelProperty | None = None
        best_score = 0.0
        for candidate in candidates:
            score = self._score_candidate(record, normalized_name, normalized_city, candidate)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate is not None and best_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            return HotelMappingResult(
                hotel=best_candidate,
                confidence_score=best_score,
                is_ambiguous=False,
                matched_existing=True,
            )

        created_hotel = HotelProperty(
            canonical_name=record.raw_name.strip(),
            normalized_name=normalized_name,
            address=(record.raw_address or "").strip() or None,
            city=record.city.strip(),
            country_code=country_code,
            latitude=record.latitude,
            longitude=record.longitude,
            stars=record.stars,
        )
        self._db.add(created_hotel)
        self._db.flush()

        return HotelMappingResult(
            hotel=created_hotel,
            confidence_score=best_score,
            is_ambiguous=best_candidate is not None and best_score >= self.MEDIUM_CONFIDENCE_THRESHOLD,
            matched_existing=False,
        )

    def _score_candidate(
        self,
        record: ProviderHotelRecord,
        normalized_name: str,
        normalized_city: str,
        candidate: HotelProperty,
    ) -> float:
        candidate_name = HotelNormalizationService.normalize_text(candidate.canonical_name)
        candidate_city = HotelNormalizationService.normalize_city(candidate.city)

        score = 0.0
        if normalized_name and candidate_name == normalized_name:
            score += 0.65
        elif normalized_name and (candidate_name.startswith(normalized_name) or normalized_name.startswith(candidate_name)):
            score += 0.50
        elif normalized_name and self._token_overlap(normalized_name, candidate_name) >= 0.60:
            score += 0.40

        if normalized_city and candidate_city == normalized_city:
            score += 0.20

        if record.latitude is not None and record.longitude is not None and candidate.latitude is not None and candidate.longitude is not None:
            distance_km = haversine_km(record.latitude, record.longitude, float(candidate.latitude), float(candidate.longitude))
            if distance_km <= 0.30:
                score += 0.15
            elif distance_km <= 1.00:
                score += 0.10
            elif distance_km > 20.0:
                score -= 0.20

        return max(0.0, min(score, 1.0))

    @staticmethod
    def _token_overlap(left: str, right: str) -> float:
        left_tokens = {t for t in left.split(" ") if t}
        right_tokens = {t for t in right.split(" ") if t}
        if not left_tokens or not right_tokens:
            return 0.0
        overlap = len(left_tokens.intersection(right_tokens))
        return overlap / max(len(left_tokens), len(right_tokens))

