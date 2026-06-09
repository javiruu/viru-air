"""GTFS transit provider: search public transport trips from open-data GTFS feeds.

Returns legs with real transit schedules (when feeds are available), without
inventing price or purchase availability.

Granular warnings:
- GTFS_FEED_UNAVAILABLE: feed download/parse failed
- GTFS_NO_NEARBY_STOPS: feed loaded but no stops near origin/destination
- GTFS_NO_SERVICE_FOR_DATE: feed has stops but no service on target date
- GTFS_NO_MATCHING_SERVICE: service exists but no trips match the time window
- GTFS_PARTIAL_COVERAGE: feed covers only some legs
- GTFS_PRICE_UNAVAILABLE: schedules found but no fare data
- GTFS_CORRIDOR_VERIFIED: search matches a verified corridor (informational)
- GTFS_CORRIDOR_PLANNED: search falls in a planned/blocked corridor

Defenses:
- respect max_walk_radius from feed service
- enforce max_ground_duration per leg
- filter outbound trips arriving after flight departure minus buffer
- skip inbound when final_destination.type == "airport_only"
"""

from datetime import datetime, timedelta
import json
from pathlib import Path

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorLegOut,
    DoorToDoorMode,
    DoorToDoorOptionOut,
    DoorToDoorPriceOut,
    DoorToDoorSourceOut,
)
from app.door_to_door.services.gtfs_feed_service import (
    GtfsFeedService,
    GtfsTransitLeg,
    load_feed_descriptors,
)

# Max reasonable duration for a ground transit leg (minutes)
_MAX_GROUND_DURATION_MINUTES = 240  # 4 hours
# Absolute max walk radius cap (meters) — overrides any feed service setting
_MAX_WALK_RADIUS_HARD_CAP = 5000  # 5 km


