from __future__ import annotations

from collections.abc import Mapping
import os
import random
import time
from typing import Any, Final

try:
    from curl_cffi import requests
    from curl_cffi.requests.errors import RequestsError
except ImportError:
    import requests
    from requests.exceptions import RequestException as RequestsError
from requests.adapters import HTTPAdapter

from app.domain.entities import ProviderFetchResult, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider
from app.infrastructure.providers.iberia_public_availability import (
    IberiaPublicAvailabilitySearch,
    build_public_availability_request,
    extract_public_availability_flights,
)

_DEFAULT_BASE_URL: Final = "https://www.iberia.com"
_DEFAULT_API_BASE_URL: Final = "https://ibisservices.iberia.com/api"
_DEFAULT_AVAILABILITY_PATH: Final = "/sse-avm/rs/v2/availability"
_DEFAULT_AUTHORIZATION: Final = "Basic aWJlcmlhX3dlYjo5ZGM4NzZjYi0xMDVkLTQ4MWItODM4Yy01NGUyNGQ3NDEwYzk="
_DEFAULT_MARKET: Final = "ES"
_DEFAULT_LANGUAGE: Final = "es"
_PROVIDER_POOL_SIZE: Final = 32


class IberiaProvider(FlightProvider):
    provider_id = "iberia"

    def __init__(
        self,
        *,
        api_base_url: str | None = None,
        base_url: str | None = None,
        authorization: str | None = None,
        market: str | None = None,
        language: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("IBERIA_BASE_URL", _DEFAULT_BASE_URL)).strip().rstrip("/")
        self.api_base_url = (
            api_base_url or os.getenv("IBERIA_API_BASE_URL", _DEFAULT_API_BASE_URL)
        ).strip().rstrip("/")
        self.availability_path = os.getenv("IBERIA_AVAILABILITY_PATH", _DEFAULT_AVAILABILITY_PATH).strip()
        self.authorization = (
            authorization or os.getenv("IBERIA_PUBLIC_AUTHORIZATION", _DEFAULT_AUTHORIZATION)
        ).strip()
        self.market = (market or os.getenv("IBERIA_MARKET", _DEFAULT_MARKET)).strip().upper()
        self.language = (language or os.getenv("IBERIA_LANGUAGE", _DEFAULT_LANGUAGE)).strip().lower()
        try:
            self._session = requests.Session(impersonate="chrome110")
        except TypeError:
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)

    def is_enabled(self) -> bool:
        return bool(self.base_url and self.api_base_url and self.authorization and self.market and self.language)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        search = self._build_search(origin, destination, travel_date, currency)
        try:
            payload = self._fetch_public_availability(search, timeout_ms=timeout_ms)
        except (RequestsError, ValueError, ProviderSourceFetchError) as exc:
            raise ProviderSourceFetchError(
                warning_codes=["iberia_provider_unavailable_total", "provider_total_outage"],
                message=f"Iberia public provider unavailable for {search.origin}->{search.destination} on {search.travel_date}",
                provider_id=self.provider_id,
                severity="error",
            ) from exc

        flights = extract_public_availability_flights(payload, search)
        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(code="provider_empty_result", provider=self.provider_id, severity="info")
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_public_availability(
        self, search: IberiaPublicAvailabilitySearch, *, timeout_ms: int
    ) -> Mapping[str, Any]:
        time.sleep(random.uniform(0.1, 0.4))
        response = self._session.post(
            self._availability_url(),
            json=build_public_availability_request(search),
            timeout=max(2.0, timeout_ms / 1000),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/flights/",
                "Authorization": self.authorization,
                "language": self.language,
                "market": self.market,
            },
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderSourceFetchError(
                warning_codes=["iberia_provider_unavailable_total", "provider_total_outage"],
                message="Iberia public provider returned a non-JSON response",
                provider_id=self.provider_id,
                severity="error",
                meta={"reason": "invalid_json"},
            ) from exc
        return payload if isinstance(payload, dict) else {}

    def _availability_url(self) -> str:
        path = self.availability_path if self.availability_path.startswith("/") else f"/{self.availability_path}"
        return f"{self.api_base_url}{path}"

    def _build_search(
        self, origin: str, destination: str, travel_date: str, currency: str
    ) -> IberiaPublicAvailabilitySearch:
        return IberiaPublicAvailabilitySearch(
            origin=origin.upper().strip(),
            destination=destination.upper().strip(),
            travel_date=travel_date,
            currency=currency.upper().strip(),
            market=self.market,
            language=self.language,
            base_url=self.base_url,
        )
