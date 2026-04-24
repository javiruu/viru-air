from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

import requests
from fastapi import APIRouter, HTTPException

from app.infrastructure.airports_catalog import (
    country_code_from_airport,
    list_seed_airports,
    list_seed_countries,
    nearby_airports,
)

router = APIRouter()

BASE_URL = "https://www.airportroutes.com/api"


def _get_json(url: str) -> Any:
    try:
        resp = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"airports_unavailable:{exc}") from exc


def _extract_iata(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("iata", "iata_code", "iataCode", "IATA"):
        value = payload.get(key)
        if isinstance(value, str) and len(value) == 3:
            return value.upper()
    for key in ("airport_iata", "destination_iata", "dest_iata", "arrival_iata", "iataCodeTo"):
        value = payload.get(key)
        if isinstance(value, str) and len(value) == 3:
            return value.upper()
    return None


def _extract_icao(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("icao", "icao_code", "icaoCode", "ICAO"):
        value = payload.get(key)
        if isinstance(value, str) and len(value) == 4:
            return value.upper()
    return None


def _validate_iata(value: str) -> str:
    cleaned = value.strip().upper()
    if len(cleaned) != 3 or not cleaned.isalpha():
        raise HTTPException(status_code=400, detail="iata_invalido")
    return cleaned


@lru_cache(maxsize=512)
def _lookup_airport_by_iata(iata: str) -> dict[str, Any] | None:
    query = iata.upper().strip()
    data = _get_json(f"{BASE_URL}/search-airports/?q={query}")
    if isinstance(data, dict):
        results = data.get("results") or data.get("airports") or []
    else:
        results = data or []
    for entry in results:
        entry_iata = _extract_iata(entry)
        if entry_iata == query:
            return entry
    return results[0] if results else None


def _extract_routes_iata(routes_payload: Any) -> list[str]:
    if isinstance(routes_payload, dict):
        routes = (
            routes_payload.get("routes")
            or routes_payload.get("results")
            or routes_payload.get("data")
            or []
        )
    else:
        routes = routes_payload or []

    out: list[str] = []
    for route in routes:
        if isinstance(route, dict):
            direct = _extract_iata(route)
            if direct:
                out.append(direct)
                continue
            for key in ("airport", "destination", "to", "arrival", "dest"):
                nested = route.get(key)
                nested_iata = _extract_iata(nested)
                if nested_iata:
                    out.append(nested_iata)
                    break
    return sorted(set(out))


def _compatible_from_iata(iata: str) -> list[str]:
    entry = _lookup_airport_by_iata(iata)
    if not entry:
        return []
    icao = _extract_icao(entry)
    if not icao:
        return []
    routes_payload = _get_json(f"{BASE_URL}/routes/?icao={icao}")
    return _extract_routes_iata(routes_payload)


@router.get("/compatible")
def compatible_airports(
    travel_date: date,
    origin_iata: str | None = None,
    destination_iata: str | None = None,
) -> dict[str, Any]:
    if origin_iata and destination_iata:
        raise HTTPException(status_code=400, detail="provide_origin_or_destination_only")
    seed = origin_iata or destination_iata
    if not seed:
        raise HTTPException(status_code=400, detail="missing_origin_or_destination")
    compatible = _compatible_from_iata(seed)
    return {
        "seed_iata": seed.upper(),
        "travel_date": str(travel_date),
        "compatible_iata": compatible,
        "source": "airportroutes",
    }


@router.get("/nearby")
def nearby(
    iata: str,
    radius_km: int = 150,
    limit: int = 8,
) -> dict[str, Any]:
    code = _validate_iata(iata)
    if radius_km < 10 or radius_km > 500:
        raise HTTPException(status_code=400, detail="radius_invalido")
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit_invalido")
    try:
        matches = nearby_airports(code, radius_km, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "seed_iata": code,
        "radius_km": radius_km,
        "nearby": matches,
        "count": len(matches),
        "source": "catalog_master",
    }


@router.get("/seeds")
def list_seed_airports_route(
    q: str | None = None,
    country_code: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    effective_limit: int | None = None
    if limit is not None:
        if limit < 1:
            raise HTTPException(status_code=400, detail="limit_invalido")
        effective_limit = min(limit, 500)
    elif q or country_code or offset > 0:
        effective_limit = 120

    page, total, next_offset = list_seed_airports(
        query=q,
        country_code=country_code,
        limit=effective_limit,
        offset=offset,
    )

    items = [
        {
            "iata": airport.iata,
            "name": airport.name,
            "municipality": airport.city,
            "country_code": country_code_from_airport(airport),
            "iso_region": airport.region or "",
            "type": airport.airport_type or "",
            "is_primary": airport.is_primary,
            "source": airport.source,
        }
        for airport in page
    ]
    response: dict[str, Any] = {
        "items": items,
        "count": len(items),
        "total": total,
        "source": "catalog_master",
    }
    if next_offset is not None:
        response["next_offset"] = next_offset
    return response


@router.get("/countries")
def list_seed_countries_route() -> dict[str, Any]:
    items = list_seed_countries()
    return {
        "items": items,
        "count": len(items),
        "source": "catalog_master",
    }
