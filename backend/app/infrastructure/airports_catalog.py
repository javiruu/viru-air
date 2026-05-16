from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Iterable

from app.infrastructure.db.session import SessionLocal
from app.infrastructure.db.models import Airport as DbAirport


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


def _ensure_seed_from_master() -> None:
    """Re-seed the airport table from airports_master.json if count mismatches.

    Runs once at import time to guarantee the DB always reflects
    the curated Ryanair-only master list, preventing stale non-Ryanair
    airports from leaking into the API and frontend.
    """
    import logging

    logger = logging.getLogger("app.airports_catalog")

    if not DATA_PATH.exists():
        logger.warning("airports_master.json not found at %s — skipping auto-seed", DATA_PATH)
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    master_count = len(master_data)
    master_iatas = {row["iata"] for row in master_data}

    from sqlalchemy import func, select, delete
    from app.infrastructure.db.session import Base, engine

    # Ensure table exists
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db_count = db.scalar(select(func.count()).select_from(DbAirport))
        if db_count is not None and db_count == master_count:
            db_iatas_rows = db.execute(select(DbAirport.iata)).all()
            db_iatas = {row[0] for row in db_iatas_rows}
            if db_iatas == master_iatas:
                return  # DB is in sync

        logger.info(
            "Airport catalog mismatch (db=%s, master=%s) — re-seeding from airports_master.json",
            db_count,
            master_count,
        )
        db.execute(delete(DbAirport))
        db.flush()

        for row in master_data:
            db.add(DbAirport(
                iata=row["iata"],
                icao=row.get("icao"),
                name=row["name"],
                city=row["city"],
                country=row["country"],
                region=row.get("region"),
                latitude=row["latitude"],
                longitude=row["longitude"],
                timezone=row.get("timezone"),
                airport_type=row.get("airport_type"),
                is_primary=row.get("is_primary", False),
                source=row.get("source", "ryanair_airports"),
            ))
        db.commit()
        logger.info("Seeded %d Ryanair-supported airports.", master_count)
    except Exception:
        db.rollback()
        logger.exception("Failed to auto-seed airports — continuing with existing DB data")
    finally:
        db.close()


def _load_master_catalog() -> list[Airport]:
    _ensure_seed_from_master()

    db = SessionLocal()
    try:
        db_airports = db.query(DbAirport).all()
    finally:
        db.close()

    out: list[Airport] = []
    for item in db_airports:
        out.append(
            Airport(
                iata=item.iata,
                icao=item.icao,
                name=item.name,
                city=item.city,
                country=item.country,
                region=item.region,
                latitude=float(item.latitude),
                longitude=float(item.longitude),
                timezone=item.timezone,
                airport_type=item.airport_type,
                is_primary=bool(item.is_primary),
                source=item.source,
            )
        )
    return out


def country_code_from_airport(airport: Airport) -> str:
    region = (airport.region or "").strip().upper()
    if "-" in region:
        prefix = region.split("-", 1)[0].strip()
        if len(prefix) == 2 and prefix.isalpha():
            return prefix
    country = (airport.country or "").strip().upper()
    if len(country) == 2 and country.isalpha():
        return country
    return ""


AIRPORTS: list[Airport] = _load_master_catalog()
AIRPORT_BY_IATA = {airport.iata: airport for airport in AIRPORTS}
AIRPORTS_SORTED = sorted(
    AIRPORTS,
    key=lambda airport: (
        country_code_from_airport(airport),
        airport.city,
        airport.name,
        airport.iata,
    ),
)


@lru_cache(maxsize=1024)
def get_airport(iata: str) -> Airport | None:
    return AIRPORT_BY_IATA.get(iata.upper().strip())


def _airport_matches_query(airport: Airport, normalized_query: str) -> bool:
    if not normalized_query:
        return True
    return normalized_query in " ".join(
        [
            airport.iata,
            airport.name,
            airport.city,
            airport.country,
            airport.region or "",
        ]
    ).lower()


def _query_rank(airport: Airport, normalized_query: str) -> tuple[int, str, str, str]:
    if not normalized_query:
        return (0, country_code_from_airport(airport), airport.city, airport.iata)
    iata = airport.iata.lower()
    name = airport.name.lower()
    city = airport.city.lower()
    if iata == normalized_query:
        rank = 0
    elif iata.startswith(normalized_query):
        rank = 1
    elif name.startswith(normalized_query) or city.startswith(normalized_query):
        rank = 2
    else:
        rank = 3
    return (rank, country_code_from_airport(airport), airport.city, airport.iata)


def list_seed_airports(
    *,
    query: str | None = None,
    country_code: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[Airport], int, int | None]:
    normalized_query = (query or "").strip().lower()
    normalized_country = (country_code or "").strip().upper()
    if offset < 0:
        offset = 0

    filtered = [
        airport
        for airport in AIRPORTS_SORTED
        if (not normalized_country or country_code_from_airport(airport) == normalized_country)
        and _airport_matches_query(airport, normalized_query)
    ]
    if normalized_query:
        filtered.sort(key=lambda airport: _query_rank(airport, normalized_query))
    total = len(filtered)

    if limit is None:
        return filtered[offset:], total, None

    effective_limit = max(1, limit)
    page = filtered[offset : offset + effective_limit]
    next_offset = offset + len(page)
    if next_offset >= total:
        next_offset = None
    return page, total, next_offset


def list_seed_countries() -> list[dict[str, object]]:
    counters: dict[str, int] = {}
    names: dict[str, str] = {}
    for airport in AIRPORTS:
        code = country_code_from_airport(airport)
        if not code:
            continue
        counters[code] = counters.get(code, 0) + 1
        current_name = names.get(code)
        if not current_name and airport.country:
            names[code] = airport.country
    rows = [
        {"code": code, "name": names.get(code, code), "airport_count": count}
        for code, count in counters.items()
    ]
    rows.sort(key=lambda item: (str(item["name"]), str(item["code"])))
    return rows


def resolve_seed_airport(iata: str) -> Airport:
    airport = get_airport(iata)
    if not airport:
        raise ValueError(f"unknown_seed_iata:{iata}")
    return airport


def nearby_airports(iata: str, radius_km: int, limit: int = 8) -> list[dict]:
    seed = resolve_seed_airport(iata)
    if radius_km < 10 or radius_km > 500:
        raise ValueError("radius_out_of_range")
    if limit < 1 or limit > 300:
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
