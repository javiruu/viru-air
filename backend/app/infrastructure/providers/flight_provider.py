from __future__ import annotations

from app.domain.entities import ProviderFetchResult
from app.infrastructure.providers.orchestrator import FlightSearchOrchestrator


class MultiSourceFlightProvider:
    def __init__(self) -> None:
        self._orchestrator = FlightSearchOrchestrator()

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        return self._orchestrator.get_flights(
            origin=origin,
            destination=destination,
            travel_date=travel_date,
            timeout_ms=timeout_ms,
            currency=currency,
        )

    def provider_ids(self) -> list[str]:
        return self._orchestrator.provider_ids()
