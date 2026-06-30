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


def test_get_flights_maps_flight_calendar_v2_item(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = VuelingProvider(
        api_token="token",
        prices_url="https://example.test/flight-calendar/prices",
    )

    def fake_get(url: str, *, params, timeout: float, headers):
        assert url == "https://example.test/flight-calendar/prices"
        assert params == {"startDate": "20260614", "numDays": "1", "productClass": "BA"}
        assert headers["Authorization"] == "token"
        return _FakeResponse(
            {
                "IsSuccessful": True,
                "Result": [
                    {
                        "Carrier": "VY",
                        "Date": 20260614,
                        "Items": [
                            "EUR;2026-06-01T09:34;85.64~"
                            "VY;6103;BCN;14/06/2026 19:05:00;ORY;14/06/2026 20:55:00;BA;5;OOWVYCLB",
                            "EUR;2026-06-01T09:34;120.00~"
                            "VY;6104;BCN;14/06/2026 22:10:00;FCO;14/06/2026 23:55:00;BA;3;OOWVYCLB",
                        ],
                    }
                ],
            }
        )

    monkeypatch.setattr(provider._session, "get", fake_get)

    result = provider.get_flights("BCN", "ORY", "2026-06-14")

    assert len(result.flights) == 1
    flight = result.flights[0]
    assert flight.price == 85.64
    assert flight.currency == "EUR"
    assert flight.departure_time_local == "19:05"
    assert flight.source == "vueling-flight-calendar"
    assert flight.deeplink_url is not None
    assert "booking/flightSearch" in flight.deeplink_url
    assert result.warnings_structured == []


def test_get_flights_returns_empty_result_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = VuelingProvider(
        api_token="token",
        prices_url="https://example.test/flight-calendar/prices",
    )

    def fake_get(*args, **kwargs):
        return _FakeResponse({"IsSuccessful": True, "Result": []})

    monkeypatch.setattr(provider._session, "get", fake_get)

    result = provider.get_flights("BCN", "ORY", "2026-06-14")

    assert result.flights == []
    assert result.warnings == []
    assert result.warnings_structured is not None
    assert result.warnings_structured[0].code == "provider_empty_result"
    assert result.warnings_structured[0].provider == "vueling"


def test_get_flights_ignores_malformed_calendar_item(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = VuelingProvider(
        api_token="token",
        prices_url="https://example.test/flight-calendar/prices",
    )

    def fake_get(*args, **kwargs):
        return _FakeResponse(
            {
                "IsSuccessful": True,
                "Result": [
                    {
                        "Carrier": "VY",
                        "Date": 20260614,
                        "Items": ["EUR;2026-06-01T09:34;85.64~VY;6103;BCN"],
                    }
                ],
            }
        )

    monkeypatch.setattr(provider._session, "get", fake_get)

    result = provider.get_flights("BCN", "ORY", "2026-06-14")

    assert result.flights == []
    assert result.warnings_structured is not None
    assert result.warnings_structured[0].code == "provider_empty_result"


def test_get_flights_raises_canonical_outage_when_request_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = VuelingProvider(
        api_token="token",
        prices_url="https://example.test/flight-calendar/prices",
    )

    def fake_get(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(provider._session, "get", fake_get)

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("BCN", "ORY", "2026-06-14")

    assert exc_info.value.provider_id == "vueling"
    assert "vueling_provider_unavailable_total" in exc_info.value.warning_codes
    assert "provider_total_outage" in exc_info.value.warning_codes
