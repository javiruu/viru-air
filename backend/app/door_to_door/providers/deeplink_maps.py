"""Google Maps deeplink provider: generates actionable directions URLs.

Generates links to google.com/maps/dir for real navigation. No price.
No availability confirmation. Source status: external_search.
"""

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


class GoogleMapsDeepLinkProvider(DoorToDoorProvider):
    """Generate Google Maps directions deep links for door-to-door segments.

    Always enabled — no API key needed for the web maps.google.com URL.
    Produces status=real_deeplink, source_type=maps, no price.
    """

    provider_name = "google_maps_deeplink"
    source_type = "maps"
    base_url = "https://www.google.com/maps/dir/"

    TRUST_COPY = (
        "Viru abre direcciones reales en Google Maps. "
        "Revisa horarios, tráfico y disponibilidad antes de decidir."
    )

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(self.provider_name, "ok", self.source_type, "deeplink")

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        flight = query.flight
        checked_at = query.checked_at
        options: list[DoorToDoorOptionOut] = []

        origin_label = query.origin.label
        dest_label = query.final_destination.label
        is_airport_only = query.final_destination.type == "airport_only"

        # Segment 1: Origin → departure airport
        origin_airport_label = f"{self._city_for_airport(flight.origin_airport)} {flight.origin_airport}"

        outbound_url = self._build_directions_url(
            origin=origin_label,
            destination=origin_airport_label,
            travelmode="driving",
        )

        source = DoorToDoorSourceOut(
            provider=self.provider_name,
            source_provider="google_maps",
            source_type="maps",
            confidence="deeplink",
            checked_at=checked_at,
            expires_at=None,
            booking_url=outbound_url,
        )

        deep_link_outbound = DoorToDoorDeepLinkOut(
            url=outbound_url,
            label="Abrir en Google Maps",
            kind="directions",
            opens_external=True,
        )

        legs_outbound = [
            DoorToDoorLegOut(
                type="ground",
                mode="car",
                from_location=origin_label,
                to_location=origin_airport_label,
                departure_at=None,
                arrival_at=None,
                duration_minutes=None,
                price_min=None,
                price_max=None,
                provider="google_maps",
                booking_url=outbound_url,
                source_type="maps",
                confidence="deeplink",
            ),
            DoorToDoorLegOut(
                type="flight",
                mode="flight",
                from_location=flight.origin_airport,
                to_location=flight.destination_airport,
                departure_at=flight.departure_at,
                arrival_at=flight.arrival_at,
                duration_minutes=int(
                    (flight.arrival_at - flight.departure_at).total_seconds() / 60
                ),
                provider="flight_watch",
                source_type="api",
                confidence=flight.flight_time_confidence,
            ),
        ]

        if not is_airport_only:
            dest_airport_label = f"{self._city_for_airport(flight.destination_airport)} {flight.destination_airport}"
            inbound_url = self._build_directions_url(
                origin=dest_airport_label,
                destination=dest_label,
                travelmode="driving",
            )
            legs_outbound.append(
                DoorToDoorLegOut(
                    type="ground",
                    mode="car",
                    from_location=dest_airport_label,
                    to_location=dest_label,
                    departure_at=None,
                    arrival_at=None,
                    duration_minutes=None,
                    price_min=None,
                    price_max=None,
                    provider="google_maps",
                    booking_url=inbound_url,
                    source_type="maps",
                    confidence="deeplink",
                )
            )

        self.push_warning(
            "UNCONFIRMED_PRICE",
            "Precio y disponibilidad se confirman fuera de Viru.",
            provider=self.provider_name,
        )

        options.append(
            DoorToDoorOptionOut(
                id="option_maps_deeplink",
                label="Abrir ruta en Google Maps",
                description="Navegación real para los tramos terrestres. Sin precio confirmado.",
                status="real_deeplink",
                total_price_min=None,
                total_price_max=None,
                price_per_person_min=None,
                price_per_person_max=None,
                currency="EUR",
                total_duration_minutes=None,
                score=None,
                transfer_count=0,
                airport_buffer_minutes=None,
                confidence="deeplink",
                source_types=["maps"],
                sources=[source],
                legs=legs_outbound,
                is_recommended=False,
                is_extended=False,
                deep_link=deep_link_outbound,
                price=DoorToDoorPriceOut(
                    amount=None, currency=None, status="external"
                ),
                trust_copy=self.TRUST_COPY,
            )
        )

        return options

    def _build_directions_url(
        self,
        origin: str,
        destination: str,
        travelmode: str = "driving",
    ) -> str:
        params: dict[str, str] = {
            "api": "1",
            "origin": origin.strip(),
            "destination": destination.strip(),
            "travelmode": travelmode,
        }
        return f"{self.base_url}?{urlencode(params)}"

    @staticmethod
    def _city_for_airport(iata: str) -> str:
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
        return mapping.get(iata.upper(), iata)
