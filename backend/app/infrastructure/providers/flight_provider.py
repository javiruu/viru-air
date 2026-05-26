from __future__ import annotations

from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError
from app.infrastructure.providers.duffel_provider import DuffelProvider
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider


class MultiSourceFlightProvider:
    def __init__(self) -> None:
        self._providers = [RyanairPublicProvider()]
        duffel = DuffelProvider()
        if duffel.is_enabled():
            self._providers.append(duffel)

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        flights: list[ProviderFlight] = []
        warnings: list[str] = []

        for provider in self._providers:
            try:
                result = provider.get_flights(
                    origin=origin,
                    destination=destination,
                    travel_date=travel_date,
                    timeout_ms=timeout_ms,
                    currency=currency,
                )
                warnings.extend(result.warnings)
                flights.extend(result.flights)
            except ProviderSourceFetchError as exc:
                warnings.extend(exc.warning_codes)

        return ProviderFetchResult(flights=self._dedupe_flights(flights), warnings=self._dedupe_warnings(warnings))

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

    def _dedupe_warnings(self, warnings: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for warning in warnings:
            if warning in seen:
                continue
            seen.add(warning)
            out.append(warning)
        return out
