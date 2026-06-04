"""Optional Nominatim geocoder fallback for area-resolve.

Enabled when HOTEL_GEOCODER_ENABLED=true.
No external API key required — Nominatim is free with usage limits.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger("app.hotels.geocoder")

_NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org").rstrip("/")
_NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "ViruTracker/1.0")


def is_geocoder_enabled() -> bool:
    return os.getenv("HOTEL_GEOCODER_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def geocode_city(query: str) -> dict[str, object] | None:
    """Resolve a city/area name to coordinates using Nominatim.

    Returns None on failure or if geocoder is disabled.
    """
    if not is_geocoder_enabled():
        return None

    url = f"{_NOMINATIM_URL}/search"
    params: dict[str, str] = {
        "q": query,
        "format": "json",
        "limit": "3",
        "accept-language": "es",
    }

    try:
        time.sleep(1.0)  # Rate-limit: 1 req/s for Nominatim free tier
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": _NOMINATIM_USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
        results: list[dict[str, Any]] = response.json()
    except Exception as exc:
        logger.warning("nominatim_geocode_failed", extra={"query": query, "error": str(exc)})
        return None

    if not results:
        return None

    # Prefer results with "city" or "administrative" type
    best = results[0]
    for r in results:
        osm_type = r.get("type", "")
        if osm_type in {"city", "administrative"}:
            best = r
            break

    lat = float(best.get("lat", 0))
    lng = float(best.get("lon", 0))
    display_name: str = best.get("display_name", query)
    country_code: str = (best.get("country_code") or "").upper()

    # Extract a short label from display_name (first part before comma)
    area_label = display_name.split(",")[0].strip()

    return {
        "area_label": area_label,
        "latitude": round(lat, 4),
        "longitude": round(lng, 4),
        "country_code": country_code,
        "confidence": "medium",
        "source": "nominatim",
    }
