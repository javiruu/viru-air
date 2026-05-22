"""BlaBlaCar deeplink provider: generates external search links.

Honest provider — no fake durations, no fake prices, no fake availability.
Generates a BlaBlaCar search URL and returns status=real_deeplink.
"""

from datetime import timedelta
from urllib.parse import urlencode

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorDeepLinkOut,
    DoorToDoorLegOut,
    DoorToDoorOptionOut,
    DoorToDoorPriceOut,
    DoorToDoorSourceOut,
)


class BlaBlaCarDeepLinkProvider(DoorToDoorProvider):
    provider_name = "blablacar_deeplink"
    source_type = "deeplink"
    search_base_url = "https://www.blablacar.es/search"

    TRUST_COPY = (
        "Viru abre la búsqueda externa en BlaBlaCar. "
        "Precio, horarios y plazas se confirman fuera de Viru."
    )

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(self.provider_name, "ok", self.source_type, "deeplink")

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        if not query.preferences.allow_rideshare:
            return []

        flight = query.flight
        checked_at = query.checked_at
        flight_duration = int((flight.arrival_at - flight.departure_at).total_seconds() / 60)
        deeplink, url_warning = self._build_deeplink(query)

        if flight.flight_time_confidence == "estimated":
            self.push_warning(
                "FLIGHT_TIME_ESTIMATED",
                "La hora de llegada del vuelo es estimada. Verifica compatibilidad con el tramo terrestre.",
            )

        self.push_warning(
            "UNCONFIRMED_PRICE",
            "Precio y disponibilidad se confirman fuera de Viru.",
            provider="blablacar_deeplink",
        )

        if url_warning:
            self.push_warning(
                "BLABLACAR_DEEPLINK_PARTIAL",
                url_warning,
                provider="blablacar_deeplink",
            )

        source = DoorToDoorSourceOut(
            provider=self.provider_name,
            source_provider="blablacar",
            source_type="deeplink",
            confidence="deeplink",
            checked_at=checked_at,
            expires_at=checked_at + timedelta(hours=2),
            booking_url=deeplink,
        )

        deep_link = DoorToDoorDeepLinkOut(
            url=deeplink,
            label="Buscar en BlaBlaCar",
            kind="provider_search",
            opens_external=True,
        )

        airport_city = self._city_for_airport(flight.origin_airport)
        airport_label = (
            f"Aeropuerto de {airport_city} {flight.origin_airport}"
            if airport_city
            else f"Aeropuerto de {flight.origin_airport}"
        )

        legs = [
            DoorToDoorLegOut(
                type="ground",
                mode="rideshare",
                from_location=query.origin.label,
                to_location=airport_label,
                departure_at=None,
                arrival_at=None,
                duration_minutes=None,
                price_min=None,
                price_max=None,
                provider="blablacar",
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

        dest_airport_city = self._city_for_airport(flight.destination_airport)
        dest_airport_label = (
            f"Aeropuerto de {dest_airport_city} {flight.destination_airport}"
            if dest_airport_city
            else f"Aeropuerto de {flight.destination_airport}"
        )
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
                    provider="local_transfer",
                    source_type="deeplink",
                    confidence="deeplink",
                )
            )

        return [
            DoorToDoorOptionOut(
                id="option_blablacar_deeplink",
                label="Buscar coche compartido en BlaBlaCar",
                description="Abre la búsqueda externa con origen, ciudad del aeropuerto y fecha del vuelo. Sin precio ni disponibilidad confirmados.",
                status="real_deeplink",
                total_price_min=None,
                total_price_max=None,
                price_per_person_min=None,
                price_per_person_max=None,
                currency="EUR",
                total_duration_minutes=None,
                risk_level="unknown",
                score=None,
                transfer_count=1,
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
        warnings: list[str] = []

        params: dict[str, str] = {}
        if query.origin.label:
            params["from"] = query.origin.label
        else:
            warnings.append("No se pudo determinar el origen para el deeplink.")

        airport_city = self._city_for_airport(flight.origin_airport)
        if airport_city:
            params["to"] = airport_city
        else:
            warnings.append("No se pudo determinar la ciudad del aeropuerto de salida.")

        if flight.departure_at:
            params["date"] = flight.departure_at.date().isoformat()
        else:
            warnings.append("No se pudo determinar la fecha del vuelo para el deeplink.")

        if query.preferences.passengers > 1:
            params["seats"] = str(query.preferences.passengers)

        deeplink = f"{self.search_base_url}?{urlencode(params)}" if params else self.search_base_url
        warning_text = "; ".join(warnings) if warnings else None

        if warnings and params:
            warning_text = (
                "El proveedor puede requerir ajustar el destino al aeropuerto. "
                + warning_text
            )

        return deeplink, warning_text

    @staticmethod
    def _city_for_airport(iata: str) -> str | None:
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
