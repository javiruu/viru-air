from datetime import timedelta
from urllib.parse import urlencode

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.domain.risk import calculate_risk_level
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import DoorToDoorLegOut, DoorToDoorOptionOut, DoorToDoorSourceOut


class BlaBlaCarDeepLinkProvider(DoorToDoorProvider):
    provider_name = "blablacar_deeplink"
    source_type = "deeplink"
    search_base_url = "https://www.blablacar.es/search"

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(self.provider_name, "ok", self.source_type, "deeplink")

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        if not query.preferences.allow_rideshare:
            return []

        flight = query.flight
        checked_at = query.checked_at
        airport_buffer = max(query.preferences.min_airport_buffer_minutes, 120)
        outbound_minutes = 230
        outbound_arrival = flight.departure_at - timedelta(minutes=airport_buffer)
        outbound_departure = outbound_arrival - timedelta(minutes=outbound_minutes)
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

        airport_city = self._city_for_airport(flight.origin_airport)
        airport_label = f"Aeropuerto de {airport_city} {flight.origin_airport}" if airport_city else f"Aeropuerto de {flight.origin_airport}"

        legs = [
            DoorToDoorLegOut(
                type="ground",
                mode="rideshare",
                from_label=query.origin.label,
                to_label=airport_label,
                departure_at=outbound_departure,
                arrival_at=outbound_arrival,
                duration_minutes=outbound_minutes,
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
                from_label=flight.origin_airport,
                to_label=flight.destination_airport,
                departure_at=flight.departure_at,
                arrival_at=flight.arrival_at,
                duration_minutes=flight_duration,
                provider="flight_watch",
                source_type="api",
                confidence=flight.flight_time_confidence,
            ),
        ]

        inbound_minutes = 0
        transfer_count = 1
        dest_airport_city = self._city_for_airport(flight.destination_airport)
        dest_airport_label = f"Aeropuerto de {dest_airport_city} {flight.destination_airport}" if dest_airport_city else f"Aeropuerto de {flight.destination_airport}"
        if query.final_destination.type != "airport_only":
            inbound_minutes = 45
            inbound_departure = flight.arrival_at + timedelta(minutes=35)
            inbound_arrival = inbound_departure + timedelta(minutes=inbound_minutes)
            transfer_count = 2
            legs.append(
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
                    provider="local_transfer",
                    source_type="deeplink",
                    confidence="deeplink",
                )
            )

        total_duration = outbound_minutes + airport_buffer + flight_duration + inbound_minutes
        risk = calculate_risk_level(airport_buffer, transfer_count, "deeplink")
        score = score_itinerary(
            price_midpoint=None,
            duration_minutes=total_duration,
            airport_buffer_minutes=airport_buffer,
            transfer_count=transfer_count,
            risk_level=risk,
            confidence="deeplink",
            uncomfortable_hour=outbound_departure.hour < 6,
            luggage_penalty=0,
        )

        return [
            DoorToDoorOptionOut(
                id="option_blablacar_deeplink",
                label="Ruta con BlaBlaCar",
                description="Enlace directo para tramo terrestre de salida. Precio final en proveedor.",
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
