from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from typing import Literal

from app.infrastructure.providers.operational_flight_provider import (
    OperationalFetchOutcome,
    OperationalFlightIdentity,
    OperationalFlightObservation,
    OperationalFlightProvider,
    OperationalNotConfigured,
    OperationalObserved,
    OperationalRateLimited,
    OperationalUnavailable,
)
from app.services.live_flight_provider_quota import ProviderBudgetPolicy, ProviderQuotaLedger


ProviderCapability = Literal["status_schedule", "position"]


@dataclass(frozen=True, slots=True)
class OperationalProviderRegistration:
    name: str
    provider: OperationalFlightProvider
    capabilities: frozenset[ProviderCapability]
    budget: ProviderBudgetPolicy


class QuotaAwareOperationalFlightProvider:
    def __init__(
        self,
        registrations: list[OperationalProviderRegistration],
        ledger: ProviderQuotaLedger,
    ) -> None:
        self.registrations = registrations
        self._ledger = ledger

    def fetch(
        self,
        identity: OperationalFlightIdentity,
        now: dt.datetime,
    ) -> OperationalFetchOutcome:
        status_observation: OperationalFlightObservation | None = None
        last_outcome: OperationalFetchOutcome = OperationalNotConfigured()
        called: set[str] = set()
        for registration in self.registrations:
            if "status_schedule" not in registration.capabilities:
                continue
            outcome = self._fetch_registration(registration, identity, now)
            called.add(registration.name)
            last_outcome = outcome
            if isinstance(outcome, OperationalObserved):
                status_observation = outcome.observation
                break
        if status_observation is None:
            return last_outcome
        if _has_position(status_observation):
            return OperationalObserved(status_observation)
        enriched_identity = replace(
            identity,
            callsign=status_observation.callsign or identity.callsign,
            icao24=status_observation.icao24 or identity.icao24,
        )
        for registration in self.registrations:
            if "position" not in registration.capabilities or registration.name in called:
                continue
            outcome = self._fetch_registration(registration, enriched_identity, now)
            if isinstance(outcome, OperationalObserved) and _has_position(outcome.observation):
                return OperationalObserved(_merge_position(status_observation, outcome.observation))
        return OperationalObserved(status_observation)

    def _fetch_registration(
        self,
        registration: OperationalProviderRegistration,
        identity: OperationalFlightIdentity,
        now: dt.datetime,
    ) -> OperationalFetchOutcome:
        if not self._ledger.reserve(registration.budget, now):
            return OperationalRateLimited(retry_after_seconds=300)
        outcome = registration.provider.fetch(identity, now)
        if isinstance(outcome, OperationalRateLimited):
            self._ledger.block(
                registration.name,
                now,
                outcome.retry_after_seconds,
                "rate_limited",
            )
        elif isinstance(outcome, OperationalUnavailable) and outcome.reason == "payment_required":
            self._ledger.block(registration.name, now, 31 * 86_400, "payment_required")
        return outcome


def _has_position(observation: OperationalFlightObservation) -> bool:
    return observation.latitude is not None and observation.longitude is not None


def _merge_position(
    primary: OperationalFlightObservation,
    position: OperationalFlightObservation,
) -> OperationalFlightObservation:
    return replace(
        primary,
        provider=f"{primary.provider}+{position.provider}",
        provider_flight_id=primary.provider_flight_id or position.provider_flight_id,
        callsign=primary.callsign or position.callsign,
        icao24=primary.icao24 or position.icao24,
        observed_at=max(primary.observed_at, position.observed_at),
        expires_at=min(primary.expires_at, position.expires_at),
        latitude=position.latitude,
        longitude=position.longitude,
        altitude_m=position.altitude_m,
        speed_mps=position.speed_mps,
        heading_deg=position.heading_deg,
        on_ground=position.on_ground,
        registration=primary.registration or position.registration,
        aircraft_iata=primary.aircraft_iata or position.aircraft_iata,
        aircraft_icao=primary.aircraft_icao or position.aircraft_icao,
        data_quality="observed",
    )
