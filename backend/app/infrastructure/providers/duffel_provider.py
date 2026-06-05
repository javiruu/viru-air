from __future__ import annotations

from datetime import datetime
import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider

_PROVIDER_POOL_SIZE = 32


class DuffelProvider(FlightProvider):
    provider_id = "duffel"

    def __init__(self, api_key: str | None = None, *, base_url: str = "https://api.duffel.com/air") -> None:
        self.api_key = (api_key or os.getenv("DUFFEL_API_KEY", "")).strip()
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=_PROVIDER_POOL_SIZE, pool_maxsize=_PROVIDER_POOL_SIZE)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        if not self.is_enabled():
            raise ProviderSourceFetchError(
                warning_codes=["duffel_not_configured"],
                message="Duffel provider is not configured",
                provider_id=self.provider_id,
                severity="warning",
            )

        origin = origin.upper().strip()
        destination = destination.upper().strip()
        payload = {
            "data": {
                "slices": [{"origin": origin, "destination": destination, "departure_date": travel_date}],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy",
            }
        }
        url = f"{self.base_url}/offer_requests"
        try:
            resp = self._session.post(
                url,
                params={
                    "return_offers": "true",
                    "supplier_timeout": str(max(2000, min(timeout_ms, 60000))),
                    "view": "offers",
                },
                json=payload,
                timeout=max(2.0, timeout_ms / 1000),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Duffel-Version": "v2",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            body = resp.json()
        except requests.RequestException as exc:
            raise ProviderSourceFetchError(
                warning_codes=["duffel_provider_unavailable_total", "provider_total_outage"],
                message=f"Duffel provider unavailable for {origin}->{destination} on {travel_date}",
                provider_id=self.provider_id,
                severity="error",
            ) from exc

        offers = ((body.get("data") or {}).get("offers") or [])
        flights: list[ProviderFlight] = []
        for offer in offers:
            flight = self._to_flight(offer, fallback_currency=currency)
            if flight is not None:
                flights.append(flight)

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

    def _to_flight(self, offer: dict[str, Any], *, fallback_currency: str) -> ProviderFlight | None:
        total_amount = offer.get("total_amount")
        if total_amount is None:
            return None
        try:
            price = float(total_amount)
        except (TypeError, ValueError):
            return None

        currency = (offer.get("total_currency") or fallback_currency or "EUR").upper()
        departure_raw = self._extract_departure_datetime(offer)
        departure_time_local = self._to_time(departure_raw)
        return ProviderFlight(
            price=price,
            currency=currency,
            departure_time_local=departure_time_local,
            captured_at=utc_now_naive(),
            source="duffel-offers",
        )

    def _extract_departure_datetime(self, offer: dict[str, Any]) -> str | None:
        slices = offer.get("slices") or []
        if not slices:
            return None
        segments = (slices[0] or {}).get("segments") or []
        if not segments:
            return None
        return (segments[0] or {}).get("departing_at")

    def _to_time(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.strftime("%H:%M")
        except ValueError:
            return None
