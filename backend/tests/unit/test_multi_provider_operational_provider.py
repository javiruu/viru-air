import datetime as dt
from dataclasses import replace

from app.infrastructure.providers.multi_provider_operational_provider import (
    OperationalProviderRegistration,
    QuotaAwareOperationalFlightProvider,
)
from app.infrastructure.providers.operational_flight_provider import (
    OperationalFlightIdentity,
    OperationalFlightObservation,
    OperationalNoCoverage,
    OperationalNotConfigured,
    OperationalObserved,
    OperationalRateLimited,
    OperationalUnavailable,
)
from app.services.live_flight_provider_quota import ProviderBudgetPolicy


NOW = dt.datetime(2026, 7, 22, 8, 45)


def _identity() -> OperationalFlightIdentity:
    return OperationalFlightIdentity(
        flight_instance_fingerprint="flight-instance",
        flight_number="FR9602",
        carrier_code="FR",
        origin_iata="MAD",
        destination_iata="FCO",
        departure_date_local=dt.date(2026, 7, 22),
        scheduled_departure_at=dt.datetime(2026, 7, 22, 8, 30),
        scheduled_arrival_at=dt.datetime(2026, 7, 22, 10, 55),
    )


def _observation(provider: str, *, positioned: bool = False) -> OperationalFlightObservation:
    return OperationalFlightObservation(
        provider=provider,
        provider_flight_id="provider-flight",
        flight_number="FR9602",
        callsign="RYR9602",
        icao24="4ca123",
        status="active",
        status_raw="en-route",
        observed_at=NOW,
        expires_at=NOW + dt.timedelta(seconds=60),
        scheduled_departure_at=dt.datetime(2026, 7, 22, 8, 30),
        estimated_departure_at=dt.datetime(2026, 7, 22, 8, 40),
        actual_departure_at=dt.datetime(2026, 7, 22, 8, 43),
        scheduled_arrival_at=dt.datetime(2026, 7, 22, 10, 55),
        estimated_arrival_at=dt.datetime(2026, 7, 22, 11, 5),
        actual_arrival_at=None,
        departure_terminal="1",
        departure_gate="B12",
        arrival_terminal="3",
        arrival_gate=None,
        departure_delay_minutes=13,
        arrival_delay_minutes=10,
        latitude=41.1 if positioned else None,
        longitude=2.1 if positioned else None,
        altitude_m=10_000 if positioned else None,
        speed_mps=220 if positioned else None,
        heading_deg=85 if positioned else None,
        on_ground=False if positioned else None,
        registration="EI-TEST" if positioned else None,
        aircraft_iata=None,
        aircraft_icao="B738" if positioned else None,
        data_quality="observed" if positioned else "status_only",
    )


class _Provider:
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.identities: list[OperationalFlightIdentity] = []

    def fetch(self, identity: OperationalFlightIdentity, now: dt.datetime):
        self.identities.append(identity)
        return self.outcome


class _Ledger:
    def __init__(self, denied: set[str] | None = None) -> None:
        self.denied = denied or set()
        self.reservations: list[tuple[str, int]] = []
        self.blocks: list[tuple[str, int, str]] = []

    def reserve(self, policy: ProviderBudgetPolicy, now: dt.datetime) -> bool:
        self.reservations.append((policy.provider, policy.units_per_request))
        return policy.provider not in self.denied

    def block(self, provider: str, now: dt.datetime, seconds: int, reason: str) -> None:
        self.blocks.append((provider, seconds, reason))


def _registration(name: str, provider: _Provider, *capabilities: str):
    return OperationalProviderRegistration(
        name=name,
        provider=provider,
        capabilities=frozenset(capabilities),
        budget=ProviderBudgetPolicy(
            provider=name,
            window="month",
            hard_limit=90,
            units_per_request=1,
        ),
    )


def test_falls_back_after_quota_and_remote_failures_then_enriches_position() -> None:
    first = _Provider(OperationalUnavailable(reason="provider"))
    second = _Provider(OperationalObserved(_observation("aerodatabox")))
    position = _Provider(
        OperationalObserved(replace(_observation("opensky", positioned=True), status="unknown"))
    )
    ledger = _Ledger(denied={"amadeus"})
    provider = QuotaAwareOperationalFlightProvider(
        [
            _registration("amadeus", first, "status_schedule"),
            _registration("aviationstack", first, "status_schedule"),
            _registration("aerodatabox", second, "status_schedule", "position"),
            _registration("opensky", position, "position"),
        ],
        ledger,
    )

    outcome = provider.fetch(_identity(), NOW)

    assert isinstance(outcome, OperationalObserved)
    observation = outcome.observation
    assert observation.provider == "aerodatabox+opensky"
    assert observation.status == "active"
    assert observation.departure_gate == "B12"
    assert observation.latitude == 41.1
    assert observation.speed_mps == 220
    assert first.identities and len(first.identities) == 1
    assert position.identities[0].icao24 == "4ca123"
    assert ("amadeus", 1) in ledger.reservations


def test_does_not_spend_position_quota_when_status_provider_has_position() -> None:
    complete = _Provider(OperationalObserved(_observation("aerodatabox", positioned=True)))
    position = _Provider(OperationalObserved(_observation("opensky", positioned=True)))
    ledger = _Ledger()
    provider = QuotaAwareOperationalFlightProvider(
        [
            _registration("aerodatabox", complete, "status_schedule", "position"),
            _registration("opensky", position, "position"),
        ],
        ledger,
    )

    outcome = provider.fetch(_identity(), NOW)

    assert isinstance(outcome, OperationalObserved)
    assert outcome.observation.provider == "aerodatabox"
    assert position.identities == []
    assert ledger.reservations == [("aerodatabox", 1)]


def test_rate_limit_blocks_only_provider_and_chain_continues() -> None:
    limited = _Provider(OperationalRateLimited(retry_after_seconds=77))
    fallback = _Provider(OperationalNoCoverage(reason="no_match"))
    ledger = _Ledger()
    provider = QuotaAwareOperationalFlightProvider(
        [
            _registration("aviationstack", limited, "status_schedule"),
            _registration("aerodatabox", fallback, "status_schedule"),
        ],
        ledger,
    )

    outcome = provider.fetch(_identity(), NOW)

    assert isinstance(outcome, OperationalNoCoverage)
    assert ledger.blocks == [("aviationstack", 77, "rate_limited")]


def test_payment_required_blocks_provider_for_full_billing_window() -> None:
    paid = _Provider(OperationalUnavailable(reason="payment_required"))
    fallback = _Provider(OperationalObserved(_observation("aviationstack")))
    ledger = _Ledger()
    provider = QuotaAwareOperationalFlightProvider(
        [
            _registration("flightaware", paid, "status_schedule"),
            _registration("aviationstack", fallback, "status_schedule"),
        ],
        ledger,
    )

    outcome = provider.fetch(_identity(), NOW)

    assert isinstance(outcome, OperationalObserved)
    assert outcome.observation.provider == "aviationstack"
    assert ledger.blocks == [("flightaware", 31 * 86_400, "payment_required")]


def test_all_unconfigured_returns_not_configured() -> None:
    provider = QuotaAwareOperationalFlightProvider([], _Ledger())

    outcome = provider.fetch(_identity(), NOW)

    assert isinstance(outcome, OperationalNotConfigured)