class GtfsTransitProvider(DoorToDoorProvider):
    provider_name = "gtfs_transit"
    source_type = "open_data"

    def __init__(
        self,
        feed_service: GtfsFeedService | None = None,
        max_ground_duration_minutes: int = _MAX_GROUND_DURATION_MINUTES,
    ) -> None:
        super().__init__()
        self._feed_service = feed_service or GtfsFeedService()
        self._descriptors = load_feed_descriptors()
        self._corridors = _load_corridors()
        self._max_ground_duration = max_ground_duration_minutes

    async def healthcheck(self) -> ProviderHealth:
        if not self._descriptors:
            return ProviderHealth(
                self.provider_name,
                "disabled_no_feeds",
                self.source_type,
                "unavailable",
                "No feeds declared. Set DOOR_TO_DOOR_GTFS_FEEDS_JSON with a valid manifest.",
            )

        # Per-feed status
        feed_details: list[str] = []
        loaded = 0
        failed = 0
        for descriptor in self._descriptors:
            cached = self._feed_service._feeds.get(descriptor.id)
            if cached:
                loaded += 1
                feed_details.append(
                    f"✅ {descriptor.id} ({descriptor.region}): cargado, {len(cached.routes)} rutas, "
                    f"{len(cached.stops)} paradas"
                )
            else:
                failed += 1
                feed_details.append(
                    f"❌ {descriptor.id} ({descriptor.region}): no cargado — verifica URL y conectividad"
                )

        detail = f"Feeds: {loaded}/{len(self._descriptors)} cargados. " + "; ".join(feed_details[:5])

        if loaded == 0:
            return ProviderHealth(
                self.provider_name,
                "no_cached_data",
                self.source_type,
                "unavailable",
                detail,
            )
        if failed > 0:
            return ProviderHealth(
                self.provider_name,
                "degraded",
                self.source_type,
                "cached",
                detail,
            )
        return ProviderHealth(
            self.provider_name,
            "ok",
            self.source_type,
            "cached",
            detail,
        )

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        if not self._descriptors:
            return []

        flight = query.flight
        prefs = query.preferences
        checked_at = query.checked_at

        # Determine which legs to search
        search_outbound = True  # origin -> departure airport
        search_inbound = query.final_destination.type != "airport_only"  # arrival airport -> destination

        outbound_trips: list[GtfsTransitLeg] = []
        inbound_trips: list[GtfsTransitLeg] = []
        feed_warnings: list[str] = []
        any_loaded = False
        outbound_no_nearby_stops = False
        inbound_no_nearby_stops = False
        outbound_no_service_for_date = False
        inbound_no_service_for_date = False

        airport_buffer = max(prefs.min_airport_buffer_minutes, 120)

        for descriptor in self._descriptors:
            feed = self._feed_service.load_feed(descriptor)
            if feed is None:
                feed_warnings.append(
                f"Feed {descriptor.id} ({descriptor.name}) no disponible. "
                f"Verifica que la URL es accesible: {descriptor.url}"
            )
                continue
            any_loaded = True

            # Outbound: origin -> airport
            if search_outbound:
                origin_lat = query.origin.lat
                origin_lng = query.origin.lng
                if origin_lat is not None and origin_lng is not None:
                    nearby_stops = self._feed_service.find_nearby_stops(
                        feed.feed_id, origin_lat, origin_lng
                    )
                    if not nearby_stops:
                        outbound_no_nearby_stops = True

                    # Find airport-area stops
                    airport_city = _city_for_airport(flight.origin_airport)
                    airport_search = airport_city or flight.origin_airport
                    airport_stops = _find_stops_by_name(feed, airport_search)

                    # Match trips from ALL origin stops to ALL airport stops
                    origin_ids = {s.stop_id for s in nearby_stops}
                    airport_ids = {s.stop_id for s in airport_stops}
                    trips_found_for_date = False
                    if origin_ids and airport_ids:
                        latest_arrival = flight.departure_at - timedelta(minutes=airport_buffer)
                        target_date = flight.departure_at.date()
                        trips = self._feed_service.find_trips_between_any(
                            feed.feed_id,
                            from_stop_ids=origin_ids,
                            to_stop_ids=airport_ids,
                            target_date=target_date,
                            latest_arrival=latest_arrival,
                        )
                        if trips:
                            trips_found_for_date = True
                        outbound_trips.extend(trips)

                    if nearby_stops and airport_stops and not trips_found_for_date:
                        outbound_no_service_for_date = True

            # Inbound: arrival airport -> final destination
            if search_inbound:
                dest_lat = query.final_destination.lat
                dest_lng = query.final_destination.lng
                if dest_lat is not None and dest_lng is not None:
                    nearby_stops = self._feed_service.find_nearby_stops(
                        feed.feed_id, dest_lat, dest_lng
                    )
                    if not nearby_stops:
                        inbound_no_nearby_stops = True

                    airport_city = _city_for_airport(flight.destination_airport)
                    airport_search = airport_city or flight.destination_airport
                    airport_stops = _find_stops_by_name(feed, airport_search)

                    airport_ids = {s.stop_id for s in airport_stops}
                    dest_ids = {s.stop_id for s in nearby_stops}
                    trips_found_for_date = False
                    if airport_ids and dest_ids:
                        earliest_departure = flight.arrival_at + timedelta(minutes=30)
                        target_date = flight.arrival_at.date()
                        trips = self._feed_service.find_trips_between_any(
                            feed.feed_id,
                            from_stop_ids=airport_ids,
                            to_stop_ids=dest_ids,
                            target_date=target_date,
                            earliest_departure=earliest_departure,
                        )
                        if trips:
                            trips_found_for_date = True
                        inbound_trips.extend(trips)

                    if nearby_stops and airport_stops and not trips_found_for_date:
                        inbound_no_service_for_date = True

        # --- Granular warnings ---

        # 1. Feed unavailable
        if feed_warnings:
            self.push_warning(
                "GTFS_FEED_UNAVAILABLE",
                "; ".join(feed_warnings[:3]),
                provider=self.provider_name,
            )

        if not any_loaded:
            self.push_warning(
                "GTFS_FEED_UNAVAILABLE",
                "Ningún feed GTFS pudo descargarse o parsearse. "
                "Verifica conectividad, URLs en el manifest y el caché en "
                f"{self._feed_service.cache_dir}.",
                provider=self.provider_name,
            )
            return []

        # 2. No nearby stops
        if search_outbound and outbound_no_nearby_stops:
            self.push_warning(
                "GTFS_NO_NEARBY_STOPS",
                f"No se encontraron paradas públicas cercanas al origen «{query.origin.label}» "
                f"(radio: {self._feed_service.max_walk_radius}m).",
                provider=self.provider_name,
            )
        if search_inbound and inbound_no_nearby_stops:
            self.push_warning(
                "GTFS_NO_NEARBY_STOPS",
                f"No se encontraron paradas públicas cercanas al destino «{query.final_destination.label}» "
                f"(radio: {self._feed_service.max_walk_radius}m).",
                provider=self.provider_name,
            )

        # 3. No service for date
        if search_outbound and outbound_no_service_for_date:
            self.push_warning(
                "GTFS_NO_SERVICE_FOR_DATE",
                f"Hay paradas cercanas, pero no se encontró servicio de transporte público "
                f"para la fecha del vuelo ({flight.departure_at.date()}) en el tramo de ida.",
                provider=self.provider_name,
            )
        if search_inbound and inbound_no_service_for_date:
            self.push_warning(
                "GTFS_NO_SERVICE_FOR_DATE",
                f"Hay paradas cercanas, pero no se encontró servicio de transporte público "
                f"para la fecha del vuelo ({flight.arrival_at.date()}) en el tramo de vuelta.",
                provider=self.provider_name,
            )

        # Filter out absurd results: trips longer than max_ground_duration
        outbound_trips = [
            t for t in outbound_trips
            if t.duration_minutes <= self._max_ground_duration
        ]
        inbound_trips = [
            t for t in inbound_trips
            if t.duration_minutes <= self._max_ground_duration
        ]

        # Deduplicate trips
        outbound_trips = _deduplicate_trips(outbound_trips)
        inbound_trips = _deduplicate_trips(inbound_trips)

        # 4. No matching service (loaded but no trips matched)
        if not outbound_trips and not inbound_trips:
            self.push_warning(
                "GTFS_NO_MATCHING_SERVICE",
                "No se encontraron viajes de transporte público que coincidan con la ruta, horario y "
                "restricciones (buffer de aeropuerto, duración máxima, ventana horaria).",
                provider=self.provider_name,
            )
            # Still emit corridor signals — geographic coverage is independent of trip matching
            _emit_corridor_signals(self, flight)
            return []

        # 5. Partial coverage
        if search_outbound and search_inbound and (not outbound_trips or not inbound_trips):
            missing = "ida" if not outbound_trips else "vuelta"
            self.push_warning(
                "GTFS_PARTIAL_COVERAGE",
                f"Cobertura parcial: hay viajes disponibles para un tramo pero no para el tramo de {missing}.",
                provider=self.provider_name,
            )

        # 6. Corridor signals — inform whether this route falls in a known corridor
        _emit_corridor_signals(self, flight)

        # Flight time estimated warning
        if flight.flight_time_confidence == "estimated":
            self.push_warning(
                "FLIGHT_TIME_ESTIMATED",
                "La hora de llegada del vuelo es estimada. Verifica compatibilidad con el transporte público.",
            )

        # Price warnings
        self.push_warning(
            "UNCONFIRMED_PRICE",
            "El precio del transporte público no está disponible. Consulta tarifas en la web del operador.",
            provider=self.provider_name,
        )

        if any(leg.mode == "bus" for leg in outbound_trips + inbound_trips):
            self.push_warning(
                "GTFS_PRICE_UNAVAILABLE",
                "Tarifas no incluidas; consulta precios con el operador de transporte público.",
                provider=self.provider_name,
            )

        # Build options
        options: list[DoorToDoorOptionOut] = []
        flight_duration = int((flight.arrival_at - flight.departure_at).total_seconds() / 60)

        # Pick best outbound and inbound
        best_outbound = outbound_trips[0] if outbound_trips else None
        best_inbound = inbound_trips[0] if inbound_trips else None

        if best_outbound:
            options.append(self._build_option(
                query=query,
                outbound=best_outbound,
                inbound=best_inbound,
                airport_buffer=airport_buffer,
                flight_duration=flight_duration,
                option_idx=0,
                is_primary=True,
            ))

        # Add alternatives if available
        for i, alt in enumerate(outbound_trips[1:3]):
            options.append(self._build_option(
                query=query,
                outbound=alt,
                inbound=best_inbound,
                airport_buffer=airport_buffer,
                flight_duration=flight_duration,
                option_idx=i + 1,
                is_primary=False,
            ))

        for i, alt in enumerate(inbound_trips[1:3]):
            options.append(self._build_option(
                query=query,
                outbound=best_outbound,
                inbound=alt,
                airport_buffer=airport_buffer,
                flight_duration=flight_duration,
                option_idx=len(outbound_trips) + i,
                is_primary=False,
            ))

        return options

    def _build_option(
        self,
        *,
        query: DoorToDoorProviderQuery,
        outbound: GtfsTransitLeg | None,
        inbound: GtfsTransitLeg | None,
        airport_buffer: int,
        flight_duration: int,
        option_idx: int,
        is_primary: bool,
    ) -> DoorToDoorOptionOut:
        flight = query.flight
        checked_at = query.checked_at

        confidence = "cached" if option_idx > 0 else "live"
        sources: list[DoorToDoorSourceOut] = []

        if outbound:
            sources.append(DoorToDoorSourceOut(
                provider=self.provider_name,
                source_provider=f"gtfs_{outbound.feed_id}",
                source_type="open_data",
                confidence=confidence,
                checked_at=checked_at,
                expires_at=checked_at + timedelta(hours=24),
            ))
        if inbound:
            sources.append(DoorToDoorSourceOut(
                provider=self.provider_name,
                source_provider=f"gtfs_{inbound.feed_id}",
                source_type="open_data",
                confidence=confidence,
                checked_at=checked_at,
                expires_at=checked_at + timedelta(hours=24),
            ))

        legs: list[DoorToDoorLegOut] = []

        # Outbound leg
        if outbound:
            mode = _gtfs_mode_to_d2d(outbound.mode)
            legs.append(DoorToDoorLegOut(
                type="ground",
                mode=mode,
                from_location=outbound.from_stop_name,
                to_location=outbound.to_stop_name,
                departure_at=outbound.departure_at,
                arrival_at=outbound.arrival_at,
                duration_minutes=outbound.duration_minutes,
                price_min=None,
                price_max=None,
                provider=self.provider_name,
                booking_url=None,
                source_type="open_data",
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

        # Inbound leg
        if inbound:
            mode = _gtfs_mode_to_d2d(inbound.mode)
            legs.append(DoorToDoorLegOut(
                type="ground",
                mode=mode,
                from_location=inbound.from_stop_name,
                to_location=inbound.to_stop_name,
                departure_at=inbound.departure_at,
                arrival_at=inbound.arrival_at,
                duration_minutes=inbound.duration_minutes,
                price_min=None,
                price_max=None,
                provider=self.provider_name,
                booking_url=None,
                source_type="open_data",
                confidence=confidence,
            ))

        transfer_count = sum(1 for leg in legs if leg.type == "ground")
        ground_duration = sum(leg.duration_minutes or 0 for leg in legs if leg.type == "ground")
        total_duration = ground_duration + airport_buffer + flight_duration

        agency_name = ""
        route_name = ""
        if outbound:
            agency_name = outbound.agency_name
            route_name = outbound.route_name
        elif inbound:
            agency_name = inbound.agency_name
            route_name = inbound.route_name

        label = f"Transporte público {route_name}" if route_name else "Ruta en transporte público"
        description = (
            f"{agency_name} · horario según feed público."
            if agency_name
            else "Horario según feed público GTFS. Precio y compra no confirmados."
        )

        score = score_itinerary(
            price_midpoint=None,
            duration_minutes=total_duration,
            airport_buffer_minutes=airport_buffer,
            transfer_count=transfer_count,
            confidence=confidence,
            uncomfortable_hour=outbound.departure_at.hour < 6 if outbound else False,
            luggage_penalty=0,
        )

        return DoorToDoorOptionOut(
            id=f"option_gtfs_{option_idx}",
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
            source_types=["open_data"],
            sources=sources,
            legs=legs,
            is_extended=not is_primary,
            deep_link=None,
            price=DoorToDoorPriceOut(amount=None, currency=None, status="unavailable"),
            trust_copy="Horarios de transporte público según feed oficial. Sin precio confirmado. Consulta tarifas con el operador.",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gtfs_mode_to_d2d(gtfs_mode: str) -> DoorToDoorMode:
    mapping: dict[str, DoorToDoorMode] = {
        "bus": "bus",
        "train": "train",
        "metro": "metro",
        "tram": "bus",
        "ferry": "bus",
        "transit": "bus",
    }
    return mapping.get(gtfs_mode, "bus")


def _city_for_airport(iata: str) -> str | None:
    """Reuse same mapping as deeplink providers for airport→city lookup."""
    mapping: dict[str, str] = {
        "AGP": "Málaga",
        "MAD": "Madrid",
        "BCN": "Barcelona",
        "ALC": "Alicante",
        "VLC": "Valencia",
        "SVQ": "Sevilla",
        "BIO": "Bilbao",
        "PMI": "Palma de Mallorca",
        "GRO": "Girona",
        "REU": "Reus",
        "ZAZ": "Zaragoza",
        "GRX": "Granada",
        "LEI": "Almería",
        "TSF": "Treviso",
        "VCE": "Venecia",
        "FCO": "Roma",
        "MXP": "Milán",
        "BGY": "Bérgamo",
        "ORY": "París",
        "CDG": "París",
        "LGW": "Londres",
        "STN": "Londres",
        "LTN": "Londres",
        "AMS": "Ámsterdam",
        "BRU": "Bruselas",
        "CRL": "Charleroi",
    }
    return mapping.get(iata.upper())


def _find_stops_by_name(feed: "ParsedGtfsFeed", query: str) -> list:  # noqa: F821
    """Find stops whose name contains the query string (case-insensitive, accent-insensitive)."""
    import unicodedata

    from app.door_to_door.services.gtfs_feed_service import ParsedGtfsFeed

    def _normalize(s: str) -> str:
        return unicodedata.normalize("NFKD", s.lower()).encode("ascii", errors="ignore").decode()

    q = _normalize(query)
    results = [stop for stop in feed.stops.values() if q in _normalize(stop.name)]
    # Sort by name length (shorter = more likely airport/main station)
    results.sort(key=lambda s: len(s.name))
    return results[:10]


def _deduplicate_trips(trips: list[GtfsTransitLeg]) -> list[GtfsTransitLeg]:
    """Deduplicate trips by from_stop_id + to_stop_id + route_name, keeping earliest."""
    seen: set[tuple[str, str, str]] = set()
    result: list[GtfsTransitLeg] = []
    for leg in sorted(trips, key=lambda t: t.departure_at):
        key = (leg.from_stop_id, leg.to_stop_id, leg.route_name)
        if key not in seen:
            seen.add(key)
            result.append(leg)
    return result


# ── Corridor definitions ───────────────────────────────────────────

_CORRIDORS_CACHE: list[dict] | None = None


def _load_corridors() -> list[dict]:
    """Load corridor definitions from the default manifest file. Cached in memory."""
    global _CORRIDORS_CACHE
    if _CORRIDORS_CACHE is not None:
        return _CORRIDORS_CACHE
    default_path = Path(__file__).resolve().parent / "gtfs_corridors.json"
    try:
        if default_path.exists():
            raw = default_path.read_text(encoding="utf-8")
            items = json.loads(raw)
            if isinstance(items, list):
                _CORRIDORS_CACHE = items
                return items
    except (OSError, json.JSONDecodeError):
        pass
    _CORRIDORS_CACHE = []
    return []


def _match_corridors(
    corridors: list[dict],
    origin_airport: str,
    destination_airport: str,
) -> list[dict]:
    """Find corridors that match either the origin or destination airport."""
    matched: list[dict] = []
    origin_upper = origin_airport.upper()
    dest_upper = destination_airport.upper()
    for corridor in corridors:
        airport = (corridor.get("destination_airport") or "").upper()
        if airport == origin_upper or airport == dest_upper:
            matched.append(corridor)
    return matched


def _emit_corridor_signals(provider: "GtfsTransitProvider", flight) -> None:
    """Emit GTFS_CORRIDOR_VERIFIED or GTFS_CORRIDOR_PLANNED based on matched corridors."""
    matched = _match_corridors(
        provider._corridors,
        flight.origin_airport,
        flight.destination_airport,
    )
    verified_corridors = [c for c in matched if c.get("status") == "verified" or c.get("status") == "verified_limited"]
    planned_corridors = [c for c in matched if c.get("status") == "planned_blocked"]

    if verified_corridors:
        names = ", ".join(c["name"] for c in verified_corridors[:2])
        provider.push_warning(
            "GTFS_CORRIDOR_VERIFIED",
            f"Esta ruta cae dentro de corredores con cobertura verificada: {names}. "
            "Es posible que haya horarios reales si la fecha y coordenadas coinciden.",
            provider=provider.provider_name,
        )
    elif planned_corridors:
        names = ", ".join(c["name"] for c in planned_corridors[:2])
        provider.push_warning(
            "GTFS_CORRIDOR_PLANNED",
            f"Esta ruta cae en un corredor planeado pero aún no activo: {names}. "
            "Los feeds necesarios requieren autenticación o configuración adicional.",
            provider=provider.provider_name,
        )
