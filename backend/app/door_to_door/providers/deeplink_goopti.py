from datetime import timedelta
from urllib.parse import urlencode

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.domain.risk import calculate_risk_level
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.providers.deeplink_blablacar import BlaBlaCarDeepLinkProvider
from app.door_to_door.schemas import DoorToDoorLegOut, DoorToDoorOptionOut, DoorToDoorSourceOut


class GoOptiDeepLinkProvider(DoorToDoorProvider):
    provider_name = "goopti_deeplink"
    source_type = "deeplink"
    search_base_url = "https://www.goopti.com/es/"

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(self.provider_name, "ok", self.source_type, "deeplink")

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        if query.final_destination.type == "airport_only":
            return []
        if not query.preferences.allow_shuttle:
            return []

        flight = query.flight
        checked_at = query.checked_at
        airport_buffer = max(query.preferences.min_airport_buffer_minutes, 120)
        outbound_minutes = 210
        outbound_arrival = flight.departure_at - timedelta(minutes=airport_buffer)
        outbound_departure = outbound_arrival - timedelta(minutes=outbound_minutes)
        flight_duration = int((flight.arrival_at - flight.departure_at).total_seconds() / 60)
        inbound_minutes = 55
        inbound_departure = flight.arrival_at + timedelta(minutes=30)
        inbound_arrival = inbound_departure + timedelta(minutes=inbound_minutes)
        deeplink, url_warning = self._build_deeplink(query)

        if flight.flight_time_confidence == "estimated":
            self.push_warning(
                "FLIGHT_TIME_ESTIMATED",
                "La hora de llegada del vuelo es estimada. Verifica compatibilidad con el traslado.",
            )

        self.push_warning(
            "UNCONFIRMED_PRICE",
            "Precio y disponibilidad se confirman fuera de Viru.",
            provider="goopti_deeplink",
        )

        if url_warning:
            self.push_warning(
                "GOOPTI_DEEPLINK_PARTIAL",
                url_warning,
                provider="goopti_deeplink",
            )

        source = DoorToDoorSourceOut(
            provider=self.provider_name,
            source_provider="goopti",
            source_type="deeplink",
            confidence="deeplink",
            checked_at=checked_at,
            expires_at=checked_at + timedelta(hours=2),
            booking_url=deeplink,
        )

        origin_airport_city = BlaBlaCarDeepLinkProvider._city_for_airport(flight.origin_airport)
        origin_airport_label = f"Aeropuerto de {origin_airport_city} {flight.origin_airport}" if origin_airport_city else f"Aeropuerto de {flight.origin_airport}"
        dest_airport_city = BlaBlaCarDeepLinkProvider._city_for_airport(flight.destination_airport)
        dest_airport_label = f"Aeropuerto de {dest_airport_city} {flight.destination_airport}" if dest_airport_city else f"Aeropuerto de {flight.destination_airport}"

        legs = [
            DoorToDoorLegOut(
                type="ground",
                mode="bus",
                from_label=query.origin.label,
                to_label=origin_airport_label,
                departure_at=outbound_departure,
                arrival_at=outbound_arrival,
                duration_minutes=outbound_minutes,
                price_min=None,
                price_max=None,
                provider="local_transfer",
                source_type="deeplink",
                confidence="deeplink",
            ),
            DoorToDoorLegOut(
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
            ),
            DoorToDoorLegOut(
                type="ground",
                mode="shuttle",
                from_label=dest_airport_label,
                to_label=query.final_destination.label,
                departure_at=inbound_departure,
                arrival_at=inbound_arrival,
                duration_minutes=inbound_minutes,
                price_min=None,
                price_max=None,
                provider="goopti",
                booking_url=deeplink,
                source_type="deeplink",
                confidence="deeplink",
            ),
        ]

        total_duration = outbound_minutes + airport_buffer + flight_duration + inbound_minutes
        risk = calculate_risk_level(airport_buffer, 2, "deeplink")
        score = score_itinerary(
            price_midpoint=None,
            duration_minutes=total_duration,
            airport_buffer_minutes=airport_buffer,
            transfer_count=2,
            risk_level=risk,
            confidence="deeplink",
            uncomfortable_hour=outbound_departure.hour < 6,
            luggage_penalty=0,
        )

        return [
            DoorToDoorOptionOut(
                id="option_goopti_deeplink",
                label="Llegada con GoOpti",
                description="Enlace directo para traslado final desde aeropuerto de llegada. Precio final en proveedor.",
                total_price_min=None,
                total_price_max=None,
                price_per_person_min=None,
                price_per_person_max=None,
                currency="EUR",
                total_duration_minutes=total_duration,
                risk_level=risk,
                score=score,
                transfer_count=2,
                airport_buffer_minutes=airport_buffer,
                confidence="deeplink",
                source_types=["deeplink", "api"],
                sources=[source],
                legs=legs,
                is_extended=True,
            )
        ]

    def _build_deeplink(self, query: DoorToDoorProviderQuery) -> tuple[str, str | None]:
        flight = query.flight
        warnings: list[str] = []

        params: dict[str, str] = {}

        # pickup = airport of arrival
        airport_label = f"Aeropuerto de {flight.destination_airport}"
        params["pickup"] = airport_label

        if query.final_destination.label:
            params["dropoff"] = query.final_destination.label
        else:
            warnings.append("No se pudo determinar el destino final para el deeplink.")

        if flight.arrival_at:
            params["date"] = flight.arrival_at.date().isoformat()
        else:
            warnings.append("No se pudo determinar la fecha de llegada para el deeplink.")

        if query.preferences.passengers > 1:
            params["passengers"] = str(query.preferences.passengers)

        deeplink = f"{self.search_base_url}?{urlencode(params)}" if params else self.search_base_url
        warning_text = "; ".join(warnings) if warnings else None

        return deeplink, warning_text
