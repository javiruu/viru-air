import pytest
import requests

from app.domain.entities import ProviderSourceFetchError
from app.infrastructure.providers.vueling_provider import VuelingProvider


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def test_provider_is_enabled_without_api_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VUELING_FLIGHTCALENDAR_TOKEN", raising=False)
    monkeypatch.delenv("VUELING_FLIGHTCALENDAR_PRICES_URL", raising=False)

    provider = VuelingProvider()

    assert provider.is_enabled() is True


def test_get_flights_uses_anonymous_public_availability(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = VuelingProvider()
    calls: list[tuple[str, dict]] = []

    def fake_post(url: str, *, json, timeout: float, headers):
        calls.append((url, json))
        if url.endswith("/asm/v1/Auth"):
            assert json == {"profileId": "e8ffa738-cb67-4a02-b501-9bfd975a4b65"}
            assert "Authorization" not in headers
            return _FakeResponse(
                {
                    "tokenType": "Bearer",
                    "accessToken": "anonymous-token",
                    "expiration": 1200,
                    "userType": "Anonymous",
                }
            )

        assert url.endswith("/avy/v3/AvailabilityServices/allFlights")
        assert headers["Authorization"] == "Bearer anonymous-token"
        assert json == {
            "originCode": "BCN",
            "destinationCode": "ORY",
            "year": 2026,
            "month": 7,
            "currencyCode": "EUR",
            "monthsRange": 17,
            "flightType": "ONE_WAY",
        }
        return _FakeResponse(
            [
                {
                    "arrivalStation": "ORY",
                    "departureDate": "2026-07-14T18:45:00",
                    "departureStation": "BCN",
                    "flightID": "8020",
                    "price": 75.99,
                    "carrierCode": "VY",
                    "currency": "EUR",
                    "isAvailableDay": True,
                    "isInvalidPrice": False,
                },
                {
                    "arrivalStation": "FCO",
                    "departureDate": "2026-07-14T20:10:00",
                    "departureStation": "BCN",
                    "flightID": "6104",
                    "price": 120.00,
                    "carrierCode": "VY",
                    "currency": "EUR",
                    "isAvailableDay": True,
                    "isInvalidPrice": False,
                },
            ]
        )

    monkeypatch.setattr(provider._session, "post", fake_post)

    result = provider.get_flights("BCN", "ORY", "2026-07-14")

    assert [url for url, _ in calls] == [
        "https://ams.vueling.com/asm/v1/Auth",
        "https://ams.vueling.com/avy/v3/AvailabilityServices/allFlights",
    ]
    assert len(result.flights) == 1
    flight = result.flights[0]
    assert flight.price == 75.99
    assert flight.currency == "EUR"
    assert flight.departure_time_local == "18:45"
    assert flight.source == "vueling-public-availability"
    assert flight.deeplink_url is not None
    assert "booking/flightSearch" in flight.deeplink_url
    assert result.warnings_structured == []


def test_get_flights_returns_empty_result_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = VuelingProvider()

    def fake_post(url: str, *, json, timeout: float, headers):
        if url.endswith("/asm/v1/Auth"):
            return _FakeResponse({"tokenType": "Bearer", "accessToken": "anonymous-token"})
        return _FakeResponse([])

    monkeypatch.setattr(provider._session, "post", fake_post)

    result = provider.get_flights("BCN", "ORY", "2026-07-14")

    assert result.flights == []
    assert result.warnings == []
    assert result.warnings_structured is not None
    assert result.warnings_structured[0].code == "provider_empty_result"
    assert result.warnings_structured[0].provider == "vueling"


def test_get_flights_ignores_invalid_availability_item(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = VuelingProvider()

    def fake_post(url: str, *, json, timeout: float, headers):
        if url.endswith("/asm/v1/Auth"):
            return _FakeResponse({"tokenType": "Bearer", "accessToken": "anonymous-token"})
        return _FakeResponse(
            [
                {
                    "arrivalStation": "ORY",
                    "departureDate": "2026-07-14T18:45:00",
                    "departureStation": "BCN",
                    "price": 0,
                    "currency": "EUR",
                    "isAvailableDay": True,
                    "isInvalidPrice": False,
                },
                {
                    "arrivalStation": "ORY",
                    "departureDate": "2026-07-14T18:45:00",
                    "departureStation": "BCN",
                    "price": 75.99,
                    "currency": "EUR",
                    "isAvailableDay": False,
                    "isInvalidPrice": False,
                },
            ]
        )

    monkeypatch.setattr(provider._session, "post", fake_post)

    result = provider.get_flights("BCN", "ORY", "2026-07-14")

    assert result.flights == []
    assert result.warnings_structured is not None
    assert result.warnings_structured[0].code == "provider_empty_result"


def test_get_flights_raises_canonical_outage_when_request_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = VuelingProvider()

    def fake_post(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(provider._session, "post", fake_post)

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("BCN", "ORY", "2026-07-14")

    assert exc_info.value.provider_id == "vueling"
    assert "vueling_provider_unavailable_total" in exc_info.value.warning_codes
    assert "provider_total_outage" in exc_info.value.warning_codes
