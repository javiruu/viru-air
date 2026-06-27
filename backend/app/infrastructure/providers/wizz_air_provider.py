from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider

_PROVIDER_POOL_SIZE = 32


class WizzAirProvider(FlightProvider):
    provider_id = "wizzair"

    def __init__(
        self,
        *,
        base_url: str = "https://be.wizzair.com/29.4.0/Api",
        day_interval: int | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("WIZZAIR_BASE_URL", "https://be.wizzair.com/29.4.0/Api")).rstrip("/")
        self.day_interval = max(3, int(day_interval or os.getenv("WIZZAIR_FARECHART_DAY_INTERVAL", "9")))
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

        try:
            body = self._fetch_farechart(origin, destination, travel_date, timeout_ms=timeout_ms)
        except requests.RequestException as exc:
            raise ProviderSourceFetchError(
                warning_codes=["wizzair_provider_unavailable_total", "provider_total_outage"],
                message=f"Wizz Air provider unavailable for {origin}->{destination} on {travel_date}",
                provider_id=self.provider_id,
                severity="error",
            ) from exc

        flights = self._extract_matching_flights(body, travel_date=travel_date, fallback_currency=currency)
        warnings_structured: list[ProviderWarning] = []
        if not flights:
            warnings_structured.append(
                ProviderWarning(
                    code="provider_empty_result",
                    provider=self.provider_id,
                    severity="info",
                )
            )
        return ProviderFetchResult(flights=flights, warnings=[], warnings_structured=warnings_structured)

    def _fetch_farechart(self, origin: str, destination: str, travel_date: str, *, timeout_ms: int) -> dict[str, Any]:
        url = f"{self.base_url}/asset/farechart"
        response = self._session.post(
            url,
            json={
                "isRescueFare": False,
                "adultCount": 1,
                "childCount": 0,
                "dayInterval": self.day_interval,
                "wdc": False,
                "isFlightChange": False,
                "flightList": [
                    {
                        "departureStation": origin,
                        "arrivalStation": destination,
                        "date": f"{travel_date}T00:00:00",
                    }
                ],
            },
            timeout=max(2.0, timeout_ms / 1000),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://www.wizzair.com",
                "Referer": "https://www.wizzair.com/",
            },
        )
        response.raise_for_status()
        return response.json()

    def _extract_matching_flights(
        self,
        payload: dict[str, Any],
        *,
        travel_date: str,
        fallback_currency: str,
    ) -> list[ProviderFlight]:
        flights: list[ProviderFlight] = []
        for item in payload.get("outboundFlights") or []:
            item_date = self._to_iso_date(item.get("date"))
            if item_date != travel_date:
                continue

            price = item.get("price") or {}
            amount = price.get("exchangedAmount")
            currency = price.get("exchangedCurrencyCode")
            if amount is None:
                amount = price.get("amount")
            if currency is None:
                currency = price.get("currencyCode") or fallback_currency
            if amount is None:
                continue

            try:
                normalized_amount = float(amount)
            except (TypeError, ValueError):
                continue

            flights.append(
                ProviderFlight(
                    price=normalized_amount,
                    currency=str(currency).upper(),
                    departure_time_local=None,
                    captured_at=utc_now_naive(),
                    source="wizzair-farechart",
                )
            )
        return flights

    def _to_iso_date(self, value: Any) -> str | None:
        if not value:
            return None
        if isinstance(value, str) and len(value) >= 10:
            raw = value[:10]
            try:
                return datetime.fromisoformat(raw).date().isoformat()
            except ValueError:
                return raw
        return None
