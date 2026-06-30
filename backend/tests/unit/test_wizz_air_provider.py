import json

import pytest

from app.domain.entities import ProviderSourceFetchError
from app.infrastructure.providers.wizz_air_provider import RequestsError, WizzAirProvider


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _InvalidJsonResponse(_FakeResponse):
    def __init__(self) -> None:
        super().__init__({})

    def json(self) -> dict:
        raise json.JSONDecodeError("Expecting value", "", 0)


class _FakeSession:
    def __init__(self, payload: dict | None = None, *, exc: Exception | None = None) -> None:
        self.payload = payload or {}
        self.exc = exc

    def post(self, *args, **kwargs) -> _FakeResponse:
        if self.exc is not None:
            raise self.exc
        return _FakeResponse(self.payload)


class _InvalidJsonSession:
    def post(self, *args, **kwargs) -> _InvalidJsonResponse:
        return _InvalidJsonResponse()


def test_get_flights_maps_exact_day_from_farechart() -> None:
    provider = WizzAirProvider()
    provider._session = _FakeSession(
        {
            "outboundFlights": [
                {
                    "departureStation": "BUD",
                    "arrivalStation": "FCO",
                    "date": "2026-08-10T00:00:00",
                    "price": {"amount": 8696.0, "currencyCode": "HUF"},
                },
                {
                    "departureStation": "BUD",
                    "arrivalStation": "FCO",
                    "date": "2026-08-11T00:00:00",
                    "price": {"amount": 13736.0, "currencyCode": "HUF"},
                },
            ]
        }
    )

    result = provider.get_flights("BUD", "FCO", "2026-08-10")

    assert len(result.flights) == 1
    assert result.flights[0].price == 8696.0
    assert result.flights[0].currency == "HUF"
    assert result.flights[0].departure_time_local is None
    assert result.flights[0].source == "wizzair-farechart"


def test_get_flights_returns_empty_result_when_requested_date_has_no_fare() -> None:
    provider = WizzAirProvider()
    provider._session = _FakeSession(
        {
            "outboundFlights": [
                {
                    "departureStation": "BUD",
                    "arrivalStation": "FCO",
                    "date": "2026-08-11T00:00:00",
                    "price": {"amount": 13736.0, "currencyCode": "HUF"},
                }
            ]
        }
    )

    result = provider.get_flights("BUD", "FCO", "2026-08-10")

    assert result.flights == []
    assert result.warnings == []
    assert result.warnings_structured is not None
    assert result.warnings_structured[0].code == "provider_empty_result"
    assert result.warnings_structured[0].provider == "wizzair"


def test_get_flights_raises_when_wizzair_farechart_fails() -> None:
    provider = WizzAirProvider()
    provider._session = _FakeSession(exc=RequestsError("timeout"))

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("BUD", "FCO", "2026-08-10")

    assert exc_info.value.provider_id == "wizzair"
    assert "wizzair_provider_unavailable_total" in exc_info.value.warning_codes
    assert "provider_total_outage" in exc_info.value.warning_codes


def test_get_flights_raises_when_wizzair_farechart_returns_non_json() -> None:
    provider = WizzAirProvider()
    provider._session = _InvalidJsonSession()

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("BUD", "FCO", "2026-08-10")

    assert exc_info.value.provider_id == "wizzair"
    assert "wizzair_provider_unavailable_total" in exc_info.value.warning_codes
    assert "provider_total_outage" in exc_info.value.warning_codes
