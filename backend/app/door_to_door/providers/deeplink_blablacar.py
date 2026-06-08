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
    _SEARCH_ORIGIN = "SEARCH"
    _ADULT_PASSENGER = "adult"

    # Known stable BlaBlaCar place ids captured from real search URLs.
    _PLACE_ID_BY_LABEL: dict[str, str] = {
        "almería, españa": "eyJpIjoiQ2hJSndmTE03QUNlZWcwUlhraThqaC1nblkwIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
        "alicante, españa": "eyJpIjoiQ2hJSlM2dWRPOW8xWWcwUjQ0RUxySEtvZlIwIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
        "málaga, españa": "eyJpIjoiQ2hJSkxTSGJUOFJaY2cwUnp6TEt5WkxjSldBIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
        "sevilla, españa": "eyJpIjoiQ2hJSmtXSy1GQkZzRWcwUlNGYi1IR0lZOERRIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
        "madrid, españa": "eyJpIjoiQ2hJSmdUd0tnSmNwUWcwUmFTS01ZY0hlTnNRIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
        "aeroport josep tarradellas barcelona-el prat (bcn), el prat de llobregat, españa": "eyJpIjoiQ2hJSnBZNThoR1NlcEJJUjE1dHYtMExwS19NIiwicCI6MSwidiI6MSwidCI6WzJdfQ==",
    }
    _PLACE_ID_BY_IATA: dict[str, str] = {
        "AGP": _PLACE_ID_BY_LABEL["málaga, españa"],
        "ALC": _PLACE_ID_BY_LABEL["alicante, españa"],
        "SVQ": _PLACE_ID_BY_LABEL["sevilla, españa"],
        "MAD": _PLACE_ID_BY_LABEL["madrid, españa"],
        "BCN": _PLACE_ID_BY_LABEL["aeroport josep tarradellas barcelona-el prat (bcn), el prat de llobregat, españa"],
    }

    TRUST_COPY = (
        "Viru abre la búsqueda externa en BlaBlaCar. "
        "Precio, horarios y plazas se confirman fuera de Viru."
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
        from_name = self._format_blablacar_label(query.origin.label)
        to_name = self._destination_label_for_outbound(flight.origin_airport)
        travel_date = flight.departure_at.date().isoformat() if flight.departure_at else None

        if not from_name:
            warnings.append("No se pudo determinar el origen para BlaBlaCar.")
        if not to_name:
            warnings.append("No se pudo determinar el destino para BlaBlaCar.")
        if not travel_date:
            warnings.append("No se pudo determinar la fecha del vuelo para BlaBlaCar.")

        params: dict[str, str] = {
            "search_origin": self._SEARCH_ORIGIN,
            "p0[ac]": self._ADULT_PASSENGER,
        }
        if from_name:
            params["fn"] = from_name
        if to_name:
            params["tn"] = to_name
        if travel_date:
            params["db"] = travel_date
        params["seats"] = str(max(1, int(query.preferences.passengers)))

        from_place_id = self._resolve_blablacar_place_id(
            query.origin.place_id,
            from_name,
            preferred_iata=None,
        )
        to_place_id = self._resolve_blablacar_place_id(
            None,
            to_name,
            preferred_iata=flight.origin_airport,
        )
        if from_place_id:
            params["from_place_id"] = from_place_id
        else:
            warnings.append("Ruta BlaBlaCar sin from_place_id confirmado: se usa búsqueda por texto.")
        if to_place_id:
            params["to_place_id"] = to_place_id
        else:
            warnings.append("Ruta BlaBlaCar sin to_place_id confirmado: se usa búsqueda por texto.")

        deeplink = f"{self.search_base_url}?{urlencode(params)}" if params else self.search_base_url
        warning_text = "; ".join(warnings) if warnings else None
        return deeplink, warning_text

    def _resolve_blablacar_place_id(
        self,
        candidate_place_id: str | None,
        label: str | None,
        preferred_iata: str | None,
    ) -> str | None:
        if candidate_place_id and self._is_blablacar_place_id(candidate_place_id):
            return candidate_place_id
        if preferred_iata:
            mapped_iata = self._PLACE_ID_BY_IATA.get(preferred_iata.upper())
            if mapped_iata:
                return mapped_iata
        if label:
            normalized = self._normalize_label(label)
            mapped = self._PLACE_ID_BY_LABEL.get(normalized)
            if mapped:
                return mapped
        return None

    def _destination_label_for_outbound(self, origin_airport_iata: str) -> str:
        if origin_airport_iata.upper() == "BCN":
            return "Aeroport Josep Tarradellas Barcelona-El Prat (BCN), El Prat de Llobregat, España"
        city = self._city_for_airport(origin_airport_iata) or origin_airport_iata
        return self._format_blablacar_label(city)

    @staticmethod
    def _is_blablacar_place_id(value: str) -> bool:
        token = value.strip()
        return token.startswith("eyJ") and len(token) >= 24

    @staticmethod
    def _normalize_label(value: str) -> str:
        return " ".join(value.strip().lower().split())

    def _format_blablacar_label(self, value: str | None) -> str:
        if not value:
            return ""
        normalized = " ".join(value.strip().split())
        lowered = normalized.lower()
        if "," in normalized:
            return normalized
        if "aeroport " in lowered or "aeropuerto " in lowered:
            return f"{normalized}, España" if "españa" not in lowered else normalized
        return f"{normalized}, España"

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
