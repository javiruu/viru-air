from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError, ProviderWarning
from app.infrastructure.providers.base import FlightProvider
from app.infrastructure.providers.registry import FlightProviderRegistry


logger = logging.getLogger(__name__)


class FlightSearchOrchestrator:
    def __init__(self, providers: list[FlightProvider] | None = None) -> None:
        self._providers = providers if providers is not None else FlightProviderRegistry().resolve_enabled_providers()

    def provider_ids(self) -> list[str]:
        return [provider.provider_id for provider in self._providers]

    def get_flights(
        self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"
    ) -> ProviderFetchResult:
        if not self._providers:
            return ProviderFetchResult(flights=[], warnings=[], warnings_structured=[])

        flights: list[ProviderFlight] = []
        warnings: list[str] = []
        warnings_structured: list[ProviderWarning] = []

        # Run all providers in parallel so that a slow provider (e.g. Wizz Air
        # with per-route locking) doesn't block faster providers (e.g. Ryanair).
        # Each provider gets its own fair share of the timeout.
        # Fair per-provider timeout: divide total, but ensure each provider
        # gets at least 3s so slower APIs (Wizz Air farechart) don't false-timeout.
        provider_timeout = max(3000, timeout_ms // len(self._providers))
        max_workers = min(len(self._providers), 4)

        logger.info(
            "orchestrator_parallel_start route=%s->%s date=%s providers=%s timeout_per_provider=%s",
            origin, destination, travel_date,
            [p.provider_id for p in self._providers],
            provider_timeout,
        )
        t_start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map: dict[Any, FlightProvider] = {}
            for provider in self._providers:
                future = executor.submit(
                    provider.get_flights,
                    origin=origin,
                    destination=destination,
                    travel_date=travel_date,
                    timeout_ms=provider_timeout,
                    currency=currency,
                )
                future_map[future] = provider

            for future in as_completed(future_map):
                provider = future_map[future]
                try:
                    result = future.result()
                    flights.extend(result.flights)
                    warnings.extend(result.warnings)
                    for item in result.warnings_structured or []:
                        warnings_structured.append(item)
                    logger.debug(
                        "orchestrator_provider_done provider=%s route=%s->%s flights=%s",
                        provider.provider_id, origin, destination, len(result.flights),
                    )
                except ProviderSourceFetchError as exc:
                    warnings.extend(exc.warning_codes)
                    warnings_structured.extend(
                        [
                            ProviderWarning(
                                code=code,
                                provider=exc.provider_id or provider.provider_id,
                                severity=exc.severity,
                                meta=exc.meta,
                            )
                            for code in exc.warning_codes
                        ]
                    )
                    logger.warning(
                        "orchestrator_provider_error provider=%s route=%s->%s codes=%s",
                        provider.provider_id, origin, destination, exc.warning_codes,
                    )
                except Exception as exc:
                    logger.warning(
                        "orchestrator_provider_unexpected provider=%s route=%s->%s error_type=%s",
                        provider.provider_id,
                        origin,
                        destination,
                        type(exc).__name__,
                        exc_info=True,
                    )
                    warnings.append("provider_error_partial")
                    warnings_structured.append(
                        ProviderWarning(
                            code="provider_error_partial",
                            provider=provider.provider_id,
                            severity="warning",
                            meta={"error_type": type(exc).__name__},
                        )
                    )

        elapsed = int((time.perf_counter() - t_start) * 1000)
        logger.info(
            "orchestrator_parallel_done route=%s->%s date=%s total_elapsed_ms=%s total_flights=%s",
            origin, destination, travel_date, elapsed, len(flights),
        )

        return ProviderFetchResult(
            flights=self._dedupe_flights(flights),
            warnings=self._dedupe_warning_codes(warnings),
            warnings_structured=self._dedupe_structured_warnings(warnings_structured),
        )

    def _dedupe_flights(self, flights: list[ProviderFlight]) -> list[ProviderFlight]:
        seen: set[tuple[str, float, str, str]] = set()
        unique: list[ProviderFlight] = []
        for flight in flights:
            key = (flight.departure_time_local or "", flight.price, flight.currency, flight.source)
            if key in seen:
                continue
            seen.add(key)
            unique.append(flight)
        return unique

    def _dedupe_warning_codes(self, warnings: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for warning in warnings:
            if warning in seen:
                continue
            seen.add(warning)
            out.append(warning)
        return out

    def _dedupe_structured_warnings(self, warnings: list[ProviderWarning]) -> list[ProviderWarning]:
        seen: set[tuple[str, str, str, tuple[tuple[str, str], ...]]] = set()
        out: list[ProviderWarning] = []
        for warning in warnings:
            normalized_meta = tuple(sorted((warning.meta or {}).items()))
            key = (warning.code, warning.provider, warning.severity, normalized_meta)
            if key in seen:
                continue
            seen.add(key)
            out.append(warning)
        return out
