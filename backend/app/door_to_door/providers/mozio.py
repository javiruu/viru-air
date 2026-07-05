"""Mozio deeplink provider: generates external airport transfer search links.

Honest provider — no fake durations, no fake prices, no fake availability.
Generates a Mozio public search URL and returns status=real_deeplink.

Mozio is a global airport transfer aggregator; the search URL accepts both
ground legs (origin -> origin airport, arrival airport -> final destination)
as `start_name` + `end_name` + `ride_date` + `num_passengers`, so we surface
the whole trip in a single external action.
"""

from datetime import timedelta
from urllib.parse import urlencode

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.providers.deeplink_builders import airport_city
from app.door_to_door.schemas import (
    DoorToDoorDeepLinkOut,
    DoorToDoorLegOut,
    DoorToDoorOptionOut,
    DoorToDoorPriceOut,
    DoorToDoorSourceOut,
)


class MozioDeepLinkProvider(DoorToDoorProvider):
    provider_name = "mozio_deeplink"
    source_type = "deeplink"
    search_base_url = "https://www.mozio.com/search"

    TRUST_COPY = (
        "Viru abre la búsqueda externa en Mozio. "
        "Precio, horarios y transfers se confirman fuera de Viru."
    )

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(self.provider_name, "ok", self.source_type, "deeplink")

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        flight = query.flight
        checked_at = query.checked_at
        flight_duration = int((flight.arrival_at - flight.departure_at).total_seconds() / 60)
        deeplink, url_warning = self._build_deeplink(query)

        if flight.flight_time_confidence == "estimated":
            self.push_warning(
                "FLIGHT_TIME_ESTIMATED",
                "La hora del vuelo es estimada. Verifica compatibilidad con el transfer.",
            )

        self.push_warning(
            "UNCONFIRMED_PRICE",
            "Precio y disponibilidad se confirman fuera de Viru.",
            provider="mozio_deeplink",
        )

        if url_warning:
            self.push_warning(
                "MOZIO_DEEPLINK_PARTIAL",
                url_warning,
                provider="mozio_deeplink",
            )

        source = DoorToDoorSourceOut(
            provider=self.provider_name,
            source_provider="mozio",
            source_type="deeplink",
            confidence="deeplink",
            checked_at=checked_at,
            expires_at=checked_at + timedelta(hours=2),
            booking_url=deeplink,
        )

        deep_link = DoorToDoorDeepLinkOut(
            url=deeplink,
            label="Buscar transfer en Mozio",
            kind="provider_search",
            opens_external=True,
        )

        origin_airport_label = f"Aeropuerto de {airport_city(flight.origin_airport)} {flight.origin_airport}"
        dest_airport_label = f"Aeropuerto de {airport_city(flight.destination_airport)} {flight.destination_airport}"

        legs = [
            DoorToDoorLegOut(
                type="ground",
                mode="shuttle",
                from_location=query.origin.label,
                to_location=origin_airport_label,
                departure_at=None,
                arrival_at=None,
                duration_minutes=None,
                price_min=None,
                price_max=None,
                provider="mozio",
                booking_url=deeplink,
                source_type="deeplink",
                confidence="deeplink",
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
                source_type="api",
                confidence=flight.flight_time_confidence,
            ),
        ]

        if query.final_destination.type != "airport_only":
            legs.append(
                DoorToDoorLegOut(
                    type="ground",
                    mode="shuttle",
                    from_location=dest_airport_label,
                    to_location=query.final_destination.label,
                    departure_at=None,
                    arrival_at=None,
                    duration_minutes=None,
                    price_min=None,
                    price_max=None,
                    provider="mozio",
                    booking_url=deeplink,
                    source_type="deeplink",
                    confidence="deeplink",
                )
            )

        transfer_count = 2 if query.final_destination.type != "airport_only" else 1

        return [
            DoorToDoorOptionOut(
                id="option_mozio_deeplink",
                label="Buscar transfer en Mozio",
                description=(
                    "Abre la búsqueda externa de transfers globales con origen, destino y "
                    "fecha del vuelo. Sin precio ni disponibilidad confirmados."
                ),
                status="real_deeplink",
                total_price_min=None,
                total_price_max=None,
                price_per_person_min=None,
                price_per_person_max=None,
                currency="EUR",
                total_duration_minutes=None,
                score=None,
                transfer_count=transfer_count,
                airport_buffer_minutes=None,
                confidence="deeplink",
                source_types=["deeplink", "api"],
                sources=[source],
                legs=legs,
                is_recommended=False,
                is_extended=False,
                deep_link=deep_link,
                price=DoorToDoorPriceOut(amount=None, currency=None, status="external"),
                trust_copy=self.TRUST_COPY,
            )
        ]

    def _build_deeplink(self, query: DoorToDoorProviderQuery) -> tuple[str, str | None]:
        flight = query.flight
        prefs = query.preferences
        warnings: list[str] = []

        airport_only = query.final_destination.type == "airport_only"

        # Mozio aggregates both ground legs into a single search; when the
        # destination is airport-only, we point the destination to the
        # arrival airport city so the user lands on a real search on Mozio.
        if airport_only:
            destination_label = f"Aeropuerto de {airport_city(flight.destination_airport)} {flight.destination_airport}"
        else:
            destination_label = query.final_destination.label

        params: dict[str, str] = {
            "start_name": query.origin.label,
            "end_name": destination_label,
        }

        ride_date = flight.arrival_at.date().isoformat() if flight.arrival_at else None
        if ride_date:
            params["ride_date"] = ride_date
        else:
            warnings.append("No se pudo determinar la fecha del vuelo para Mozio.")

        # Only emit num_passengers when party size > 1 — Mozio's public form
        # defaults to 1 pax, so an explicit param would be redundant noise.
        if prefs.passengers > 1:
            params["num_passengers"] = str(prefs.passengers)

        origin_coords: tuple[float, float] | None = None
        if query.origin.lat is not None and query.origin.lng is not None:
            origin_coords = (float(query.origin.lat), float(query.origin.lng))
        if origin_coords:
            params["start_lat"] = f"{origin_coords[0]:.6f}"
            params["start_lng"] = f"{origin_coords[1]:.6f}"

        if not airport_only and query.final_destination.lat is not None and query.final_destination.lng is not None:
            dest_coords = (float(query.final_destination.lat), float(query.final_destination.lng))
            params["end_lat"] = f"{dest_coords[0]:.6f}"
            params["end_lng"] = f"{dest_coords[1]:.6f}"

        if not query.origin.label:
            warnings.append("No se pudo determinar el origen para Mozio.")
        if not destination_label:
            warnings.append("No se pudo determinar el destino para Mozio.")

        deeplink = f"{self.search_base_url}?{urlencode(params)}" if params else self.search_base_url
        warning_text = "; ".join(warnings) if warnings else None
        return deeplink, warning_text
