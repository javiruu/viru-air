import pytest
import requests

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight, ProviderSourceFetchError
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider


def test_get_flights_falls_back_to_fares_when_availability_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = RyanairPublicProvider()

    def fake_availability(origin: str, destination: str, travel_date: str, *, timeout_ms: int):
        raise requests.HTTPError("409 conflict")

    def fake_fares(origin: str, destination: str, travel_date: str, *, timeout_ms: int):
        return [
            ProviderFlight(
                price=52.4,
                currency="EUR",
                departure_time_local="22:00",
                captured_at=utc_now_naive(),
                source="ryanair-public-fares",
            )
        ]

    monkeypatch.setattr(provider, "_fetch_availability", fake_availability)
    monkeypatch.setattr(provider, "_fetch_one_way_fares", fake_fares)

    result = provider.get_flights("MAD", "DUB", "2026-06-14")

    assert len(result.flights) == 1
    assert result.flights[0].source == "ryanair-public-fares"
    assert "ryanair_availability_failed_partial" in result.warnings


def test_get_flights_raises_when_both_sources_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = RyanairPublicProvider()

    def fail(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(provider, "_fetch_availability", fail)
    monkeypatch.setattr(provider, "_fetch_one_way_fares", fail)

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("MAD", "DUB", "2026-06-14")

    assert exc_info.value.warning_codes == [
        "ryanair_availability_failed",
        "ryanair_fares_failed",
        "ryanair_provider_unavailable_total",
    ]
