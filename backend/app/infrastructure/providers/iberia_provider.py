from __future__ import annotations

import os
import random
import time
from typing import Final
import xml.etree.ElementTree as ET

try:
    from curl_cffi import requests
    from curl_cffi.requests.errors import RequestsError
except ImportError:
    import requests
    from requests.exceptions import RequestException as RequestsError
from requests.adapters import HTTPAdapter

from app.domain.entities import ProviderFetchResult, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider
from app.infrastructure.providers.iberia_ndc_parser import IberiaAirShoppingQuery, parse_air_shopping_flights

_DEFAULT_BOOKING_URL: Final = "https://www.iberia.com"
_DEFAULT_ENDPOINT_PATH: Final = "/AirShopping"
_DEFAULT_API_KEY_HEADER: Final = "apikey"
_PROVIDER_POOL_SIZE: Final = 32

class IberiaProvider(FlightProvider):
    provider_id = "iberia"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        seller_id: str | None = None,
    ) -> None:
        self.api_key = (api_key or os.getenv("IBERIA_NDC_API_KEY", "")).strip()
        self.base_url = (base_url or os.getenv("IBERIA_NDC_BASE_URL", "")).strip().rstrip("/")
        self.endpoint_path = os.getenv("IBERIA_NDC_AIRSHOPPING_PATH", _DEFAULT_ENDPOINT_PATH).strip()
        self.api_key_header = os.getenv("IBERIA_NDC_API_KEY_HEADER", _DEFAULT_API_KEY_HEADER).strip()
        self.seller_id = (seller_id or os.getenv("IBERIA_NDC_SELLER_ID", "viru-tracker")).strip()
        self.booking_base_url = os.getenv("IBERIA_BOOKING_BASE_URL", _DEFAULT_BOOKING_URL).strip().rstrip("/")
        try:
            self._session = requests.Session(impersonate="chrome110")
        except TypeError:
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)

    def is_enabled(self) -> bool:
        return bool(self.api_key and self.base_url and self.api_key_header)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        if not self.is_enabled():
            raise ProviderSourceFetchError(
                warning_codes=["iberia_not_configured"],
                message="Iberia NDC provider is not configured",
                provider_id=self.provider_id,
                severity="warning",
            )

        search = IberiaAirShoppingQuery(
            origin=origin.upper().strip(),
            destination=destination.upper().strip(),
            travel_date=travel_date,
            currency=currency.upper().strip(),
        )
        try:
            payload = self._fetch_air_shopping(search, timeout_ms=timeout_ms)
        except (RequestsError, ET.ParseError) as exc:
            raise ProviderSourceFetchError(
                warning_codes=["iberia_provider_unavailable_total", "provider_total_outage"],
                message=f"Iberia NDC provider unavailable for {search.origin}->{search.destination} on {search.travel_date}",
                provider_id=self.provider_id,
                severity="error",
            ) from exc

        flights = parse_air_shopping_flights(payload, search, booking_base_url=self.booking_base_url)
        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(code="provider_empty_result", provider=self.provider_id, severity="info")
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_air_shopping(self, search: IberiaAirShoppingQuery, *, timeout_ms: int) -> ET.Element:
        time.sleep(random.uniform(0.1, 0.4))
        response = self._session.post(
            self._air_shopping_url(),
            data=self._build_air_shopping_request(search),
            timeout=max(2.0, timeout_ms / 1000),
            headers={
                self.api_key_header: self.api_key,
                "Accept": "application/xml, text/xml",
                "Content-Type": "application/xml",
                "User-Agent": "ViruTracker/1.0",
            },
        )
        response.raise_for_status()
        return ET.fromstring(response.text)

    def _air_shopping_url(self) -> str:
        endpoint_path = self.endpoint_path if self.endpoint_path.startswith("/") else f"/{self.endpoint_path}"
        return f"{self.base_url}{endpoint_path}"

    def _build_air_shopping_request(self, search: IberiaAirShoppingQuery) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<AirShoppingRQ xmlns="http://www.iata.org/IATA/EDIST/2017.2" Version="17.2">
  <Document>
    <Name>Viru Tracker</Name>
  </Document>
  <Party>
    <Sender>
      <TravelAgencySender>
        <Name>{self.seller_id}</Name>
      </TravelAgencySender>
    </Sender>
  </Party>
  <CoreQuery>
    <OriginDestinations>
      <OriginDestination>
        <Departure>
          <AirportCode>{search.origin}</AirportCode>
          <Date>{search.travel_date}</Date>
        </Departure>
        <Arrival>
          <AirportCode>{search.destination}</AirportCode>
        </Arrival>
      </OriginDestination>
    </OriginDestinations>
  </CoreQuery>
  <DataLists>
    <PassengerList>
      <Passenger PassengerID="PAX1">
        <PTC>ADT</PTC>
      </Passenger>
    </PassengerList>
  </DataLists>
  <Preference>
    <CurrencyPreferences>
      <Currency>{search.currency}</Currency>
    </CurrencyPreferences>
  </Preference>
</AirShoppingRQ>"""
