"""GTFS transit provider: search public transport trips from open-data GTFS feeds.

Returns legs with real transit schedules (when feeds are available), without
inventing price or purchase availability.
"""

from datetime import datetime, timedelta

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.domain.risk import calculate_risk_level
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorLegOut,
    DoorToDoorMode,
    DoorToDoorOptionOut,
    DoorToDoorSourceOut,
)
from app.door_to_door.services.gtfs_feed_service import (
    GtfsFeedService,
    GtfsTransitLeg,
    load_feed_descriptors,
)


class GtfsTransitProvider(DoorToDoorProvider):
    provider_name = "gtfs_transit"
    source_type = "open_data"

    def __init__(self, feed_service: GtfsFeedService | None = None) -> None:
        super().__init__()
        self._feed_service = feed_service or GtfsFeedService()
        self._descriptors = load_feed_descriptors()

    async def healthcheck(self) -> ProviderHealth:
        if not self._descriptors:
            return ProviderHealth(
                self.provider_name,
                "disabled_no_feeds",
                self.source_type,
                "unavailable",
                "No feeds declared. Set DOOR_TO_DOOR_GTFS_FEEDS_JSON.",
            )
        loaded = sum(1 for d in self._descriptors if self._feed_service._feeds.get(d.id))
        return ProviderHealth(
            self.provider_name,
            "ok" if loaded > 0 else "no_cached_data",
            self.source_type,
            "cached" if loaded > 0 else "unavailable",
            f"Feeds declared: {len(self._descriptors)}; cached: {loaded}.",
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

        for descriptor in self._descriptors:
            feed = self._feed_service.load_feed(descriptor)
            if feed is None:
                feed_warnings.append(f"Feed {descriptor.id} ({descriptor.name}) no disponible.")
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
                    # Find airport-area stops
                    airport_city = _city_for_airport(flight.origin_airport)
                    airport_search = airport_city or flight.origin_airport
                    airport_stops = _find_stops_by_name(feed, airport_search)

                    # Match trips from origin stops to airport stops
                    for orig_stop in nearby_stops[: self._feed_service.max_results]:
                        for dest_stop in airport_stops[: self._feed_service.max_results]:
                            if orig_stop.stop_id == dest_stop.stop_id:
                                continue
                            airport_buffer = max(prefs.min_airport_buffer_minutes, 120)
                            latest_arrival = flight.departure_at - timedelta(minutes=airport_buffer)
                            target_date = flight.departure_at.date()
                            trips = self._feed_service.find_trips_between(
                                feed.feed_id,
                                orig_stop.stop_id,
                                dest_stop.stop_id,
                                target_date=target_date,
                                latest_arrival=latest_arrival,
                            )
                            outbound_trips.extend(trips)

            # Inbound: arrival airport -> final destination
            if search_inbound:
                dest_lat = query.final_destination.lat
                dest_lng = query.final_destination.lng
                if dest_lat is not None and dest_lng is not None:
                    nearby_stops = self._feed_service.find_nearby_stops(
                        feed.feed_id, dest_lat, dest_lng
                    )
                    airport_city = _city_for_airport(flight.destination_airport)
                    airport_search = airport_city or flight.destination_airport
                    airport_stops = _find_stops_by_name(feed, airport_search)

                    for orig_stop in airport_stops[: self._feed_service.max_results]:
                        for dest_stop in nearby_stops[: self._feed_service.max_results]:
                            if orig_stop.stop_id == dest_stop.stop_id:
                                continue
                            # Inbound: depart after flight arrival + buffer
                            earliest_departure = flight.arrival_at + timedelta(minutes=30)
                            target_date = flight.arrival_at.date()
                            trips = self._feed_service.find_trips_between(
                                feed.feed_id,
                                orig_stop.stop_id,
                                dest_stop.stop_id,
                                target_date=target_date,
                                earliest_departure=earliest_departure,
                            )
                            inbound_trips.extend(trips)

        # Emit feed warnings
        if feed_warnings:
            self.push_warning(
                "GTFS_FEED_UNAVAILABLE",
                "; ".join(feed_warnings[:3]),  # cap at 3 feed messages
                provider=self.provider_name,
            )

        if not any_loaded:
            self.push_warning(
                "GTFS_PARTIAL_COVERAGE",
                "Ningún feed GTFS disponible para esta consulta.",
                provider=self.provider_name,
            )

        # Deduplicate trips
        outbound_trips = _deduplicate_trips(outbound_trips)
        inbound_trips = _deduplicate_trips(inbound_trips)

        if not outbound_trips and not inbound_trips:
            if any_loaded:
                self.push_warning(
                    "GTFS_NO_MATCHING_SERVICE",
                    "No se encontraron viajes de transporte público que coincidan con la ruta y horario.",
                    provider=self.provider_name,
                )
            return []

        if any_loaded and (not outbound_trips or not inbound_trips):
            self.push_warning(
                "GTFS_PARTIAL_COVERAGE",
                "Cobertura parcial: algunos tramos no tienen viajes GTFS disponibles.",
                provider=self.provider_name,
            )

        # Emit flight_time_estimated if needed
        if flight.flight_time_confidence == "estimated":
            self.push_warning(
                "FLIGHT_TIME_ESTIMATED",
                "La hora de llegada del vuelo es estimada. Verifica compatibilidad con el transporte público.",
            )

        # Emit unconfirmed price
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
        airport_buffer = max(prefs.min_airport_buffer_minutes, 120)
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
                from_label=outbound.from_stop_name,
                to_label=outbound.to_stop_name,
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
            from_label=flight.origin_airport,
            to_label=flight.destination_airport,
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
                from_label=inbound.from_stop_name,
                to_label=inbound.to_stop_name,
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

        risk = calculate_risk_level(airport_buffer, transfer_count, confidence)
        score = score_itinerary(
            price_midpoint=None,
            duration_minutes=total_duration,
            airport_buffer_minutes=airport_buffer,
            transfer_count=transfer_count,
            risk_level=risk,
            confidence=confidence,
            uncomfortable_hour=outbound.departure_at.hour < 6 if outbound else False,
            luggage_penalty=0,
        )

        return DoorToDoorOptionOut(
            id=f"option_gtfs_{option_idx}",
            label=label,
            description=description,
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
            confidence=confidence,
            source_types=["open_data"],
            sources=sources,
            legs=legs,
            is_extended=not is_primary,
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
