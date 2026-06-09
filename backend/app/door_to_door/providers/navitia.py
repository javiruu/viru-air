"""Navitia provider: search public transport journeys via the Navitia API.

Navitia (navitia.io) is an open-source multi-modal transport API covering many
European regions including Spain and Italy. It returns real transit schedules
with sections (walking, public_transport, etc.), duration, and transfer count.

Returns legs with real transit schedules, without inventing price or purchase
availability. Falls back gracefully when the API key is missing or coverage is
unavailable.

Granular warnings:
- NAVITIA_API_KEY_MISSING: no API key configured
- NAVITIA_API_ERROR: API returned an error
- NAVITIA_NO_COVERAGE: no coverage found for the origin/destination region
- NAVITIA_NO_JOURNEYS: coverage exists but no journeys match the query
- NAVITIA_PARTIAL_COVERAGE: only one leg (outbound/inbound) has coverage
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorConfidence,
    DoorToDoorLegOut,
    DoorToDoorMode,
    DoorToDoorOptionOut,
    DoorToDoorPriceOut,
    DoorToDoorSourceOut,
)

logger = logging.getLogger("app.door_to_door.navitia")

NAVITIA_BASE_URL = "https://api.navitia.io/v1"
NAVITIA_TIMEOUT_SECONDS = 8.0

# Airport coordinates (same set as google_routes provider)
_AIRPORT_COORDS: dict[str, tuple[float, float]] = {
    "AGP": (36.675, -4.499),
    "ALC": (38.282, -0.558),
    "AMS": (52.308, 4.764),
    "BCN": (41.297, 2.078),
    "BGY": (45.674, 9.704),
    "BIO": (43.301, -2.911),
    "BRU": (50.901, 4.484),
    "CDG": (49.010, 2.548),
    "CRL": (50.459, 4.454),
    "FCO": (41.800, 12.239),
    "GRO": (41.901, 2.761),
    "GRX": (37.189, -3.777),
    "LEI": (36.844, -2.370),
    "LGW": (51.153, -0.182),
    "LTN": (51.875, -0.368),
    "MAD": (40.472, -3.563),
    "MXP": (45.631, 8.728),
    "ORY": (48.723, 2.379),
    "PMI": (39.552, 2.738),
    "REU": (41.147, 1.167),
    "STN": (51.885, 0.235),
    "SVQ": (37.418, -5.899),
    "TSF": (45.651, 12.199),
    "VCE": (45.505, 12.352),
    "VLC": (39.489, -0.482),
    "ZAZ": (41.666, -1.042),
}


@dataclass
class _CoverageInfo:
    id: str
    name: str
    shape: str | None  # WKT polygon
    admin_level: int | None
    parent_id: str | None


@dataclass
class _JourneySection:
    mode: str
    from_name: str
    to_name: str
    departure_dt: datetime
    arrival_dt: datetime
    duration_seconds: int
    route_name: str | None
    network: str | None


@dataclass
class _JourneyResult:
    duration_seconds: int
    departure_dt: datetime
    arrival_dt: datetime
    transfers: int
    sections: list[_JourneySection]


class NavitiaProvider(DoorToDoorProvider):
    provider_name = "navitia"
    source_type = "api"

    def __init__(self) -> None:
        super().__init__()
        self.api_key = os.getenv("NAVITIA_API_KEY", "").strip()
        self.enabled = self._flag("DOOR_TO_DOOR_ENABLE_NAVITIA", False)
        self.timeout_seconds = float(
            os.getenv("DOOR_TO_DOOR_NAVITIA_TIMEOUT_SECONDS", str(NAVITIA_TIMEOUT_SECONDS))
        )
        self._coverages: list[_CoverageInfo] | None = None
        self._coverage_cache: dict[tuple[float, float], str | None] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        if not self.enabled or not self.api_key:
            if not self.api_key:
                self.push_warning(
                    "NAVITIA_API_KEY_MISSING",
                    "Navitia no esta configurado. Define NAVITIA_API_KEY en tu .env para activarlo.",
                )
            return []

        flight = query.flight
        checked_at = query.checked_at

        # Resolve airport coordinates
        origin_airport_coords = _AIRPORT_COORDS.get(flight.origin_airport.upper())
        dest_airport_coords = _AIRPORT_COORDS.get(flight.destination_airport.upper())

        if not origin_airport_coords:
            self.push_warning(
                "NAVITIA_NO_COVERAGE",
                f"No se han podido resolver coordenadas para el aeropuerto {flight.origin_airport}.",
            )
            return []

        # Ensure coverages are loaded
        await self._load_coverages()

        outbound_journeys: list[_JourneyResult] = []
        inbound_journeys: list[_JourneyResult] = []

        # Outbound: origin -> departure airport
        if query.origin.lat is not None and query.origin.lng is not None:
            origin_coords = (float(query.origin.lat), float(query.origin.lng))
            coverage_id = await self._find_coverage_for_point(origin_coords)
            if coverage_id and origin_airport_coords:
                airport_buffer = max(query.preferences.min_airport_buffer_minutes, 90)
                latest_arrival = flight.departure_at - timedelta(minutes=airport_buffer)
                # Navitia returns timezone-naive local times. Strip tz from flight
                # times for comparison (safe approximation for transit scheduling).
                latest_arrival_naive = latest_arrival.replace(tzinfo=None) if latest_arrival.tzinfo else latest_arrival
                journeys = await self._search_journeys(
                    coverage_id=coverage_id,
                    from_coords=origin_coords,
                    to_coords=origin_airport_coords,
                    datetime_ref=flight.departure_at,
                    datetime_is_departure=True,
                )
                outbound_journeys = [
                    j for j in journeys
                    if j.arrival_dt <= latest_arrival_naive
                ]
            else:
                self.push_warning(
                    "NAVITIA_NO_COVERAGE",
                    f"No se encontro cobertura Navitia para el origen «{query.origin.label}».",
                )

        # Inbound: arrival airport -> final destination
        search_inbound = query.final_destination.type != "airport_only"
        if search_inbound and query.final_destination.lat is not None and query.final_destination.lng is not None:
            dest_coords = (float(query.final_destination.lat), float(query.final_destination.lng))
            coverage_id = await self._find_coverage_for_point(dest_coords)
            if coverage_id and dest_airport_coords:
                earliest_departure = flight.arrival_at + timedelta(minutes=30)
                earliest_departure_naive = earliest_departure.replace(tzinfo=None) if earliest_departure.tzinfo else earliest_departure
                journeys = await self._search_journeys(
                    coverage_id=coverage_id,
                    from_coords=dest_airport_coords,
                    to_coords=dest_coords,
                    datetime_ref=flight.arrival_at,
                    datetime_is_departure=False,
                )
                inbound_journeys = [
                    j for j in journeys
                    if j.departure_dt >= earliest_departure_naive
                ]
            elif not query.final_destination.type == "airport_only":
                self.push_warning(
                    "NAVITIA_NO_COVERAGE",
                    f"No se encontro cobertura Navitia para el destino «{query.final_destination.label}».",
                )

        # No journeys found at all
        if not outbound_journeys and not inbound_journeys:
            if not any(w.code == "NAVITIA_NO_COVERAGE" for w in self._warnings):
                self.push_warning(
                    "NAVITIA_NO_JOURNEYS",
                    "Navitia tiene cobertura en esta zona pero no se encontraron viajes "
                    "de transporte publico para esta ruta y horario.",
                )
            return []

        # Partial coverage warning
        if search_inbound and (not outbound_journeys or not inbound_journeys):
            missing = "ida" if not outbound_journeys else "vuelta"
            self.push_warning(
                "NAVITIA_PARTIAL_COVERAGE",
                f"Cobertura parcial Navitia: hay viajes para un tramo pero no para el de {missing}.",
            )

        # Build options
        best_outbound = outbound_journeys[0] if outbound_journeys else None
        best_inbound = inbound_journeys[0] if inbound_journeys else None

        airport_buffer = max(query.preferences.min_airport_buffer_minutes, 90)
        flight_duration = int((flight.arrival_at - flight.departure_at).total_seconds() / 60)

        options: list[DoorToDoorOptionOut] = []
        options.append(self._build_option(
            query=query,
            outbound=best_outbound,
            inbound=best_inbound,
            airport_buffer=airport_buffer,
            flight_duration=flight_duration,
            option_idx=0,
            is_primary=True,
            checked_at=checked_at,
        ))

        # Additional alternatives
        for i, alt in enumerate(outbound_journeys[1:3]):
            options.append(self._build_option(
                query=query,
                outbound=alt,
                inbound=best_inbound,
                airport_buffer=airport_buffer,
                flight_duration=flight_duration,
                option_idx=i + 1,
                is_primary=False,
                checked_at=checked_at,
            ))

        return options

    async def healthcheck(self) -> ProviderHealth:
        if not self.enabled:
            return ProviderHealth(
                provider=self.provider_name,
                status="disabled",
                source_type=self.source_type,
                confidence="unavailable",
                message="Navitia desactivado por flag DOOR_TO_DOOR_ENABLE_NAVITIA.",
            )
        if not self.api_key:
            return ProviderHealth(
                provider=self.provider_name,
                status="missing_api_key",
                source_type=self.source_type,
                confidence="unavailable",
                message="NAVITIA_API_KEY no configurada.",
            )

        # Quick coverage check
        try:
            await self._load_coverages()
            if self._coverages:
                count = len(self._coverages)
                regions = ", ".join(c.id for c in self._coverages[:5])
                return ProviderHealth(
                    provider=self.provider_name,
                    status="ok",
                    source_type=self.source_type,
                    confidence="live",
                    message=f"Navitia activo con {count} coberturas disponibles: {regions}...",
                )
            return ProviderHealth(
                provider=self.provider_name,
                status="no_coverages",
                source_type=self.source_type,
                confidence="unavailable",
                message="Navitia configurado pero sin coberturas accesibles.",
            )
        except Exception as exc:
            return ProviderHealth(
                provider=self.provider_name,
                status="api_error",
                source_type=self.source_type,
                confidence="unavailable",
                message=f"Error al consultar Navitia: {exc}",
            )

    # ------------------------------------------------------------------
    # Option builder
    # ------------------------------------------------------------------

    def _build_option(
        self,
        *,
        query: DoorToDoorProviderQuery,
        outbound: _JourneyResult | None,
        inbound: _JourneyResult | None,
        airport_buffer: int,
        flight_duration: int,
        option_idx: int,
        is_primary: bool,
        checked_at: datetime,
    ) -> DoorToDoorOptionOut:
        flight = query.flight
        confidence: DoorToDoorConfidence = "cached" if option_idx > 0 else "live"

        sources: list[DoorToDoorSourceOut] = [
            DoorToDoorSourceOut(
                provider=self.provider_name,
                source_provider=self.provider_name,
                source_type="api",
                confidence=confidence,
                checked_at=checked_at,
                expires_at=checked_at + timedelta(hours=6),
            )
        ]

        legs: list[DoorToDoorLegOut] = []

        # Outbound ground leg (from journey sections)
        if outbound:
            for section in outbound.sections:
                legs.append(DoorToDoorLegOut(
                    type="ground",
                    mode=_navitia_mode_to_d2d(section.mode),
                    from_location=section.from_name,
                    to_location=section.to_name,
                    departure_at=section.departure_dt,
                    arrival_at=section.arrival_dt,
                    duration_minutes=max(1, int(round(section.duration_seconds / 60))),
                    price_min=None,
                    price_max=None,
                    provider=self.provider_name,
                    booking_url=None,
                    source_type="api",
                    confidence=confidence,
                ))

        # Flight leg
        legs.append(DoorToDoorLegOut(
            type="flight",
            mode="flight",
            from_location=flight.origin_airport,
            to_location=flight.destination_airport,
            departure_at=flight.departure_at,
            arrival_at=flight.arrival_at,
            duration_minutes=flight_duration,
            provider="flight_watch",
            source_type="api",
            confidence=flight.flight_time_confidence,
        ))

        # Inbound ground leg
        if inbound:
            for section in inbound.sections:
                legs.append(DoorToDoorLegOut(
                    type="ground",
                    mode=_navitia_mode_to_d2d(section.mode),
                    from_location=section.from_name,
                    to_location=section.to_name,
                    departure_at=section.departure_dt,
                    arrival_at=section.arrival_dt,
                    duration_minutes=max(1, int(round(section.duration_seconds / 60))),
                    price_min=None,
                    price_max=None,
                    provider=self.provider_name,
                    booking_url=None,
                    source_type="api",
                    confidence=confidence,
                ))

        transfer_count = sum(1 for leg in legs if leg.type == "ground")
        ground_duration = sum(leg.duration_minutes or 0 for leg in legs if leg.type == "ground")
        total_duration = ground_duration + airport_buffer + flight_duration

        # Build label from the primary transit route
        transit_sections = [
            s for j in [outbound, inbound] if j
            for s in j.sections
            if s.mode not in ("walking", "street_network")
        ]
        route_label = transit_sections[0].route_name if transit_sections else ""
        network_label = transit_sections[0].network if transit_sections else ""

        if route_label and network_label:
            label = f"{network_label} {route_label}"
        elif route_label:
            label = f"Transporte publico {route_label}"
        else:
            label = "Ruta en transporte publico (Navitia)"

        description = "Horario real de transporte publico via Navitia. Sin precio confirmado."

        score = score_itinerary(
            price_midpoint=None,
            duration_minutes=total_duration,
            airport_buffer_minutes=airport_buffer,
            transfer_count=transfer_count,
            confidence=confidence,
            completeness="full" if outbound and inbound else "partial_actionable",
            uncomfortable_hour=outbound.sections[0].departure_dt.hour < 6 if outbound and outbound.sections else False,
        )

        return DoorToDoorOptionOut(
            id=f"option_navitia_{option_idx}",
            label=label,
            description=description,
            status="real_result",
            total_price_min=None,
            total_price_max=None,
            price_per_person_min=None,
            price_per_person_max=None,
            currency="EUR",
            total_duration_minutes=total_duration,
            score=score,
            transfer_count=transfer_count,
            airport_buffer_minutes=airport_buffer,
            confidence=confidence,
            source_types=["api"],
            sources=sources,
            legs=legs,
            is_extended=not is_primary,
            deep_link=None,
            price=DoorToDoorPriceOut(amount=None, currency=None, status="unavailable"),
            trust_copy="Horarios de transporte publico via Navitia. Sin precio confirmado. Consulta tarifas con el operador.",
        )

    # ------------------------------------------------------------------
    # Coverages
    # ------------------------------------------------------------------

    async def _load_coverages(self) -> None:
        """Fetch available coverages from Navitia, cached in memory."""
        if self._coverages is not None:
            return
        if not self.api_key:
            self._coverages = []
            return

        try:
            resp = await asyncio.to_thread(
                lambda: httpx.get(
                    f"{NAVITIA_BASE_URL}/coverage",
                    auth=(self.api_key, ""),
                    timeout=self.timeout_seconds,
                )
            )
            if resp.status_code >= 400:
                logger.warning(
                    "navitia_coverage_fetch_failed",
                    extra={"status_code": resp.status_code, "body": resp.text[:300]},
                )
                self._coverages = []
                return

            data = resp.json()
            regions = data.get("regions") or []
            parsed: list[_CoverageInfo] = []
            for region in regions:
                parsed.append(_CoverageInfo(
                    id=region.get("id", ""),
                    name=region.get("name", ""),
                    shape=region.get("shape"),  # WKT string
                    admin_level=region.get("admin_level"),
                    parent_id=region.get("parent_region_id"),
                ))
            self._coverages = parsed
            logger.info(
                "navitia_coverages_loaded",
                extra={"count": len(parsed), "regions": [c.id for c in parsed[:10]]},
            )
        except Exception as exc:
            logger.warning("navitia_coverage_error", extra={"error": str(exc)})
            self._coverages = []

    async def _find_coverage_for_point(self, coords: tuple[float, float]) -> str | None:
        """Find the best coverage containing the given lat/lng point.

        Uses point-in-polygon testing on coverage shapes. Results are cached.
        Prefers lower admin_level (more specific) coverages.
        """
        lat, lng = coords
        cache_key = (round(lat, 3), round(lng, 3))
        if cache_key in self._coverage_cache:
            return self._coverage_cache[cache_key]

        await self._load_coverages()
        if not self._coverages:
            self._coverage_cache[cache_key] = None
            return None

        # Find coverages whose polygon contains the point
        matching: list[_CoverageInfo] = []
        for cov in self._coverages:
            if cov.shape and _point_in_wkt_polygon(lat, lng, cov.shape):
                matching.append(cov)

        if not matching:
            self._coverage_cache[cache_key] = None
            return None

        # Sort by admin_level (lower = more specific), then by name
        matching.sort(key=lambda c: (c.admin_level or 99, c.name))
        best = matching[0]
        self._coverage_cache[cache_key] = best.id
        return best.id

    # ------------------------------------------------------------------
    # Journey API
    # ------------------------------------------------------------------

    async def _search_journeys(
        self,
        *,
        coverage_id: str,
        from_coords: tuple[float, float],
        to_coords: tuple[float, float],
        datetime_ref: datetime,
        datetime_is_departure: bool,
    ) -> list[_JourneyResult]:
        """Search journeys between two points in a coverage region.

        Navitia uses longitude;latitude coordinate format.
        Datetime format: YYYYMMDDTHHMM (ISO 8601 basic).
        """
        from_str = f"{from_coords[1]};{from_coords[0]}"
        to_str = f"{to_coords[1]};{to_coords[0]}"
        dt_str = datetime_ref.strftime("%Y%m%dT%H%M")
        dt_repr = "departure" if datetime_is_departure else "arrival"

        url = (
            f"{NAVITIA_BASE_URL}/coverage/{coverage_id}/journeys"
            f"?from={from_str}&to={to_str}"
            f"&datetime={dt_str}"
            f"&datetime_represents={dt_repr}"
            f"&count=3"
        )

        try:
            resp = await asyncio.to_thread(
                lambda: httpx.get(
                    url,
                    auth=(self.api_key, ""),
                    timeout=self.timeout_seconds,
                )
            )
            if resp.status_code >= 400:
                logger.warning(
                    "navitia_journeys_failed",
                    extra={
                        "coverage_id": coverage_id,
                        "status_code": resp.status_code,
                        "body": resp.text[:300],
                    },
                )
                self.push_warning(
                    "NAVITIA_API_ERROR",
                    f"Navitia respondio con error {resp.status_code} para la cobertura {coverage_id}.",
                )
                return []

            data = resp.json()
            raw_journeys = data.get("journeys") or []
            parsed: list[_JourneyResult] = []
            for j in raw_journeys:
                journey = _parse_journey(j)
                if journey is not None:
                    parsed.append(journey)
            return parsed

        except Exception as exc:
            logger.warning(
                "navitia_journeys_error",
                extra={"coverage_id": coverage_id, "error": str(exc)},
            )
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _flag(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_journey(raw: dict) -> _JourneyResult | None:
    """Parse a Navitia journey response into a _JourneyResult."""
    try:
        duration = raw.get("duration", 0)
        dep_str = raw.get("departure_date_time", "")
        arr_str = raw.get("arrival_date_time", "")
        transfers = raw.get("nb_transfers", 0)
        sections_raw = raw.get("sections") or []

        dep_dt = _parse_navitia_datetime(dep_str)
        arr_dt = _parse_navitia_datetime(arr_str)
        if dep_dt is None or arr_dt is None:
            return None

        sections: list[_JourneySection] = []
        for sec in sections_raw:
            parsed_sec = _parse_section(sec)
            if parsed_sec:
                sections.append(parsed_sec)

        if not sections:
            return None

        return _JourneyResult(
            duration_seconds=duration,
            departure_dt=dep_dt,
            arrival_dt=arr_dt,
            transfers=transfers,
            sections=sections,
        )
    except Exception:
        return None


def _parse_section(raw: dict) -> _JourneySection | None:
    """Parse a single section from a Navitia journey."""
    try:
        mode = raw.get("mode", "walking")
        display = raw.get("display_informations") or {}
        from_info = raw.get("from") or {}
        to_info = raw.get("to") or {}

        dep_str = raw.get("departure_date_time", "")
        arr_str = raw.get("arrival_date_time", "")

        dep_dt = _parse_navitia_datetime(dep_str)
        arr_dt = _parse_navitia_datetime(arr_str)

        if dep_dt is None or arr_dt is None:
            return None

        return _JourneySection(
            mode=mode,
            from_name=from_info.get("name", ""),
            to_name=to_info.get("name", ""),
            departure_dt=dep_dt,
            arrival_dt=arr_dt,
            duration_seconds=raw.get("duration", 0),
            route_name=display.get("headsign") or display.get("name"),
            network=display.get("network"),
        )
    except Exception:
        return None


def _parse_navitia_datetime(raw: str) -> datetime | None:
    """Parse Navitia datetime format: YYYYMMDDTHHMMSS into timezone-naive datetime.

    Navitia returns local times without timezone info. We store them as-is.
    """
    if not raw:
        return None
    try:
        # Format: 20260715T143000
        if "T" in raw:
            dt_part, tm_part = raw.split("T")
            year = int(dt_part[:4])
            month = int(dt_part[4:6])
            day = int(dt_part[6:8])
            hour = int(tm_part[:2])
            minute = int(tm_part[2:4])
            second = int(tm_part[4:6]) if len(tm_part) >= 6 else 0
            return datetime(year, month, day, hour, minute, second)
        return None
    except (ValueError, IndexError):
        return None


def _navitia_mode_to_d2d(mode: str) -> DoorToDoorMode:
    """Map Navitia transport modes to DoorToDoorMode."""
    mapping: dict[str, DoorToDoorMode] = {
        "walking": "walking",
        "street_network": "walking",
        "bike": "walking",  # bike not a separate mode in D2D yet
        "car": "car",
        "bus": "bus",
        "train": "train",
        "metro": "bus",  # metro maps to bus in D2D
        "tram": "bus",
        "tramway": "bus",
        "ferry": "bus",
        "funicular": "bus",
        "coach": "bus",
        "shuttle": "shuttle",
        "taxi": "taxi",
    }
    return mapping.get(mode, "bus")


# ---------------------------------------------------------------------------
# Point-in-polygon for WKT shapes
# ---------------------------------------------------------------------------

def _point_in_wkt_polygon(lat: float, lng: float, wkt: str) -> bool:
    """Test whether a point falls inside a WKT polygon.

    Navitia returns shapes as WKT strings like:
    "POLYGON((2.37 48.84, 2.35 48.85, ...))"
    Coordinates in WKT are (longitude latitude), matching GeoJSON convention.

    Uses the ray-casting algorithm.
    """
    coords = _parse_wkt_polygon(wkt)
    if not coords or len(coords) < 3:
        return False

    # coords are (lng, lat) from WKT
    n = len(coords)
    inside = False
    j = n - 1
    for i in range(n):
        lng_i, lat_i = coords[i]
        lng_j, lat_j = coords[j]

        if ((lat_i > lat) != (lat_j > lat)) and (
            lng < (lng_j - lng_i) * (lat - lat_i) / (lat_j - lat_i) + lng_i
        ):
            inside = not inside
        j = i

    return inside


def _parse_wkt_polygon(wkt: str) -> list[tuple[float, float]] | None:
    """Parse a WKT POLYGON string into a list of (lng, lat) coordinate tuples."""
    if not wkt or not isinstance(wkt, str):
        return None

    wkt_upper = wkt.strip().upper()
    if not wkt_upper.startswith("POLYGON"):
        if wkt_upper.startswith("MULTIPOLYGON"):
            # Take the first polygon from a multipolygon
            start = wkt_upper.find("((")
            if start < 0:
                return None
            end = wkt.find("))")
            if end < 0:
                return None
            return _parse_polygon_ring(wkt[start + 1 : end + 1])
        return None

    return _parse_polygon_ring(wkt)


def _parse_polygon_ring(wkt: str) -> list[tuple[float, float]] | None:
    """Parse a single polygon ring from WKT text."""
    # Extract the outer ring coordinates between (( and ))
    start = wkt.find("((")
    if start < 0:
        return None
    end = wkt.rfind("))")
    if end < 0:
        return None
    ring = wkt[start + 2 : end]

    coords: list[tuple[float, float]] = []
    for point in ring.split(","):
        parts = point.strip().split()
        if len(parts) >= 2:
            try:
                lng = float(parts[0])
                lat = float(parts[1])
                coords.append((lng, lat))
            except ValueError:
                continue

    return coords if len(coords) >= 3 else None
