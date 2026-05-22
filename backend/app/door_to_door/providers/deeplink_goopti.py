from datetime import timedelta
from urllib.parse import urlencode

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.domain.risk import calculate_risk_level
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
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
        deeplink = self._build_deeplink(query)

        source = DoorToDoorSourceOut(
            provider=self.provider_name,
            source_provider="goopti",
            source_type="deeplink",
            confidence="deeplink",
            checked_at=checked_at,
            expires_at=checked_at + timedelta(hours=2),
            booking_url=deeplink,
        )
        estimate_source = DoorToDoorSourceOut(
            provider="viru_estimator",
            source_provider="viru_estimator",
            source_type="api",
            confidence="estimated",
            checked_at=checked_at,
            expires_at=checked_at + timedelta(hours=1),
        )

        legs = [
            DoorToDoorLegOut(
                type="ground",
                mode="bus",
                from_label=query.origin.label,
                to_label=f"Aeropuerto de Málaga {flight.origin_airport}",
                departure_at=outbound_departure,
                arrival_at=outbound_arrival,
                duration_minutes=outbound_minutes,
                price_min=None,
                price_max=None,
                provider="viru_estimator",
                source_type="api",
                confidence="estimated",
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
                from_label=f"Treviso Airport {flight.destination_airport}",
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
                description="Enlace directo para traslado final desde TSF. Precio final en proveedor.",
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
                sources=[source, estimate_source],
                legs=legs,
                is_extended=True,
            )
        ]

    def _build_deeplink(self, query: DoorToDoorProviderQuery) -> str:
        params = urlencode(
            {
                "pickup": f"Treviso Airport {query.flight.destination_airport}",
                "dropoff": query.final_destination.label,
                "date": query.flight.arrival_at.date().isoformat(),
                "passengers": query.preferences.passengers,
            }
        )
        return f"{self.search_base_url}?{params}"
