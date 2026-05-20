from datetime import timedelta

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.domain.risk import calculate_risk_level
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import DoorToDoorLegOut, DoorToDoorOptionOut, DoorToDoorSourceOut


class MockDoorToDoorProvider(DoorToDoorProvider):
    provider_name = "mock_multimodal"
    source_type = "mock"

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(self.provider_name, "ok", "mock", "estimated")

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        flight = query.flight
        prefs = query.preferences
        origin = query.origin.label
        destination = query.final_destination.label
        checked_at = query.checked_at
        airport_only = query.final_destination.type == "airport_only"
        luggage_penalty = 4 if prefs.luggage == "checked" else 1 if prefs.luggage == "cabin" else 0

        seeds = [
            ("option_best", "Mejor equilibrio", "Sales con margen cómodo antes del vuelo.", "bus", 230, 18, 28, 140, 2),
            ("option_cheap", "Más barata", "Ahorra dinero, pero depende de más cambios.", "train", 285, 14, 22, 105, 4),
            ("option_safe", "Menos riesgo", "Menos cambios y margen amplio antes de embarcar.", "shuttle", 195, 34, 52, 175, 1),
            ("option_fast", "Más rápida", "Reduce tiempo total con traslado directo hasta la terminal.", "car", 170, 42, 62, 125, 1),
            ("option_public", "Transporte público", "Prioriza bus y tren con coste controlado.", "bus", 255, 20, 34, 130, 3),
            ("option_shared", "Coche compartido", "Buena opción si aparece una salida compatible.", "rideshare", 210, 24, 38, 115, 2),
        ]
        if prefs.public_transport_only:
            seeds = [seed for seed in seeds if seed[3] in {"bus", "train"}]
        if not prefs.allow_rideshare:
            seeds = [seed for seed in seeds if seed[3] != "rideshare"]
        if not prefs.allow_shuttle:
            seeds = [seed for seed in seeds if seed[3] != "shuttle"]
        if not prefs.allow_car:
            seeds = [seed for seed in seeds if seed[3] != "car"]

        options: list[DoorToDoorOptionOut] = []
        flight_duration = int((flight.arrival_at - flight.departure_at).total_seconds() / 60)
        for index, (option_id, label, description, mode, outbound_minutes, base_min, base_max, buffer_minutes, transfers) in enumerate(seeds):
            outbound_arrival = flight.departure_at - timedelta(minutes=buffer_minutes)
            outbound_departure = outbound_arrival - timedelta(minutes=outbound_minutes)
            source_provider = f"mock_{mode}"
            source = DoorToDoorSourceOut(
                provider=source_provider,
                source_provider=source_provider,
                source_type="mock",
                confidence="estimated",
                checked_at=checked_at,
                expires_at=checked_at + timedelta(hours=6),
            )
            price_multiplier = prefs.passengers if mode in {"bus", "train", "rideshare"} else max(1, prefs.passengers * 0.72)
            outbound_price_min = round(base_min * price_multiplier, 2)
            outbound_price_max = round(base_max * price_multiplier, 2)
            legs = [
                DoorToDoorLegOut(
                    type="ground",
                    mode=mode,
                    from_label=origin,
                    to_label=f"Aeropuerto de Málaga {flight.origin_airport}",
                    departure_at=outbound_departure,
                    arrival_at=outbound_arrival,
                    duration_minutes=outbound_minutes,
                    price_min=outbound_price_min,
                    price_max=outbound_price_max,
                    provider=source_provider,
                    booking_url=None,
                    source_type="mock",
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
                    source_type="mock",
                    confidence=flight.flight_time_confidence,
                ),
            ]
            inbound_price_min = 0.0
            inbound_price_max = 0.0
            inbound_minutes = 0
            if not airport_only:
                inbound_minutes = 40 + (index % 3) * 12
                inbound_departure = flight.arrival_at + timedelta(minutes=25 + (index % 2) * 10)
                inbound_arrival = inbound_departure + timedelta(minutes=inbound_minutes)
                inbound_mode = "shuttle" if mode != "train" else "train"
                inbound_provider = f"mock_{inbound_mode}"
                inbound_price_min = round((12 + index * 2) * max(1, prefs.passengers * 0.82), 2)
                inbound_price_max = round((20 + index * 3) * max(1, prefs.passengers * 0.82), 2)
                legs.append(
                    DoorToDoorLegOut(
                        type="ground",
                        mode=inbound_mode,
                        from_label=f"Treviso Airport {flight.destination_airport}",
                        to_label=destination,
                        departure_at=inbound_departure,
                        arrival_at=inbound_arrival,
                        duration_minutes=inbound_minutes,
                        price_min=inbound_price_min,
                        price_max=inbound_price_max,
                        provider=inbound_provider,
                        booking_url=None,
                        source_type="mock",
                        confidence="estimated",
                    )
                )
            total_min = outbound_price_min + inbound_price_min
            total_max = outbound_price_max + inbound_price_max
            total_duration = outbound_minutes + flight_duration + inbound_minutes + buffer_minutes
            risk = calculate_risk_level(buffer_minutes, transfers, "estimated")
            score = score_itinerary(
                price_midpoint=(total_min + total_max) / 2,
                duration_minutes=total_duration,
                airport_buffer_minutes=buffer_minutes,
                transfer_count=transfers,
                risk_level=risk,
                confidence="estimated",
                uncomfortable_hour=outbound_departure.hour < 6,
                luggage_penalty=luggage_penalty,
            )
            options.append(
                DoorToDoorOptionOut(
                    id=option_id,
                    label=label,
                    description=description,
                    total_price_min=round(total_min, 2),
                    total_price_max=round(total_max, 2),
                    price_per_person_min=round(total_min / prefs.passengers, 2),
                    price_per_person_max=round(total_max / prefs.passengers, 2),
                    currency="EUR",
                    total_duration_minutes=total_duration,
                    risk_level=risk,
                    score=score,
                    transfer_count=transfers,
                    airport_buffer_minutes=buffer_minutes,
                    confidence="estimated",
                    source_types=["mock"],
                    sources=[source],
                    legs=legs,
                    is_extended=index >= 3,
                )
            )
        return options
