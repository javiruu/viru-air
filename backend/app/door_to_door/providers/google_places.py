from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Sequence

import requests

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.schemas import DoorToDoorSuggestionOut

GOOGLE_PLACES_AUTOCOMPLETE_ENDPOINT = "https://places.googleapis.com/v1/places:autocomplete"
logger = logging.getLogger("app.door_to_door.google_places")


@dataclass(frozen=True)
class _CachedSuggestions:
    items: list[DoorToDoorSuggestionOut]
    expires_at: datetime


class GooglePlacesSuggestionsProvider:
    provider_name = "google_places"
    source_type = "api"

    def __init__(self) -> None:
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
        self.enabled = self._flag("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", False)
        self.timeout_seconds = float(os.getenv("DOOR_TO_DOOR_GOOGLE_PLACES_TIMEOUT_SECONDS", "4"))
        self.cache_ttl_seconds = int(os.getenv("DOOR_TO_DOOR_GOOGLE_PLACES_CACHE_TTL_SECONDS", "600"))
        self.max_cache_entries = max(int(os.getenv("DOOR_TO_DOOR_GOOGLE_PLACES_CACHE_MAX_ENTRIES", "500")), 50)
        self._cache: dict[str, _CachedSuggestions] = {}

    async def suggest(
        self,
        query: str,
        *,
        limit: int = 6,
        session_token: str | None = None,
        preferred_region_codes: Sequence[str] | None = None,
    ) -> list[DoorToDoorSuggestionOut]:
        normalized = query.strip()
        if not normalized:
            return []
        if not self.enabled or not self.api_key:
            return []

        normalized_regions = tuple(sorted({code.strip().lower() for code in (preferred_region_codes or []) if code}))
        token_fragment = (session_token or "").strip()[:32]
        cache_key = f"{normalized.lower()}|{','.join(normalized_regions)}|{token_fragment}"
        now = datetime.now(tz=UTC)
        self._prune_cache(now)
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > now:
            return cached.items[:limit]

        suggestions = await asyncio.to_thread(
            self._fetch_suggestions,
            normalized,
            limit,
            session_token,
        )
        if suggestions:
            self._cache[cache_key] = _CachedSuggestions(
                items=suggestions,
                expires_at=now + timedelta(seconds=self.cache_ttl_seconds),
            )
            self._prune_cache(now)
        return suggestions

    def _prune_cache(self, now: datetime) -> None:
        if not self._cache:
            return
        expired_keys = [key for key, value in self._cache.items() if value.expires_at <= now]
        for key in expired_keys:
            self._cache.pop(key, None)
        if len(self._cache) <= self.max_cache_entries:
            return
        overflow = len(self._cache) - self.max_cache_entries
        keys_by_expiry = sorted(self._cache.keys(), key=lambda key: self._cache[key].expires_at)
        for key in keys_by_expiry[:overflow]:
            self._cache.pop(key, None)

    async def healthcheck(self) -> ProviderHealth:
        if not self.enabled:
            return ProviderHealth(
                provider=self.provider_name,
                status="disabled",
                source_type=self.source_type,
                confidence="unavailable",
                message="Google Places desactivado por flag.",
            )
        if not self.api_key:
            return ProviderHealth(
                provider=self.provider_name,
                status="missing_api_key",
                source_type=self.source_type,
                confidence="unavailable",
                message="GOOGLE_MAPS_API_KEY no configurada.",
            )
        return ProviderHealth(
            provider=self.provider_name,
            status="ok",
            source_type=self.source_type,
            confidence="live",
            message="Google Places listo para sugerencias reales.",
        )

    def _fetch_suggestions(
        self,
        query: str,
        limit: int,
        session_token: str | None = None,
    ) -> list[DoorToDoorSuggestionOut]:
        body: dict[str, object] = {
            "input": query,
            "languageCode": "es",
        }
        if session_token:
            body["sessionToken"] = session_token

        response = requests.post(
            GOOGLE_PLACES_AUTOCOMPLETE_ENDPOINT,
            json=body,
            headers={
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": (
                    "suggestions.placePrediction.placeId,"
                    "suggestions.placePrediction.text.text,"
                    "suggestions.placePrediction.structuredFormat.mainText.text,"
                    "suggestions.placePrediction.structuredFormat.secondaryText.text"
                ),
            },
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            logger.warning(
                "google_places_autocomplete_failed status=%s body=%s",
                response.status_code,
                (response.text or "")[:300],
            )
            return []

        payload = response.json()
        suggestions_raw = payload.get("suggestions") or []
        items: list[DoorToDoorSuggestionOut] = []
        for index, entry in enumerate(suggestions_raw[:limit]):
            prediction = entry.get("placePrediction") or entry.get("queryPrediction") or {}
            place_id = prediction.get("placeId")
            text_block = prediction.get("text") or prediction.get("structuredFormat", {}).get("mainText") or {}
            label = text_block.get("text") or ""
            if not isinstance(label, str) or not label.strip():
                continue
            structured = prediction.get("structuredFormat") or {}
            subtitle = (structured.get("secondaryText") or {}).get("text")
            if not isinstance(subtitle, str) or not subtitle.strip():
                subtitle = "Proveedor de geocoding"
            items.append(
                DoorToDoorSuggestionOut(
                    id=f"google_places_{place_id or index}",
                    type="city",
                    label=label,
                    subtitle=subtitle,
                    source_type="api",
                    place_id=place_id,
                )
            )
        return items

    @staticmethod
    def _flag(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}
