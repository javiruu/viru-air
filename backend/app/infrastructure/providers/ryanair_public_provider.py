from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from app.core.time import utc_now_naive

import requests

from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderPrice, ProviderSourceFetchError


class RyanairPublicProvider:
    def __init__(self, currency: str = "EUR") -> None:
        self.currency = currency
        self._session = requests.Session()

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000
    ) -> ProviderFetchResult:
        origin = origin.upper().strip()
        destination = destination.upper().strip()
        warnings: list[str] = []
        availability_error = False
        fares_error = False

        try:
            availability = self._fetch_availability(origin, destination, travel_date, timeout_ms=timeout_ms)
        except requests.RequestException:
            availability = []
            availability_error = True
            warnings.append("ryanair_availability_failed_partial")

        try:
            fares = self._fetch_one_way_fares(origin, destination, travel_date, timeout_ms=timeout_ms)
        except requests.RequestException:
            fares = []
            fares_error = True
            warnings.append("ryanair_fares_failed_partial")

        flights = self._dedupe_flights(availability + fares)
        if flights:
            return ProviderFetchResult(flights=flights, warnings=warnings)

        if availability_error and fares_error:
            raise ProviderSourceFetchError(
                warning_codes=[
                    "ryanair_availability_failed",
                    "ryanair_fares_failed",
                    "ryanair_provider_unavailable_total",
                ],
                message=f"Ryanair provider unavailable for {origin}->{destination} on {travel_date}",
            )

        return ProviderFetchResult(flights=[], warnings=warnings)

    def get_cheapest_price(self, origin: str, destination: str, travel_date: str) -> ProviderPrice | None:
        result = self.get_flights(origin, destination, travel_date)
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
        self, origin: str, destination: str, travel_date: str, *, timeout_ms: int
    ) -> list[ProviderFlight]:
        url = (
            "https://www.ryanair.com/api/farfnd/3/oneWayFares"
            f"?departureAirportIataCode={origin}"
            f"&arrivalAirportIataCode={destination}"
            f"&outboundDepartureDateFrom={travel_date}"
            f"&outboundDepartureDateTo={travel_date}"
            f"&currency={self.currency}"
        )
        data = self._get_json(url, timeout_ms=timeout_ms)
        fares = data.get("fares") or []
        flights: list[ProviderFlight] = []
        for fare in fares:
            outbound = fare.get("outbound") or {}
            price = (outbound.get("price") or {}).get("value")
            dep = outbound.get("departureDate") or outbound.get("departureDateTime")
            if price is None:
                continue
            flights.append(
                ProviderFlight(
                    price=float(price),
                    currency=self.currency,
                    departure_time_local=self._to_time(dep),
                    captured_at=utc_now_naive(),
                    source="ryanair-public-fares",
                )
            )
        return flights

    def _fetch_availability(
        self, origin: str, destination: str, travel_date: str, *, timeout_ms: int
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
            f"&Currency={self.currency}"
        )
        data = self._get_json(url, timeout_ms=timeout_ms)
        trips = data.get("trips") or []
        flights: list[ProviderFlight] = []
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
                        currency=self.currency,
                        departure_time_local=self._to_time(departure),
                        captured_at=utc_now_naive(),
                        source="ryanair-public-availability",
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

    def debug_payload(self, origin: str, destination: str, travel_date: str) -> dict[str, Any]:
        result = self.get_flights(origin, destination, travel_date)
        return {
            "origin": origin,
            "destination": destination,
            "travel_date": travel_date,
            "warnings": result.warnings,
            "flights": [asdict(f) for f in result.flights],
        }
