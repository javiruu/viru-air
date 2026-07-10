import datetime as dt

from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError
from app.infrastructure.providers.base import FlightProvider
from app.infrastructure.providers.orchestrator import FlightSearchOrchestrator
from app.services.provider_health_stats import reset_provider_health_stats_for_tests, snapshot_provider_health


def _flight(price: float, dep: str, source: str, currency: str = "EUR") -> ProviderFlight:
    return ProviderFlight(
        price=price,
        currency=currency,
        departure_time_local=dep,
        captured_at=dt.datetime.now(dt.UTC).replace(tzinfo=None),
        source=source,
    )


class _OkProvider(FlightProvider):
    provider_id = "ok"

    def is_enabled(self) -> bool:
        return True

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"):
        return ProviderFetchResult(
            flights=[
                _flight(100, "10:00", "ok-offers", "EUR"),
                _flight(100, "10:00", "ok-offers", "EUR"),
            ],
            warnings=[],
            warnings_structured=[],
        )


class _FailProvider(FlightProvider):
    provider_id = "fail"

    def is_enabled(self) -> bool:
        return True

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"):
        raise ProviderSourceFetchError(
            warning_codes=["provider_error_partial", "provider_total_outage"],
            message="failed",
            provider_id=self.provider_id,
        )


class _BuggyProvider(FlightProvider):
    provider_id = "wizzair"

    def is_enabled(self) -> bool:
        return True

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 12000, currency: str = "EUR"):
        raise ValueError("malformed farechart payload")


def test_orchestrator_merges_dedupes_and_collects_structured_warnings():
    orchestrator = FlightSearchOrchestrator(providers=[_OkProvider(), _FailProvider()])

    result = orchestrator.get_flights("MAD", "DUB", "2026-06-14")

    assert len(result.flights) == 1
    assert result.flights[0].source == "ok-offers"
    assert "provider_error_partial" in result.warnings
    assert "provider_total_outage" in result.warnings
    assert result.warnings_structured is not None
    assert any(item.provider == "fail" and item.code == "provider_error_partial" for item in result.warnings_structured)


def test_orchestrator_keeps_other_provider_results_when_one_provider_crashes():
    orchestrator = FlightSearchOrchestrator(providers=[_OkProvider(), _BuggyProvider()])

    result = orchestrator.get_flights("MAD", "DUB", "2026-06-14")

    assert len(result.flights) == 1
    assert result.flights[0].source == "ok-offers"
    assert "provider_error_partial" in result.warnings
    assert result.warnings_structured is not None
    warning = next(item for item in result.warnings_structured if item.provider == "wizzair")
    assert warning.code == "provider_error_partial"
    assert warning.meta == {"error_type": "ValueError"}


def test_orchestrator_records_local_provider_health_samples():
    reset_provider_health_stats_for_tests()
    orchestrator = FlightSearchOrchestrator(providers=[_OkProvider(), _FailProvider(), _BuggyProvider()])

    result = orchestrator.get_flights("MAD", "DUB", "2026-06-14")

    snapshots = {item.provider_id: item for item in snapshot_provider_health()}
    assert len(result.flights) == 1
    assert snapshots["ok"].calls == 1
    assert snapshots["ok"].successes == 1
    assert snapshots["fail"].calls == 1
    assert snapshots["fail"].outages == 1
    assert snapshots["wizzair"].calls == 1
    assert snapshots["wizzair"].errors == 1
