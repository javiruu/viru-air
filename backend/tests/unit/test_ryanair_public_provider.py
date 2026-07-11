import json

import pytest

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight, ProviderSourceFetchError
from app.infrastructure.providers.ryanair_public_provider import RequestsError, RyanairPublicProvider


class _InvalidJsonResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self):
        raise json.JSONDecodeError("Expecting value", "", 0)


class _InvalidJsonSession:
    def get(self, *args, **kwargs) -> _InvalidJsonResponse:
        return _InvalidJsonResponse()


def test_get_flights_falls_back_to_fares_when_availability_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = RyanairPublicProvider()

    def fake_availability(origin: str, destination: str, travel_date: str, *, timeout_ms: int, currency: str):
        raise RequestsError("409 conflict")

    def fake_fares(origin: str, destination: str, travel_date: str, *, timeout_ms: int, currency: str):
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
        raise RequestsError("timeout")

    monkeypatch.setattr(provider, "_fetch_availability", fail)
    monkeypatch.setattr(provider, "_fetch_one_way_fares", fail)

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("MAD", "DUB", "2026-06-14")

    assert "ryanair_availability_failed" in exc_info.value.warning_codes
    assert "ryanair_fares_failed" in exc_info.value.warning_codes
    assert "ryanair_provider_unavailable_total" in exc_info.value.warning_codes
    assert "provider_total_outage" in exc_info.value.warning_codes


def test_get_flights_raises_when_ryanair_sources_return_non_json() -> None:
    provider = RyanairPublicProvider()
    provider._session = _InvalidJsonSession()

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("MAD", "DUB", "2026-06-14")

    assert "ryanair_availability_failed" in exc_info.value.warning_codes
    assert "ryanair_fares_failed" in exc_info.value.warning_codes
    assert "ryanair_provider_unavailable_total" in exc_info.value.warning_codes
    assert "provider_total_outage" in exc_info.value.warning_codes


def test_availability_flights_include_normalized_provider_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = RyanairPublicProvider()

    def fake_get_json(url: str, *, timeout_ms: int):
        assert "Origin=MAD" in url
        assert "Destination=DUB" in url
        assert "DateOut=2026-06-14" in url
        return {
            "trips": [
                {
                    "flights": [
                        {
                            "flightNumber": "fr 7032",
                            "regularFare": {"fares": [{"amount": 42.5}]},
                            "time": ["2026-06-14T06:30:00"],
                        }
                    ]
                }
            ]
        }

    monkeypatch.setattr(provider, "_get_json", fake_get_json)

    flights = provider._fetch_availability("MAD", "DUB", "2026-06-14", timeout_ms=1000, currency="EUR")

    assert len(flights) == 1
    flight = flights[0]
    assert flight.provider == "ryanair"
    assert flight.origin_iata == "MAD"
    assert flight.destination_iata == "DUB"
    assert flight.travel_date == "2026-06-14"
    assert flight.departure_time_local == "06:30"
    assert flight.carrier_code == "FR"
    assert flight.flight_number == "FR7032"
    assert flight.deeplink_url is not None
    assert "ryanair.com" in flight.deeplink_url
