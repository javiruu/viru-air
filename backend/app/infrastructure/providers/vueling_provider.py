from __future__ import annotations

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

_DEFAULT_BASE_URL: Final = "https://ams.vueling.com"
_DEFAULT_BOOKING_URL: Final = "https://tickets.vueling.com/booking/flightSearch"
_DEFAULT_PROFILE_ID: Final = "e8ffa738-cb67-4a02-b501-9bfd975a4b65"
_FLIGHT_TYPE_ONE_WAY: Final = "ONE_WAY"
_MONTHS_RANGE: Final = 17
_PROVIDER_POOL_SIZE: Final = 32


@dataclass(frozen=True, slots=True)
class _VuelingSearch:
    origin: str
    destination: str
    travel_date: str
    currency: str


class VuelingProvider(FlightProvider):
    provider_id = "vueling"

    def __init__(self, *, base_url: str | None = None, profile_id: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("VUELING_BASE_URL", _DEFAULT_BASE_URL)).strip().rstrip("/")
        self.profile_id = (profile_id or os.getenv("VUELING_PROFILE_ID", _DEFAULT_PROFILE_ID)).strip()
        try:
            self._session = requests.Session(impersonate="chrome110")
        except TypeError:
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)

    def is_enabled(self) -> bool:
        return bool(self.base_url and self.profile_id)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        search = _VuelingSearch(
            origin=origin.upper().strip(),
            destination=destination.upper().strip(),
            travel_date=travel_date,
            currency=currency.upper().strip(),
        )
        try:
            token = self._get_anonymous_token(timeout_ms=timeout_ms)
            payload = self._fetch_public_availability(search, token, timeout_ms=timeout_ms)
        except RequestsError as exc:
            raise ProviderSourceFetchError(
                warning_codes=["vueling_provider_unavailable_total", "provider_total_outage"],
                message=f"Vueling provider unavailable for {search.origin}->{search.destination} on {search.travel_date}",
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

    def _get_anonymous_token(self, *, timeout_ms: int) -> str:
        payload = self._post_json(
            f"{self.base_url}/asm/v1/Auth",
            json_body={"profileId": self.profile_id},
            timeout_ms=timeout_ms,
        )
        token = payload.get("accessToken") if isinstance(payload, dict) else None
        if not token:
            raise ProviderSourceFetchError(
                warning_codes=["vueling_provider_unavailable_total", "provider_total_outage"],
                message="Vueling anonymous session did not return an access token",
                provider_id=self.provider_id,
                severity="error",
            )
        return str(token)

    def _fetch_public_availability(self, search: _VuelingSearch, token: str, *, timeout_ms: int) -> list:
        parsed_date = datetime.fromisoformat(search.travel_date)
        payload = self._post_json(
            f"{self.base_url}/avy/v3/AvailabilityServices/allFlights",
            json_body={
                "originCode": search.origin,
                "destinationCode": search.destination,
                "year": parsed_date.year,
                "month": parsed_date.month,
                "currencyCode": search.currency,
                "monthsRange": _MONTHS_RANGE,
                "flightType": _FLIGHT_TYPE_ONE_WAY,
            },
            timeout_ms=timeout_ms,
            token=token,
        )
        return payload if isinstance(payload, list) else []

    def _post_json(self, url: str, *, json_body: dict, timeout_ms: int, token: str | None = None):
        time.sleep(random.uniform(0.1, 0.4))
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://tickets.vueling.com",
            "Referer": "https://tickets.vueling.com/",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self._session.post(url, json=json_body, timeout=max(2.0, timeout_ms / 1000), headers=headers)
        response.raise_for_status()
        return response.json()

    def _extract_flights(self, payload: list, search: _VuelingSearch) -> list[ProviderFlight]:
        flights: list[ProviderFlight] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            flight = self._flight_from_item(item, search)
            if flight is not None:
                flights.append(flight)
        return flights

    def _flight_from_item(self, item: dict, search: _VuelingSearch) -> ProviderFlight | None:
        if item.get("departureStation", "").upper() != search.origin:
            return None
        if item.get("arrivalStation", "").upper() != search.destination:
            return None
        if item.get("isAvailableDay") is False or item.get("isInvalidPrice") is True:
            return None

        departure_raw = str(item.get("departureDate") or "")
        if self._to_iso_date(departure_raw) != search.travel_date:
            return None
        amount = self._positive_float(item.get("price"))
        if amount is None:
            return None

        return ProviderFlight(
            price=amount,
            currency=str(item.get("currency") or search.currency).upper(),
            departure_time_local=self._to_time(departure_raw),
            captured_at=utc_now_naive(),
            source="vueling-public-availability",
            deeplink_url=self._build_deeplink(search),
        )

    def _build_deeplink(self, search: _VuelingSearch) -> str:
        params = {
            "o": search.origin,
            "d": search.destination,
            "dd": search.travel_date,
            "rd": "",
            "adt": "1",
            "chd": "0",
            "inf": "0",
            "extraseat": "0",
            "c": "en-GB",
            "cur": search.currency,
            "dt": "",
        }
        return f"{_DEFAULT_BOOKING_URL}?{urlencode(params)}"

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

    def _positive_float(self, value) -> float | None:
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return None
        return amount if amount > 0.0 else None
