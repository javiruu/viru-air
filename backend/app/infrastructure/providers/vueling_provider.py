from __future__ import annotations

from datetime import datetime
import os
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider

_PROVIDER_POOL_SIZE = 32
_DEFAULT_BOOKING_URL = "https://tickets.vueling.com/booking/flightSearch"


class VuelingProvider(FlightProvider):
    provider_id = "vueling"

    def __init__(
        self,
        api_token: str | None = None,
        *,
        prices_url: str | None = None,
        product_class: str | None = None,
    ) -> None:
        self.api_token = (api_token or os.getenv("VUELING_FLIGHTCALENDAR_TOKEN", "")).strip()
        self.prices_url = (
            prices_url or os.getenv("VUELING_FLIGHTCALENDAR_PRICES_URL", "")
        ).strip()
        self.product_class = (product_class or os.getenv("VUELING_PRODUCT_CLASS", "BA")).strip().upper()
        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def is_enabled(self) -> bool:
        return bool(self.api_token and self.prices_url)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        if not self.is_enabled():
            raise ProviderSourceFetchError(
                warning_codes=["vueling_not_configured"],
                message="Vueling provider is not configured",
                provider_id=self.provider_id,
                severity="warning",
            )

        origin = origin.upper().strip()
        destination = destination.upper().strip()
        try:
            body = self._fetch_calendar_prices(travel_date, timeout_ms=timeout_ms)
        except requests.RequestException as exc:
            raise ProviderSourceFetchError(
                warning_codes=["vueling_provider_unavailable_total", "provider_total_outage"],
                message=f"Vueling provider unavailable for {origin}->{destination} on {travel_date}",
                provider_id=self.provider_id,
                severity="error",
            ) from exc

        flights = self._extract_flights(
            body,
            origin=origin,
            destination=destination,
            travel_date=travel_date,
            fallback_currency=currency,
        )
        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(code="provider_empty_result", provider=self.provider_id, severity="info")
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_calendar_prices(self, travel_date: str, *, timeout_ms: int) -> dict:
        parsed_date = datetime.fromisoformat(travel_date).strftime("%Y%m%d")
        response = self._session.get(
            self.prices_url,
            params={"startDate": parsed_date, "numDays": "1", "productClass": self.product_class},
            timeout=max(2.0, timeout_ms / 1000),
            headers={"Authorization": self.api_token, "Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def _extract_flights(
        self,
        payload: dict,
        *,
        origin: str,
        destination: str,
        travel_date: str,
        fallback_currency: str,
    ) -> list[ProviderFlight]:
        flights: list[ProviderFlight] = []
        for day in payload.get("Result") or payload.get("result") or []:
            for item in day.get("Items") or day.get("items") or []:
                flight = self._flight_from_item(
                    str(item),
                    origin=origin,
                    destination=destination,
                    travel_date=travel_date,
                    fallback_currency=fallback_currency,
                )
                if flight is not None:
                    flights.append(flight)
        return flights

    def _flight_from_item(
        self,
        item: str,
        *,
        origin: str,
        destination: str,
        travel_date: str,
        fallback_currency: str,
    ) -> ProviderFlight | None:
        if "~" not in item:
            return None
        general_raw, segments_raw = item.split("~", 1)
        general = general_raw.split(";")
        segments = [segment.split(";") for segment in segments_raw.split("^") if segment]
        if len(general) < 3 or not segments:
            return None
        if any(len(segment) < 5 for segment in segments):
            return None
        if segments[0][2].upper() != origin or segments[-1][4].upper() != destination:
            return None
        departure_raw = segments[0][3]
        if self._to_iso_date(departure_raw) != travel_date:
            return None

        amount = self._price_from_item(general, segments)
        if amount is None:
            return None

        return ProviderFlight(
            price=amount,
            currency=(general[0] or fallback_currency).upper(),
            departure_time_local=self._to_time(departure_raw),
            captured_at=utc_now_naive(),
            source="vueling-flight-calendar",
            deeplink_url=self._build_deeplink(origin, destination, travel_date, general[0] or fallback_currency),
        )

    def _price_from_item(self, general: list[str], segments: list[list[str]]) -> float | None:
        if len(segments[0]) == 9:
            return self._positive_float(general[2])

        segment_total = 0.0
        for segment in segments:
            if len(segment) < 10:
                return None
            amount = self._positive_float(segment[7])
            if amount is None:
                return None
            segment_total += amount

        connection_fee = self._positive_float(general[2]) or 0.0
        total = segment_total + connection_fee
        return total if total > 0.0 else None

    def _build_deeplink(self, origin: str, destination: str, travel_date: str, currency: str) -> str:
        params = {
            "o": origin,
            "d": destination,
            "dd": travel_date,
            "rd": "",
            "adt": "1",
            "chd": "0",
            "inf": "0",
            "extraseat": "0",
            "c": "en-GB",
            "cur": currency.upper(),
            "dt": "",
        }
        return f"{_DEFAULT_BOOKING_URL}?{urlencode(params)}"

    def _to_iso_date(self, value: str) -> str | None:
        try:
            return datetime.strptime(value, "%d/%m/%Y %H:%M:%S").date().isoformat()
        except ValueError:
            return None

    def _to_time(self, value: str) -> str | None:
        try:
            return datetime.strptime(value, "%d/%m/%Y %H:%M:%S").strftime("%H:%M")
        except ValueError:
            return None

    def _positive_float(self, value: str) -> float | None:
        try:
            amount = float(value)
        except ValueError:
            return None
        return amount if amount > 0.0 else None
