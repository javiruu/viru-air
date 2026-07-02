from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import os
import random
import time
from typing import Final
from urllib.parse import urlencode

try:
    from curl_cffi import requests
    from curl_cffi.requests.errors import RequestsError
except ImportError:
    import requests
    from requests.exceptions import RequestException as RequestsError
from requests.adapters import HTTPAdapter

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider

type JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]

_DEFAULT_BASE_URL: Final = "https://www.easyjet.com"
_DEFAULT_LANGUAGE_CODE: Final = "EN"
_PROVIDER_POOL_SIZE: Final = 32


@dataclass(frozen=True, slots=True)
class _EasyJetSearch:
    origin: str
    destination: str
    travel_date: str
    currency: str


class EasyJetProvider(FlightProvider):
    provider_id = "easyjet"

    def __init__(self, *, base_url: str | None = None, language_code: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("EASYJET_BASE_URL", _DEFAULT_BASE_URL)).strip().rstrip("/")
        self.language_code = (
            language_code or os.getenv("EASYJET_LANGUAGE_CODE", _DEFAULT_LANGUAGE_CODE)
        ).strip().upper()
        try:
            self._session = requests.Session(impersonate="chrome110")
        except TypeError:
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)

    def is_enabled(self) -> bool:
        return bool(self.base_url and self.language_code)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        search = _EasyJetSearch(
            origin=origin.upper().strip(),
            destination=destination.upper().strip(),
            travel_date=travel_date,
            currency=currency.upper().strip(),
        )
        try:
            payload = self._fetch_public_availability(search, timeout_ms=timeout_ms)
        except (RequestsError, ValueError) as exc:
            raise ProviderSourceFetchError(
                warning_codes=["easyjet_provider_unavailable_total", "provider_total_outage"],
                message=f"easyJet provider unavailable for {search.origin}->{search.destination} on {search.travel_date}",
                provider_id=self.provider_id,
                severity="error",
            ) from exc

        flights = self._extract_flights(payload, search)
        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(code="provider_empty_result", provider=self.provider_id, severity="info")
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_public_availability(self, search: _EasyJetSearch, *, timeout_ms: int) -> Mapping[str, JsonValue]:
        response = self._session.get(
            f"{self.base_url}/ejavailability/api/v16/availability/query",
            params=self._build_query_params(search),
            timeout=max(2.0, timeout_ms / 1000),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/en/buy/flights",
            },
        )
        time.sleep(random.uniform(0.1, 0.4))
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderSourceFetchError(
                warning_codes=["easyjet_provider_unavailable_total", "provider_total_outage"],
                message="easyJet provider returned a non-JSON response",
                provider_id=self.provider_id,
                severity="error",
                meta={"reason": "invalid_json"},
            ) from exc
        return payload if isinstance(payload, dict) else {}

    def _build_query_params(self, search: _EasyJetSearch) -> dict[str, str]:
        return {
            "AdditionalSeats": "0",
            "AdultSeats": "1",
            "ArrivalIata": search.destination,
            "ChildSeats": "0",
            "DepartureIata": search.origin,
            "IncludeAdminFees": "true",
            "IncludeFlexiFares": "false",
            "IncludeLowestFareSeats": "true",
            "IncludePrices": "true",
            "Infants": "0",
            "IsTransfer": "false",
            "LanguageCode": self.language_code,
            "MaxDepartureDate": search.travel_date,
            "MaxReturnDate": search.travel_date,
            "MinDepartureDate": search.travel_date,
            "MinReturnDate": search.travel_date,
        }

    def _extract_flights(
        self, payload: Mapping[str, JsonValue], search: _EasyJetSearch
    ) -> list[ProviderFlight]:
        raw_flights = payload.get("AvailableFlights")
        if not isinstance(raw_flights, list):
            return []
        flights: list[ProviderFlight] = []
        for item in raw_flights:
            if not isinstance(item, dict):
                continue
            flight = self._flight_from_item(item, search)
            if flight is not None:
                flights.append(flight)
        return flights

    def _flight_from_item(
        self, item: Mapping[str, JsonValue], search: _EasyJetSearch
    ) -> ProviderFlight | None:
        if self._normalized_text(item.get("DepartureIata")) != search.origin:
            return None
        if self._normalized_text(item.get("ArrivalIata")) != search.destination:
            return None

        departure_raw = self._text_or_empty(item.get("LocalDepartureTime"))
        if self._to_iso_date(departure_raw) != search.travel_date:
            return None

        amount = self._lowest_adult_price(item.get("FlightFares"))
        if amount is None:
            return None

        return ProviderFlight(
            price=amount,
            currency=search.currency,
            departure_time_local=self._to_time(departure_raw),
            captured_at=utc_now_naive(),
            source="easyjet-public-availability",
            deeplink_url=self._build_deeplink(search),
        )

    def _lowest_adult_price(self, raw_fares: JsonValue) -> float | None:
        if not isinstance(raw_fares, list):
            return None
        prices: list[float] = []
        for raw_fare in raw_fares:
            if not isinstance(raw_fare, dict):
                continue
            seats_available = raw_fare.get("SeatsAvailable")
            if isinstance(seats_available, int) and seats_available <= 0:
                continue
            raw_price = self._adult_price_from_fare(raw_fare)
            amount = self._positive_float(raw_price)
            if amount is not None:
                prices.append(amount)
        return min(prices) if prices else None

    def _adult_price_from_fare(self, fare: Mapping[str, JsonValue]) -> JsonValue:
        raw_prices = fare.get("Prices")
        if not isinstance(raw_prices, dict):
            return None
        raw_adult = raw_prices.get("Adult")
        if not isinstance(raw_adult, dict):
            return None
        return raw_adult.get("Price")

    def _build_deeplink(self, search: _EasyJetSearch) -> str:
        params = {
            "lang": self.language_code,
            "dep": search.origin,
            "dest": search.destination,
            "dd": search.travel_date,
            "apax": "1",
            "cpax": "0",
            "ipax": "0",
            "isOneWay": "on",
            "pid": "www.easyjet.com",
        }
        return f"{self.base_url}/deeplink?{urlencode(params)}"

    def _normalized_text(self, value: JsonValue) -> str:
        return self._text_or_empty(value).upper().strip()

    def _text_or_empty(self, value: JsonValue) -> str:
        return value if isinstance(value, str) else ""

    def _to_iso_date(self, value: str) -> str | None:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return None

    def _to_time(self, value: str) -> str | None:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%H:%M")
        except ValueError:
            return None

    def _positive_float(self, value: JsonValue) -> float | None:
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return None
        return amount if amount > 0.0 else None
