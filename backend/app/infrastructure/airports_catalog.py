from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Airport:
    iata: str
    icao: str | None
    name: str
    city: str
    country: str
    region: str | None
    latitude: float
    longitude: float
    timezone: str | None
    airport_type: str | None
    is_primary: bool
    source: str


@dataclass(frozen=True)
class ExpandedAirportCandidate:
    seed_iata: str
    expanded_iata: str
    is_seed: bool
    distance_km: float
    candidate_reason: str
    source_of_expansion: str


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "airports_master.json"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    a = sin(d_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return earth_radius_km * c


def _is_valid_iata(value: str) -> bool:
    cleaned = value.strip().upper()
    return len(cleaned) == 3 and cleaned.isalpha()


def _load_master_catalog() -> list[Airport]:
    if not DATA_PATH.exists():
        raise RuntimeError(f"airports_master_catalog_missing:{DATA_PATH}")
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("airports_master_catalog_invalid_format")

    out: list[Airport] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        iata = str(item.get("iata") or "").strip().upper()
        if not _is_valid_iata(iata):
            continue
        try:
            lat = float(item["latitude"])
            lon = float(item["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append(
            Airport(
                iata=iata,
                icao=str(item.get("icao") or "").strip().upper() or None,
                name=str(item.get("name") or iata),
                city=str(item.get("city") or ""),
                country=str(item.get("country") or ""),
                region=str(item.get("region") or "") or None,
                latitude=lat,
                longitude=lon,
                timezone=str(item.get("timezone") or "") or None,
                airport_type=str(item.get("airport_type") or "") or None,
                is_primary=bool(item.get("is_primary", False)),
                source=str(item.get("source") or "airports_master"),
            )
        )
    return out


AIRPORTS: list[Airport] = _load_master_catalog()
AIRPORT_BY_IATA = {airport.iata: airport for airport in AIRPORTS}


@lru_cache(maxsize=1024)
def get_airport(iata: str) -> Airport | None:
    return AIRPORT_BY_IATA.get(iata.upper().strip())


def resolve_seed_airport(iata: str) -> Airport:
    airport = get_airport(iata)
    if not airport:
        raise ValueError(f"unknown_seed_iata:{iata}")
    return airport


def nearby_airports(iata: str, radius_km: int, limit: int = 8) -> list[dict]:
    seed = resolve_seed_airport(iata)
    if radius_km < 10 or radius_km > 500:
        raise ValueError("radius_out_of_range")
    if limit < 1 or limit > 50:
        raise ValueError("limit_out_of_range")

    matches: list[tuple[Airport, float]] = []
    for airport in AIRPORTS:
        if airport.iata == seed.iata:
            continue
        distance = _haversine_km(seed.latitude, seed.longitude, airport.latitude, airport.longitude)
        if distance <= radius_km:
            matches.append((airport, distance))

    # Distance first, then prefer primary airports for ties
    matches.sort(key=lambda item: (item[1], 0 if item[0].is_primary else 1, item[0].iata))
    return [
        {
            "iata": airport.iata,
            "name": airport.name,
            "city": airport.city,
            "country": airport.country,
            "distance_km": round(distance, 1),
            "is_primary": airport.is_primary,
            "source": airport.source,
        }
        for airport, distance in matches[:limit]
    ]


def expand_side(
    seed_iata: str,
    include_nearby: bool,
    radius_km: int,
    max_candidates: int,
    exclusions: Iterable[str] | None = None,
) -> list[ExpandedAirportCandidate]:
    seed = resolve_seed_airport(seed_iata)
    excluded = {code.strip().upper() for code in (exclusions or []) if _is_valid_iata(code)}

    candidates: list[ExpandedAirportCandidate] = []
    if seed.iata not in excluded:
        candidates.append(
            ExpandedAirportCandidate(
                seed_iata=seed.iata,
                expanded_iata=seed.iata,
                is_seed=True,
                distance_km=0.0,
                candidate_reason="seed",
                source_of_expansion="catalog",
            )
        )

    if include_nearby:
        for neighbor in nearby_airports(seed.iata, radius_km=radius_km, limit=max(1, max_candidates * 3)):
            iata = neighbor["iata"].upper()
            if iata in excluded:
                continue
            if any(existing.expanded_iata == iata for existing in candidates):
                continue
            candidates.append(
                ExpandedAirportCandidate(
                    seed_iata=seed.iata,
                    expanded_iata=iata,
                    is_seed=False,
                    distance_km=float(neighbor["distance_km"]),
                    candidate_reason="nearby",
                    source_of_expansion="catalog",
                )
            )
            if len(candidates) >= max_candidates:
                break

    return candidates


def expand_airports(iatas: Iterable[str], radius_km: int, limit_per_seed: int = 6) -> list[str]:
    """Legacy adapter kept for compatibility with current endpoints."""
    out: list[str] = []
    seen: set[str] = set()
    for code in iatas:
        expanded = expand_side(code, include_nearby=True, radius_km=radius_km, max_candidates=limit_per_seed)
        for candidate in expanded:
            iata = candidate.expanded_iata
            if iata in seen:
                continue
            seen.add(iata)
            out.append(iata)
    return out


def airport_to_dict(airport: Airport) -> dict:
    return asdict(airport)
