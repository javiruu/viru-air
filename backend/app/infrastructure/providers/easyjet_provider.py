from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
import random
import time
from typing import Final

try:
    from curl_cffi import requests
    from curl_cffi.requests.errors import RequestsError
except ImportError:
    import requests
    from requests.exceptions import RequestException as RequestsError
from requests.adapters import HTTPAdapter

from app.domain.entities import ProviderFetchResult, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider
from app.infrastructure.providers.easyjet_flight_connections import (
    EasyJetFlightConnectionsSearch,
    build_flight_connections_params,
    extract_flight_connections_flights,
)
from app.infrastructure.providers.easyjet_public_availability import (
    EasyJetPublicAvailabilitySearch,
    JsonValue,
    build_public_availability_params,
    extract_public_availability_flights,
)

_DEFAULT_BASE_URL: Final = "https://www.easyjet.com"
_DEFAULT_FLIGHT_CONNECTIONS_URL: Final = "https://flightconnections.easyjet.com"
_DEFAULT_LANGUAGE_CODE: Final = "EN"
_DEFAULT_RESIDENCY: Final = "ES"
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
        self.flight_connections_url = os.getenv(
            "EASYJET_FLIGHT_CONNECTIONS_URL", _DEFAULT_FLIGHT_CONNECTIONS_URL
        ).strip().rstrip("/")
        self.flight_connections_bypass_secret = (
            os.getenv("EASYJET_FLIGHT_CONNECTIONS_BYPASS_SECRET")
            or os.getenv("DATADOME_BYPASS_SECRET", "")
        ).strip()
        self.language_code = (
            language_code or os.getenv("EASYJET_LANGUAGE_CODE", _DEFAULT_LANGUAGE_CODE)
        ).strip().upper()
        self.residency = os.getenv("EASYJET_RESIDENCY", _DEFAULT_RESIDENCY).strip().upper()
        try:
            self._session = requests.Session(impersonate="chrome110")
        except TypeError:
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)

    def is_enabled(self) -> bool:
        return bool(self.base_url and self.flight_connections_url and self.language_code and self.residency)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        search = _EasyJetSearch(
            origin=origin.upper().strip(),
            destination=destination.upper().strip(),
            travel_date=travel_date,
            currency=currency.upper().strip(),
        )
        source_error: Exception | None = None
        try:
            payload = self._fetch_public_availability(search, timeout_ms=timeout_ms)
            flights = extract_public_availability_flights(payload, self._to_public_availability_search(search))
        except (RequestsError, ValueError, ProviderSourceFetchError) as exc:
            source_error = exc
            flights = []

        if not flights:
            try:
                connections_payload = self._fetch_flight_connections(search, timeout_ms=timeout_ms)
                flights = extract_flight_connections_flights(
                    connections_payload, self._to_flight_connections_search(search)
                )
            except (RequestsError, ValueError, ProviderSourceFetchError) as exc:
                source_error = exc

        if source_error is not None and not flights:
            raise ProviderSourceFetchError(
                warning_codes=["easyjet_provider_unavailable_total", "provider_total_outage"],
                message=f"easyJet provider unavailable for {search.origin}->{search.destination} on {search.travel_date}",
                provider_id=self.provider_id,
                severity="error",
            ) from source_error

        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(code="provider_empty_result", provider=self.provider_id, severity="info")
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_public_availability(self, search: _EasyJetSearch, *, timeout_ms: int) -> Mapping[str, JsonValue]:
        response = self._session.get(
            f"{self.base_url}/ejavailability/api/v16/availability/query",
            params=build_public_availability_params(self._to_public_availability_search(search)),
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

    def _to_public_availability_search(self, search: _EasyJetSearch) -> EasyJetPublicAvailabilitySearch:
        return EasyJetPublicAvailabilitySearch(
            origin=search.origin,
            destination=search.destination,
            travel_date=search.travel_date,
            currency=search.currency,
            language=self.language_code,
            base_url=self.base_url,
        )

    def _fetch_flight_connections(self, search: _EasyJetSearch, *, timeout_ms: int) -> Mapping[str, JsonValue]:
        flight_connections_search = self._to_flight_connections_search(search)
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Origin": self.flight_connections_url,
            "Referer": f"{self.flight_connections_url}/{self.language_code.lower()}/search",
        }
        if self.flight_connections_bypass_secret:
            headers["X-Dohop-Bypass"] = self.flight_connections_bypass_secret
        response = self._session.get(
            f"{self.flight_connections_url}/api/graphql",
            params=build_flight_connections_params(flight_connections_search),
            timeout=max(2.0, timeout_ms / 1000),
            headers=headers,
        )
        time.sleep(random.uniform(0.1, 0.4))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _to_flight_connections_search(self, search: _EasyJetSearch) -> EasyJetFlightConnectionsSearch:
        return EasyJetFlightConnectionsSearch(
            origin=search.origin,
            destination=search.destination,
            travel_date=search.travel_date,
            currency=search.currency,
            language=self.language_code,
            residency=self.residency,
            base_url=self.flight_connections_url,
        )
