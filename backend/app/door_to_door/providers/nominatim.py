from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Sequence

import requests

from app.door_to_door.schemas import DoorToDoorLocationType, DoorToDoorSuggestionOut

logger = logging.getLogger("app.door_to_door.nominatim")


@dataclass(frozen=True)
class _CachedSuggestions:
    items: list[DoorToDoorSuggestionOut]
    expires_at: datetime


class NominatimSuggestionsProvider:
    provider_name = "nominatim"
    source_type = "open_data"

    def __init__(self) -> None:
        app_env = os.getenv("APP_ENV", "local").strip().lower()
        enabled_default = app_env in {"local", "dev", "development", "test"}
        self.enabled = self._flag("DOOR_TO_DOOR_ENABLE_NOMINATIM_SUGGESTIONS", enabled_default)
        self.timeout_seconds = float(os.getenv("DOOR_TO_DOOR_NOMINATIM_TIMEOUT_SECONDS", "3.5"))
        self.base_url = os.getenv("DOOR_TO_DOOR_NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org/search").strip()
        self.cache_ttl_seconds = int(os.getenv("DOOR_TO_DOOR_NOMINATIM_CACHE_TTL_SECONDS", "600"))
        self.max_cache_entries = max(int(os.getenv("DOOR_TO_DOOR_NOMINATIM_CACHE_MAX_ENTRIES", "500")), 50)
        self.user_agent = os.getenv(
            "DOOR_TO_DOOR_NOMINATIM_USER_AGENT",
            "viru-air/1.0 (door-to-door suggestions)",
        ).strip()
        self._cache: dict[str, _CachedSuggestions] = {}

    async def suggest(
        self,
        query: str,
        *,
        limit: int = 6,
        session_token: str | None = None,  # parity with google provider
        preferred_region_codes: Sequence[str] | None = None,
    ) -> list[DoorToDoorSuggestionOut]:
        del session_token
        normalized = self._normalize_query(query)
        if not normalized or not self.enabled:
            return []

        normalized_regions = tuple(sorted({code.strip().lower() for code in (preferred_region_codes or []) if code}))
        cache_key = f"{normalized.lower()}|{','.join(normalized_regions)}"
        now = datetime.now(tz=UTC)
        self._prune_cache(now)
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > now:
            return cached.items[:limit]

        items = await asyncio.to_thread(
            self._fetch_suggestions,
            normalized,
            limit,
        )
        if not items:
            return []

        ranked = self._rank_by_preferred_region(items, normalized_regions)
        self._cache[cache_key] = _CachedSuggestions(
            items=ranked,
            expires_at=now + timedelta(seconds=self.cache_ttl_seconds),
        )
        self._prune_cache(now)
        return ranked[:limit]

    def _fetch_suggestions(self, query: str, limit: int) -> list[DoorToDoorSuggestionOut]:
        try:
            params: dict[str, str | int] = {
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": max(limit * 2, 8),
            }
            response = requests.get(
                self.base_url,
                params=params,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Language": "es,en",
                },
                timeout=self.timeout_seconds,
            )
        except requests.RequestException:
            logger.exception("nominatim_suggestions_request_failed")
            return []

        if response.status_code >= 400:
            logger.warning(
                "nominatim_suggestions_failed status=%s body=%s",
                response.status_code,
                (response.text or "")[:300],
            )
            return []

        try:
            payload = response.json()
        except ValueError:
            logger.warning("nominatim_suggestions_invalid_json")
            return []
        if not isinstance(payload, list):
            return []

        items: list[DoorToDoorSuggestionOut] = []
        for index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                continue
            suggestion = self._normalize_item(raw, index=index)
            if suggestion is not None:
                items.append(suggestion)
        return items

    def _normalize_item(self, raw: dict[str, Any], *, index: int) -> DoorToDoorSuggestionOut | None:
        label = str(raw.get("display_name") or "").strip()
        if not label:
            return None

        raw_address = raw.get("address")
        address: dict[str, Any] = raw_address if isinstance(raw_address, dict) else {}
        city = str(address.get("city") or address.get("town") or address.get("village") or "").strip()
        country = str(address.get("country") or "").strip()
        subtitle_parts = [part for part in [city, country] if part]
        subtitle = ", ".join(subtitle_parts) if subtitle_parts else "OpenStreetMap"

        place_class = str(raw.get("class") or "").lower()
        osm_type = str(raw.get("type") or "").lower()
        location_type: DoorToDoorLocationType = "address"
        if place_class in {"aeroway"} or "airport" in osm_type:
            location_type = "airport"
        elif place_class in {"railway", "public_transport"} or osm_type in {"station", "halt"}:
            location_type = "station"
        elif place_class in {"place", "boundary"}:
            location_type = "city"

        lat = self._parse_float(raw.get("lat"))
        lng = self._parse_float(raw.get("lon"))
        place_id = str(raw.get("place_id") or raw.get("osm_id") or f"nominatim_{index}")
        return DoorToDoorSuggestionOut(
            id=f"nominatim_{place_id}",
            type=location_type,
            label=label[:180],
            subtitle=subtitle[:180],
            source_type="open_data",
            lat=lat,
            lng=lng,
            place_id=f"osm:{place_id}",
        )

    @staticmethod
    def _normalize_query(raw_query: str) -> str:
        return " ".join(raw_query.strip().split())[:180]

    @staticmethod
    def _parse_float(value: object) -> float | None:
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_region_code(item: DoorToDoorSuggestionOut) -> str | None:
        subtitle = item.subtitle.strip()
        if not subtitle:
            return None
        country_part = subtitle.split(",")[-1].strip().lower()
        if len(country_part) == 2 and country_part.isalpha():
            return country_part
        country_map = {
            "spain": "es",
            "españa": "es",
            "italy": "it",
            "italia": "it",
            "france": "fr",
            "portugal": "pt",
            "germany": "de",
            "united kingdom": "gb",
            "uk": "gb",
            "united states": "us",
        }
        return country_map.get(country_part)

    def _rank_by_preferred_region(
        self,
        items: list[DoorToDoorSuggestionOut],
        preferred_region_codes: Sequence[str],
    ) -> list[DoorToDoorSuggestionOut]:
        preferred = {code.strip().lower() for code in preferred_region_codes if code}
        if not preferred:
            return items
        ranked = sorted(
            items,
            key=lambda item: 0 if (self._extract_region_code(item) in preferred) else 1,
        )
        return ranked

    def _prune_cache(self, now: datetime) -> None:
        if not self._cache:
            return
        expired = [key for key, value in self._cache.items() if value.expires_at <= now]
        for key in expired:
            self._cache.pop(key, None)
        if len(self._cache) <= self.max_cache_entries:
            return
        overflow = len(self._cache) - self.max_cache_entries
        keys_by_expiry = sorted(self._cache.keys(), key=lambda key: self._cache[key].expires_at)
        for key in keys_by_expiry[:overflow]:
            self._cache.pop(key, None)

    @staticmethod
    def _flag(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}
