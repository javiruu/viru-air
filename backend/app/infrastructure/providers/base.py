from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities import ProviderFetchResult


class FlightProvider(ABC):
    provider_id: str

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        raise NotImplementedError
