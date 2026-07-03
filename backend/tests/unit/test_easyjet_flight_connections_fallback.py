import pytest

from app.domain.entities import ProviderSourceFetchError
from app.infrastructure.providers.easyjet_provider import EasyJetProvider


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _QueuedSession:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = payloads
        self.headers: list[dict[str, str]] = []

    def get(self, url: str, *, params: dict[str, str], timeout: float, headers: dict[str, str]):
        self.headers.append(headers)
        return _FakeResponse(self.payloads.pop(0))


def test_get_flights_maps_flight_connections_search_payload_variant() -> None:
    provider = EasyJetProvider()
    session = _QueuedSession(
        [
            {"AvailableFlights": []},
            {
                "data": {
                    "search": {
                        "offers": [
                            {
                                "price": "88.67",
                                "currency": "eur",
                                "transferUrl": "https://flightconnections.easyjet.com/es/checkout/flexible",
                                "itinerary": {
                                    "outbound": [
                                        {
                                            "origin": {"code": "BLQ"},
                                            "destination": {"code": "OLB"},
                                            "legs": [
                                                {
                                                    "origin": {"code": "BLQ"},
                                                    "destination": {"code": "OLB"},
                                                    "departure": "2026-07-04T09:00:00+02:00",
                                                },
                                                {
                                                    "origin": {"code": "OLB"},
                                                    "destination": {"code": "BER"},
                                                    "departure": "2026-07-04T15:30:00+02:00",
                                                },
                                            ],
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                }
            },
        ]
    )
    provider._session = session

    result = provider.get_flights("BLQ", "BER", "2026-07-04")

    assert len(result.flights) == 1
    flight = result.flights[0]
    assert flight.price == 88.67
    assert flight.currency == "EUR"
    assert flight.departure_time_local == "09:00"
    assert flight.source == "easyjet-flight-connections"
    assert flight.deeplink_url == "https://flightconnections.easyjet.com/es/checkout/flexible"


def test_get_flights_uses_flight_connections_deeplink_when_transfer_url_is_missing() -> None:
    provider = EasyJetProvider(language_code="ES")
    session = _QueuedSession(
        [
            {"AvailableFlights": []},
            {
                "data": {
                    "boundSearch": {
                        "offers": [
                            {
                                "pricePerPerson": 88.67,
                                "currency": "EUR",
                                "itinerary": {
                                    "outbound": [
                                        {
                                            "origin": {"code": "BLQ"},
                                            "destination": {"code": "BER"},
                                            "departure": "2026-07-04T09:00:00+02:00",
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                }
            },
        ]
    )
    provider._session = session

    result = provider.get_flights("BLQ", "BER", "2026-07-04")

    assert len(result.flights) == 1
    assert result.flights[0].deeplink_url == (
        "https://flightconnections.easyjet.com/es/search?"
        "origins=BLQ&destinations=BER&departureDate=2026-07-04&"
        "isOneWay=true&adults=1&currency=EUR&residency=ES"
    )


def test_get_flights_sends_flight_connections_bypass_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EASYJET_FLIGHT_CONNECTIONS_BYPASS_SECRET", "secret-token")
    provider = EasyJetProvider()
    session = _QueuedSession(
        [
            {"AvailableFlights": []},
            {"data": {"boundSearch": {"offers": []}}},
        ]
    )
    provider._session = session

    result = provider.get_flights("BLQ", "BER", "2026-07-04")

    assert result.flights == []
    assert session.headers[1]["X-Dohop-Bypass"] == "secret-token"


def test_get_flights_raises_outage_when_flight_connections_returns_graphql_errors() -> None:
    provider = EasyJetProvider()
    session = _QueuedSession(
        [
            {"AvailableFlights": []},
            {"errors": [{"message": "Forbidden"}], "data": None},
        ]
    )
    provider._session = session

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("BLQ", "BER", "2026-07-04")

    assert exc_info.value.provider_id == "easyjet"
    assert "easyjet_provider_unavailable_total" in exc_info.value.warning_codes
    assert "provider_total_outage" in exc_info.value.warning_codes
