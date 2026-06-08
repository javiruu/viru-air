"""Unified deeplink provider for door-to-door.

Generates the main actionable option with legs containing external actions.
"""

from datetime import timedelta
from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorDeepLinkOut,
    DoorToDoorLegOut,
    DoorToDoorOptionOut,
    DoorToDoorPriceOut,
    DoorToDoorSourceOut,
)
from app.door_to_door.providers.deeplink_builders import (
    build_google_maps_action,
    build_blablacar_action,
    build_goopti_action,
)

class DeeplinkDoorToDoorProvider(DoorToDoorProvider):
    provider_name = "external_deeplink"
    source_type = "external_deeplink"

    TRUST_COPY = "Precio, horario y plazas se confirman fuera de Viru."

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(self.provider_name, "ok", self.source_type, "deeplink")

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        flight = query.flight
        prefs = query.preferences
        origin = query.origin.label
        destination = query.final_destination.label
        checked_at = query.checked_at
        airport_only = query.final_destination.type == "airport_only"
        flight_duration = int((flight.arrival_at - flight.departure_at).total_seconds() / 60) if flight.departure_at and flight.arrival_at else None

        origin_airport_label = f"Aeropuerto de {flight.origin_airport}"
        dest_airport_label = f"Aeropuerto de {flight.destination_airport}"

        # Origin leg actions
        origin_actions = []
        origin_actions.append(
            build_google_maps_action(origin, origin_airport_label, "origin_to_airport:google_maps")
        )
        if prefs.allow_rideshare:
            date_str = flight.departure_at.date().isoformat() if flight.departure_at else ""
            origin_actions.append(
                build_blablacar_action(origin, origin_airport_label, date_str, prefs.passengers, "origin_to_airport:blablacar")
            )

        origin_leg = DoorToDoorLegOut(
            type="ground",
            mode="car", # Generic ground mode, as actions determine the real mode
            from_location=origin,
            to_location=origin_airport_label,
            provider="external_deeplink",
            source_type="external_deeplink",
            confidence="deeplink",
            actions=origin_actions,
        )

        flight_leg = DoorToDoorLegOut(
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
        )

        legs = [origin_leg, flight_leg]

        if not airport_only:
            dest_actions = []
            dest_actions.append(
                build_google_maps_action(dest_airport_label, destination, "arrival_to_destination:google_maps")
            )
            if prefs.allow_shuttle:
                date_str = flight.arrival_at.date().isoformat() if flight.arrival_at else ""
                dest_actions.append(
                    build_goopti_action(dest_airport_label, destination, date_str, prefs.passengers, "arrival_to_destination:goopti")
                )
            
            dest_leg = DoorToDoorLegOut(
                type="ground",
                mode="car",
                from_location=dest_airport_label,
                to_location=destination,
                provider="external_deeplink",
                source_type="external_deeplink",
                confidence="deeplink",
                actions=dest_actions,
            )
            legs.append(dest_leg)

        source = DoorToDoorSourceOut(
            provider=self.provider_name,
            source_provider="external_deeplink",
            source_type="external_deeplink",
            confidence="deeplink",
            checked_at=checked_at,
        )
        primary_action_url = (
            origin_actions[0].url
            if origin_actions
            else (dest_actions[0].url if (not airport_only and dest_actions) else "")
        )
        deep_link = (
            DoorToDoorDeepLinkOut(
                url=primary_action_url,
                label="Abrir ruta accionable",
                kind="directions",
                opens_external=True,
            )
            if primary_action_url
            else None
        )

        return [
            DoorToDoorOptionOut(
                id="option_external_actions",
                label="Ruta accionable",
                description="Tramos terrestres con búsqueda externa. Sin precio ni horario confirmado en Viru.",
                status="real_deeplink",
                currency="EUR",
                transfer_count=1 if airport_only else 2,
                confidence="deeplink",
                source_types=["external_deeplink"],
                sources=[source],
                legs=legs,
                deep_link=deep_link,
                is_extended=False,
                trust_copy=self.TRUST_COPY,
            )
        ]
