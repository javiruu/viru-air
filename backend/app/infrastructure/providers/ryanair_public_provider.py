from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from app.core.time import utc_now_naive

import time
import random
import requests as std_requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderPrice, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider
from app.services.flight_number_enrichment import normalize_explicit_flight_number

curl_requests: Any | None
CurlRequestsError: type[Exception]
try:
    from curl_cffi import requests as imported_curl_requests
    from curl_cffi.requests.errors import RequestsError as imported_curl_requests_error
except ImportError:
    curl_requests = None
    CurlRequestsError = RequestException
else:
    curl_requests = imported_curl_requests
    CurlRequestsError = imported_curl_requests_error

# Keep the historical module-level transport seam: when curl_cffi is present,
# callers can still exercise its impersonated session and its fallback path.
requests: Any = curl_requests if curl_requests is not None else std_requests
RequestsError = CurlRequestsError

_PROVIDER_POOL_SIZE = 32


class RyanairPublicProvider(FlightProvider):
    provider_id = "ryanair"

    def __init__(self) -> None:
        self._session: Any
        try:
            if curl_requests is None:
                raise TypeError("curl_cffi_unavailable")
            self._session = curl_requests.Session(impersonate="chrome110")
        except TypeError:
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)

    def is_enabled(self) -> bool:
        return True

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        origin = origin.upper().strip()
        destination = destination.upper().strip()
        warnings: list[str] = []
        availability_error = False
        fares_error = False

        try:
            availability = self._fetch_availability(origin, destination, travel_date, timeout_ms=timeout_ms, currency=currency)
        except (CurlRequestsError, RequestException, ValueError):
            availability = []
            availability_error = True
            warnings.append("ryanair_availability_failed_partial")

        try:
            fares = self._fetch_one_way_fares(origin, destination, travel_date, timeout_ms=timeout_ms, currency=currency)
        except (CurlRequestsError, RequestException, ValueError):
            fares = []
            fares_error = True
            warnings.append("ryanair_fares_failed_partial")

        flights = self._dedupe_flights(availability + fares)
        warnings_structured = [
            ProviderWarning(
                code=self._to_canonical_warning(code),
                provider=self.provider_id,
                severity="warning",
            )
            for code in warnings
        ]
        if flights:
            return ProviderFetchResult(flights=flights, warnings=warnings, warnings_structured=warnings_structured)

        if availability_error and fares_error:
            raise ProviderSourceFetchError(
                warning_codes=[
                    "ryanair_availability_failed",
                    "ryanair_fares_failed",
                    "ryanair_provider_unavailable_total",
                    "provider_total_outage",
                ],
                message=f"Ryanair provider unavailable for {origin}->{destination} on {travel_date}",
                provider_id=self.provider_id,
                severity="error",
            )

        return ProviderFetchResult(flights=[], warnings=warnings, warnings_structured=warnings_structured)

    def _to_canonical_warning(self, warning_code: str) -> str:
        if warning_code.endswith("_failed_partial") or warning_code.endswith("_unavailable_partial"):
            return "provider_error_partial"
        return warning_code

    def get_cheapest_price(self, origin: str, destination: str, travel_date: str, currency: str = "EUR") -> ProviderPrice | None:
        result = self.get_flights(origin, destination, travel_date, currency=currency)
        if not result.flights:
            return None
        best = min(result.flights, key=lambda f: f.price)
        return ProviderPrice(
            price=best.price,
            currency=best.currency,
            captured_at=best.captured_at,
            source=best.source,
        )

    def _fetch_one_way_fares(
        self, origin: str, destination: str, travel_date: str, *, timeout_ms: int, currency: str
    ) -> list[ProviderFlight]:
        url = (
            "https://www.ryanair.com/api/farfnd/3/oneWayFares"
            f"?departureAirportIataCode={origin}"
            f"&arrivalAirportIataCode={destination}"
            f"&outboundDepartureDateFrom={travel_date}"
            f"&outboundDepartureDateTo={travel_date}"
            f"&currency={currency}"
        )
        data = self._get_json(url, timeout_ms=timeout_ms)
        fares = data.get("fares") or []
        flights: list[ProviderFlight] = []
        deeplink_url = self._build_deeplink(origin, destination, travel_date, currency)
        for fare in fares:
            outbound = fare.get("outbound") or {}
            price = (outbound.get("price") or {}).get("value")
            dep = outbound.get("departureDate") or outbound.get("departureDateTime")
            if price is None:
                continue
            flights.append(
                ProviderFlight(
                    price=float(price),
                    currency=currency,
                    departure_time_local=self._to_time(dep),
                    captured_at=utc_now_naive(),
                    source="ryanair-public-fares",
                    provider=self.provider_id,
                    origin_iata=origin,
                    destination_iata=destination,
                    travel_date=travel_date,
                    deeplink_url=deeplink_url,
                    carrier_code="FR",
                    flight_number=self._normalize_flight_number(outbound.get("flightNumber")),
                )
            )
        return flights

    def _fetch_availability(
        self, origin: str, destination: str, travel_date: str, *, timeout_ms: int, currency: str
    ) -> list[ProviderFlight]:
        url = (
            "https://www.ryanair.com/api/booking/v4/es-es/availability"
            f"?Origin={origin}"
            f"&Destination={destination}"
            f"&DateOut={travel_date}"
            f"&DateIn="
            f"&FlexDaysOut=0"
            f"&FlexDaysIn=0"
            f"&RoundTrip=false"
            f"&ToUs=AGREED"
            f"&IncludeConnectingFlights=false"
            f"&Currency={currency}"
        )
        data = self._get_json(url, timeout_ms=timeout_ms)
        trips = data.get("trips") or []
        flights: list[ProviderFlight] = []
        deeplink_url = self._build_deeplink(origin, destination, travel_date, currency)
        for trip in trips:
            for flight in trip.get("flights") or []:
                regular = flight.get("regularFare") or {}
                fares = regular.get("fares") or flight.get("fares") or []
                amounts = [fare.get("amount") for fare in fares if fare.get("amount") is not None]
                if not amounts:
                    continue
                amount = min(amounts)
                times = flight.get("time") or flight.get("timeUTC") or []
                departure = times[0] if times else flight.get("departureTime")
                flights.append(
                    ProviderFlight(
                        price=float(amount),
                        currency=currency,
                        departure_time_local=self._to_time(departure),
                        captured_at=utc_now_naive(),
                        source="ryanair-public-availability",
                        provider=self.provider_id,
                        origin_iata=origin,
                        destination_iata=destination,
                        travel_date=travel_date,
                        deeplink_url=deeplink_url,
                        carrier_code="FR",
                        flight_number=self._normalize_flight_number(flight.get("flightNumber")),
                    )
                )
        return flights

    def _dedupe_flights(self, flights: list[ProviderFlight]) -> list[ProviderFlight]:
        seen: set[tuple[str, float, str]] = set()
        unique: list[ProviderFlight] = []
        for flight in flights:
            key = (flight.departure_time_local or "", flight.price, flight.currency)
            if key in seen:
                continue
            seen.add(key)
            unique.append(flight)
        return unique

    def _get_json(self, url: str, *, timeout_ms: int = 12000) -> dict[str, Any]:
        time.sleep(random.uniform(0.1, 0.4))
        resp = self._session.get(
            url,
            timeout=max(1, timeout_ms / 1000),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()

    def _to_time(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.strftime("%H:%M")
        except ValueError:
            return None

    def _normalize_flight_number(self, value: Any) -> str | None:
        return normalize_explicit_flight_number(value, carrier_code="FR")

    def _build_deeplink(self, origin: str, destination: str, travel_date: str, currency: str) -> str:
        params = {
            "adults": "1",
            "teens": "0",
            "children": "0",
            "infants": "0",
            "dateOut": travel_date,
            "dateIn": "",
            "isReturn": "false",
            "originIata": origin,
            "destinationIata": destination,
            "currency": currency,
        }
        return f"https://www.ryanair.com/es-es/trip/flights/select?{urlencode(params)}"

    def debug_payload(self, origin: str, destination: str, travel_date: str, currency: str = "EUR") -> dict[str, Any]:
        result = self.get_flights(origin, destination, travel_date, currency=currency)
        return {
            "origin": origin,
            "destination": destination,
            "travel_date": travel_date,
            "warnings": result.warnings,
            "flights": [asdict(f) for f in result.flights],
        }
