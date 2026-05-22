"""Mock/Estimate provider for door-to-door.

Demoted to estimate_only: never presented as a primary recommendation.
Only used as fallback "Estimación orientativa" section.
No CTA, no fake booking_url, no "Marcar elegida" as if real.
"""

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorLegOut,
    DoorToDoorOptionOut,
    DoorToDoorPriceOut,
    DoorToDoorSourceOut,
)


class MockDoorToDoorProvider(DoorToDoorProvider):
    provider_name = "mock_multimodal"
    source_type = "estimate"

    TRUST_COPY = (
        "Estimación orientativa mientras no hay fuentes reales suficientes. "
        "Precios, horarios y disponibilidad no están confirmados. "
        "Usa las opciones de búsqueda externa para datos reales."
    )

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(self.provider_name, "ok", "estimate", "estimated")

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        flight = query.flight
        prefs = query.preferences
        origin = query.origin.label
        destination = query.final_destination.label
        checked_at = query.checked_at
        airport_only = query.final_destination.type == "airport_only"
        flight_duration = int((flight.arrival_at - flight.departure_at).total_seconds() / 60)

        source = DoorToDoorSourceOut(
            provider=self.provider_name,
            source_provider="mock_multimodal",
            source_type="estimate",
            confidence="estimated",
            checked_at=checked_at,
            expires_at=None,
            booking_url=None,
        )

        origin_airport_label = f"Aeropuerto de {flight.origin_airport}"
        dest_airport_label = f"Aeropuerto de {flight.destination_airport}"

        legs = [
            DoorToDoorLegOut(
                type="ground",
                mode="bus",
                from_location=origin,
                to_location=origin_airport_label,
                departure_at=None,
                arrival_at=None,
                duration_minutes=None,
                price_min=None,
                price_max=None,
                provider="mock_multimodal",
                booking_url=None,
                source_type="estimate",
                confidence="estimated",
            ),
            DoorToDoorLegOut(
                type="flight",
                mode="flight",
                from_location=flight.origin_airport,
                to_location=flight.destination_airport,
                departure_at=flight.departure_at,
                arrival_at=flight.arrival_at,
                duration_minutes=flight_duration,
                provider="flight_watch",
                source_type="estimate",
                confidence=flight.flight_time_confidence,
            ),
        ]

        if not airport_only:
            legs.append(
                DoorToDoorLegOut(
                    type="ground",
                    mode="shuttle",
                    from_location=dest_airport_label,
                    to_location=destination,
                    departure_at=None,
                    arrival_at=None,
                    duration_minutes=None,
                    price_min=None,
                    price_max=None,
                    provider="mock_multimodal",
                    booking_url=None,
                    source_type="estimate",
                    confidence="estimated",
                )
            )

        self.push_warning(
            "ESTIMATED_MOCK_DATA",
            "Esta es una estimación orientativa. No hay fuentes reales activas para confirmar precio, horario ni disponibilidad.",
        )

        return [
            DoorToDoorOptionOut(
                id="option_estimate",
                label="Estimación orientativa",
                description="Simulación aproximada del viaje puerta a puerta. Sin precios ni horarios reales confirmados.",
                status="estimate_only",
                total_price_min=None,
                total_price_max=None,
                price_per_person_min=None,
                price_per_person_max=None,
                currency="EUR",
                total_duration_minutes=None,
                risk_level="unknown",
                score=None,
                transfer_count=1 if airport_only else 2,
                airport_buffer_minutes=prefs.min_airport_buffer_minutes,
                confidence="estimated",
                source_types=["estimate"],
                sources=[source],
                legs=legs,
                is_recommended=False,
                is_extended=True,
                deep_link=None,
                price=DoorToDoorPriceOut(amount=None, currency=None, status="estimated"),
                trust_copy=self.TRUST_COPY,
            )
        ]
