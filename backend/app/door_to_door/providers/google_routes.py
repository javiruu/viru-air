from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import requests

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.domain.risk import calculate_risk_level
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorConfidence,
    DoorToDoorLegOut,
    DoorToDoorLocation,
    DoorToDoorOptionOut,
    DoorToDoorSourceOut,
)

GOOGLE_ROUTES_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
GOOGLE_PLACE_DETAILS_ENDPOINT = "https://places.googleapis.com/v1/places/{place_id}"
AIRPORT_COORDS: dict[str, tuple[float, float]] = {
    "AGP": (36.675, -4.499),
    "TSF": (45.651, 12.199),
}
LABEL_COORDS: dict[str, tuple[float, float]] = {
    "almeria": (36.834, -2.463),
    "almería": (36.834, -2.463),
    "treviso centro": (45.667, 12.243),
    "venecia": (45.441, 12.316),
    "padua": (45.406, 11.877),
}


@dataclass(frozen=True)
class _RouteResult:
    duration_minutes: int
    distance_meters: int
    mode: str
    confidence: DoorToDoorConfidence
    checked_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class _CachedRoute:
    result: _RouteResult


class GoogleRoutesProvider(DoorToDoorProvider):
    provider_name = "google_routes"
    source_type = "api"

    def __init__(self) -> None:
        super().__init__()
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
        self.enabled = self._flag("DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES", False)
        self.timeout_seconds = float(os.getenv("DOOR_TO_DOOR_GOOGLE_ROUTES_TIMEOUT_SECONDS", "6"))
        self.cache_ttl_seconds = int(os.getenv("DOOR_TO_DOOR_GOOGLE_ROUTES_CACHE_TTL_SECONDS", "900"))
        self._cache: dict[str, _CachedRoute] = {}
        self._resolved_places: dict[str, tuple[float, float]] = {}

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        if not self.enabled or not self.api_key:
            return []

        outbound_target = self._airport_coords(query.flight.origin_airport)
        if not outbound_target:
            self.push_warning(
                "PROVIDER_PARTIAL_COVERAGE",
                "No se han podido resolver coordenadas del aeropuerto de salida para rutas reales.",
            )
            return []

        outbound_origin = await self._resolve_location_coords(query.origin)
        if outbound_origin is None:
            self.push_warning(
                "PROVIDER_PARTIAL_COVERAGE",
                "No se han podido resolver coordenadas del origen para rutas reales.",
            )
            return []

        outbound = await self._route_leg(
            origin=outbound_origin,
            destination=outbound_target,
            mode_hint="transit" if query.preferences.public_transport_only else "driving",
            departure_at=query.flight.departure_at,
        )

        if outbound is None:
            raise RuntimeError("google_routes_outbound_unavailable")

        inbound: _RouteResult | None = None
        if query.final_destination.type != "airport_only":
            inbound_origin = self._airport_coords(query.flight.destination_airport)
            inbound_destination = await self._resolve_location_coords(query.final_destination)
            if inbound_origin and inbound_destination:
                inbound = await self._route_leg(
                    origin=inbound_origin,
                    destination=inbound_destination,
                    mode_hint="driving",
                    departure_at=query.flight.arrival_at,
                )
            else:
                self.push_warning(
                    "PROVIDER_PARTIAL_COVERAGE",
                    "No se ha podido calcular el tramo de llegada con rutas reales.",
                )

        airport_buffer = max(query.preferences.min_airport_buffer_minutes, 90)
        flight_duration = int((query.flight.arrival_at - query.flight.departure_at).total_seconds() / 60)
        outbound_arrival = query.flight.departure_at - timedelta(minutes=airport_buffer)
        outbound_departure = outbound_arrival - timedelta(minutes=outbound.duration_minutes)

        legs = [
            DoorToDoorLegOut(
                type="ground",
                mode=self._map_mode(outbound.mode),
                from_label=query.origin.label,
                to_label=f"Aeropuerto de Málaga {query.flight.origin_airport}",
                departure_at=outbound_departure,
                arrival_at=outbound_arrival,
                duration_minutes=outbound.duration_minutes,
                distance_meters=outbound.distance_meters,
                price_min=None,
                price_max=None,
                provider=self.provider_name,
                booking_url=None,
                source_type="api",
                confidence=outbound.confidence,
            ),
            DoorToDoorLegOut(
                type="flight",
                mode="flight",
                from_label=query.flight.origin_airport,
                to_label=query.flight.destination_airport,
                departure_at=query.flight.departure_at,
                arrival_at=query.flight.arrival_at,
                duration_minutes=flight_duration,
                provider="flight_watch",
                source_type="api",
                confidence=query.flight.flight_time_confidence,
            ),
        ]

        if query.final_destination.type != "airport_only":
            if inbound is not None:
                inbound_departure = query.flight.arrival_at + timedelta(minutes=25)
                inbound_arrival = inbound_departure + timedelta(minutes=inbound.duration_minutes)
                legs.append(
                    DoorToDoorLegOut(
                        type="ground",
                        mode=self._map_mode(inbound.mode),
                        from_label=f"Treviso Airport {query.flight.destination_airport}",
                        to_label=query.final_destination.label,
                        departure_at=inbound_departure,
                        arrival_at=inbound_arrival,
                        duration_minutes=inbound.duration_minutes,
                        distance_meters=inbound.distance_meters,
                        price_min=None,
                        price_max=None,
                        provider=self.provider_name,
                        booking_url=None,
                        source_type="api",
                        confidence=inbound.confidence,
                    )
                )
            else:
                self.push_warning(
                    "PROVIDER_PARTIAL_COVERAGE",
                    "No se ha podido calcular el tramo final con rutas reales.",
                )

        source_confidence = self._merge_confidence([
            outbound.confidence,
            inbound.confidence if inbound is not None else "live",
        ])
        checked_at = max([outbound.checked_at, inbound.checked_at if inbound is not None else outbound.checked_at])
        expires_at = min([outbound.expires_at, inbound.expires_at if inbound is not None else outbound.expires_at])

        source = DoorToDoorSourceOut(
            provider=self.provider_name,
            source_provider=self.provider_name,
            source_type="api",
            confidence=source_confidence,
            checked_at=checked_at,
            expires_at=expires_at,
            booking_url=None,
        )

        total_duration = outbound.duration_minutes + flight_duration + airport_buffer
        if inbound is not None:
            total_duration += inbound.duration_minutes
        transfer_count = 2 if inbound is not None else 1
        risk = calculate_risk_level(airport_buffer, transfer_count, source_confidence)
        score = score_itinerary(
            price_midpoint=None,
            duration_minutes=total_duration,
            airport_buffer_minutes=airport_buffer,
            transfer_count=transfer_count,
            risk_level=risk,
            confidence=source_confidence,
            uncomfortable_hour=outbound_departure.hour < 6,
            luggage_penalty=0,
        )

        self.push_warning(
            "UNCONFIRMED_PRICE",
            "Esta opción tiene duración/distancia reales, pero sin precio confirmado.",
        )

        return [
            DoorToDoorOptionOut(
                id="option_google_routes",
                label="Duración real de ruta terrestre",
                description="Duración y distancia calculadas con proveedor de rutas.",
                total_price_min=None,
                total_price_max=None,
                price_per_person_min=None,
                price_per_person_max=None,
                currency="EUR",
                total_duration_minutes=total_duration,
                risk_level=risk,
                score=score,
                transfer_count=transfer_count,
                airport_buffer_minutes=airport_buffer,
                confidence=source_confidence,
                source_types=["api"],
                sources=[source],
                legs=legs,
                is_extended=False,
            )
        ]

    async def healthcheck(self) -> ProviderHealth:
        if not self.enabled:
            return ProviderHealth(
                provider=self.provider_name,
                status="disabled",
                source_type=self.source_type,
                confidence="unavailable",
                message="Google Routes desactivado por flag.",
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
            message="Google Routes listo para calcular duración/distancia.",
        )

    @staticmethod
    def _flag(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def _airport_coords(self, iata: str) -> tuple[float, float] | None:
        return AIRPORT_COORDS.get(iata.strip().upper())

    async def _resolve_location_coords(self, location: DoorToDoorLocation) -> tuple[float, float] | None:
        if location.lat is not None and location.lng is not None:
            return (float(location.lat), float(location.lng))

        if location.place_id:
            cached = self._resolved_places.get(location.place_id)
            if cached:
                return cached
            resolved = await asyncio.to_thread(self._fetch_place_coords, location.place_id)
            if resolved:
                self._resolved_places[location.place_id] = resolved
                return resolved

        normalized = location.label.strip().lower()
        if normalized in LABEL_COORDS:
            return LABEL_COORDS[normalized]
        if location.type in {"airport", "airport_only"}:
            for iata, coords in AIRPORT_COORDS.items():
                if iata in location.label.upper():
                    return coords
        return None

    def _fetch_place_coords(self, place_id: str) -> tuple[float, float] | None:
        url = GOOGLE_PLACE_DETAILS_ENDPOINT.format(place_id=place_id)
        try:
            response = requests.get(
                url,
                headers={
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": "location",
                },
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                return None
            payload = response.json()
        except Exception:
            return None

        location = payload.get("location") or {}
        lat = location.get("latitude")
        lng = location.get("longitude")
        if lat is None or lng is None:
            return None
        return (float(lat), float(lng))

    async def _route_leg(
        self,
        *,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode_hint: str,
        departure_at: datetime,
    ) -> _RouteResult | None:
        candidate_modes = [mode_hint]
        if mode_hint == "transit":
            candidate_modes.append("driving")
        if mode_hint == "driving":
            candidate_modes.append("walking")

        for index, mode in enumerate(candidate_modes):
            cached = self._get_cached_route(origin, destination, mode, departure_at)
            if cached:
                return cached
            result = await asyncio.to_thread(
                self._fetch_route,
                origin,
                destination,
                mode,
                departure_at,
            )
            if result is not None:
                self._cache_route(origin, destination, mode, departure_at, result)
                if index > 0:
                    self.push_warning(
                        "PROVIDER_PARTIAL_COVERAGE",
                        "No se encontró ruta en el modo preferido. Se ha aplicado fallback para completar la opción.",
                    )
                return result
        return None

    def _cache_key(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str,
        departure_at: datetime,
    ) -> str:
        rounded_departure = departure_at.replace(second=0, microsecond=0).isoformat()
        return (
            f"{origin[0]:.5f}:{origin[1]:.5f}:{destination[0]:.5f}:{destination[1]:.5f}:"
            f"{mode}:{rounded_departure}"
        )

    def _get_cached_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str,
        departure_at: datetime,
    ) -> _RouteResult | None:
        key = self._cache_key(origin, destination, mode, departure_at)
        cached = self._cache.get(key)
        if not cached:
            return None
        if cached.result.expires_at <= datetime.now(tz=UTC):
            self._cache.pop(key, None)
            return None
        return _RouteResult(
            duration_minutes=cached.result.duration_minutes,
            distance_meters=cached.result.distance_meters,
            mode=cached.result.mode,
            confidence="cached",
            checked_at=cached.result.checked_at,
            expires_at=cached.result.expires_at,
        )

    def _cache_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str,
        departure_at: datetime,
        route: _RouteResult,
    ) -> None:
        key = self._cache_key(origin, destination, mode, departure_at)
        self._cache[key] = _CachedRoute(result=route)

    def _fetch_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str,
        departure_at: datetime,
    ) -> _RouteResult | None:
        body: dict[str, object] = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin[0],
                        "longitude": origin[1],
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination[0],
                        "longitude": destination[1],
                    }
                }
            },
            "travelMode": mode.upper(),
            "languageCode": "es-ES",
            "units": "METRIC",
        }
        if mode in {"driving", "walking"}:
            body["routingPreference"] = "TRAFFIC_AWARE"
        if mode in {"driving", "transit"}:
            body["departureTime"] = departure_at.astimezone(UTC).replace(microsecond=0).isoformat().replace(
                "+00:00", "Z"
            )

        try:
            response = requests.post(
                GOOGLE_ROUTES_ENDPOINT,
                json=body,
                headers={
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
                },
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                return None
            payload = response.json()
        except Exception:
            return None
        routes = payload.get("routes") or []
        if not routes:
            return None
        first = routes[0]
        duration_seconds = self._parse_duration_seconds(first.get("duration"))
        distance_meters = first.get("distanceMeters")
        if duration_seconds is None or distance_meters is None:
            return None

        checked_at = datetime.now(tz=UTC)
        expires_at = checked_at + timedelta(seconds=self.cache_ttl_seconds)
        return _RouteResult(
            duration_minutes=max(1, int(round(duration_seconds / 60))),
            distance_meters=int(distance_meters),
            mode=mode,
            confidence="live",
            checked_at=checked_at,
            expires_at=expires_at,
        )

    @staticmethod
    def _parse_duration_seconds(raw: object) -> int | None:
        if not isinstance(raw, str) or not raw.endswith("s"):
            return None
        value = raw[:-1]
        try:
            return int(float(value))
        except ValueError:
            return None

    @staticmethod
    def _map_mode(raw_mode: str) -> str:
        if raw_mode == "transit":
            return "bus"
        if raw_mode == "walking":
            return "walking"
        return "car"

    @staticmethod
    def _merge_confidence(confidences: list[DoorToDoorConfidence]) -> DoorToDoorConfidence:
        if all(value == "cached" for value in confidences):
            return "cached"
        if any(value == "live" for value in confidences):
            return "live"
        if any(value == "cached" for value in confidences):
            return "cached"
        return "estimated"
