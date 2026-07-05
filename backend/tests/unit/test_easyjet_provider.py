import json

import pytest

from app.domain.entities import ProviderSourceFetchError
from app.infrastructure.providers.easyjet_provider import EasyJetProvider, RequestsError


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
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, *, params: dict[str, str], timeout: float, headers: dict[str, str]):
        if self.exc is not None:
            raise self.exc
        self.calls.append((url, params))
        return _FakeResponse(self.payload)

    def post(self, url: str, *, json, timeout: float, headers: dict[str, str]):
        # After the GET → POST switch for the flight connections fallback, any
        # test that drives only the public availability path also implicitly
        # falls through to a flight-connections POST (when public_avail returns
        # empty / errors). We mirror `get` so the fallback sees the same payload
        # or hits the same exception as the test author intended.
        if self.exc is not None:
            raise self.exc
        self.calls.append((url, json))
        return _FakeResponse(self.payload)


class _QueuedSession:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = payloads
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, *, params: dict[str, str], timeout: float, headers: dict[str, str]):
        self.calls.append((url, params))
        return _FakeResponse(self.payloads.pop(0))

    def post(self, url: str, *, json, timeout: float, headers: dict[str, str]):
        # The flight connections fallback now POSTs the same query/variables dict
        # as a JSON body (avoids long-URI WAF heuristics on Dohop's edge).
        self.calls.append((url, json))
        return _FakeResponse(self.payloads.pop(0))


class _InvalidJsonSession:
    def get(self, *args, **kwargs) -> _InvalidJsonResponse:
        return _InvalidJsonResponse()

    def post(self, *args, **kwargs) -> _InvalidJsonResponse:
        return _InvalidJsonResponse()


def _skip_warmup(provider: EasyJetProvider) -> None:
    """Tests mock `_session` so the warmup `get` would consume queue payloads.

    Setting both warmed markers short-circuits the warmup helpers and keeps the
    recorded call sequence predictable for the assertions below.
    """
    provider._warmed_marketing = True
    provider._warmed_flightconnections = True


def test_get_flights_maps_easyjet_public_availability() -> None:
    provider = EasyJetProvider()
    session = _FakeSession(
        {
            "AvailableFlights": [
                {
                    "CarrierCode": "EZY",
                    "FlightNumber": 2431,
                    "DepartureIata": "LTN",
                    "ArrivalIata": "CDG",
                    "LocalDepartureTime": "2026-07-14T07:05:00",
                    "FlightFares": [
                        {
                            "SeatsAvailable": 9,
                            "Prices": {
                                "Adult": {
                                    "Price": 85.86,
                                    "PriceWithDebitCard": 100.86,
                                }
                            },
                        }
                    ],
                },
                {
                    "CarrierCode": "EZY",
                    "FlightNumber": 2432,
                    "DepartureIata": "LTN",
                    "ArrivalIata": "AMS",
                    "LocalDepartureTime": "2026-07-14T08:05:00",
                    "FlightFares": [{"Prices": {"Adult": {"Price": 62.0}}}],
                },
            ]
        }
    )
    provider._session = session
    _skip_warmup(provider)

    result = provider.get_flights("ltn", "cdg", "2026-07-14", currency="eur")

    assert len(result.flights) == 1
    flight = result.flights[0]
    assert flight.price == 85.86
    assert flight.currency == "EUR"
    assert flight.departure_time_local == "07:05"
    assert flight.source == "easyjet-public-availability"
    assert flight.deeplink_url is not None
    assert "easyjet.com/deeplink" in flight.deeplink_url
    assert result.warnings_structured == []
    assert len(session.calls) == 1
    assert session.calls[0][0] == "https://www.easyjet.com/ejavailability/api/v16/availability/query"
    assert session.calls[0][1]["DepartureIata"] == "LTN"
    assert session.calls[0][1]["ArrivalIata"] == "CDG"
    assert session.calls[0][1]["MinDepartureDate"] == "2026-07-14"
    assert session.calls[0][1]["IncludePrices"] == "true"


def test_get_flights_returns_empty_result_warning() -> None:
    provider = EasyJetProvider()
    provider._session = _FakeSession({"AvailableFlights": []})
    _skip_warmup(provider)

    result = provider.get_flights("LGW", "BCN", "2026-07-14")

    assert result.flights == []
    assert result.warnings == []
    assert result.warnings_structured is not None
    assert result.warnings_structured[0].code == "provider_empty_result"
    assert result.warnings_structured[0].provider == "easyjet"


def test_get_flights_maps_easyjet_flight_connections_when_public_availability_is_empty() -> None:
    provider = EasyJetProvider()
    session = _QueuedSession(
        [
            {"AvailableFlights": []},
            {
                "data": {
                    "boundSearch": {
                        "offers": [
                            {
                                "pricePerPerson": 392.68,
                                "currency": "EUR",
                                "transferURL": "https://flightconnections.easyjet.com/es/checkout/demo",
                                "itinerary": {
                                    "outbound": [
                                        {
                                            "origin": {"code": "BLQ"},
                                            "destination": {"code": "BER"},
                                            "departure": "2026-07-04T13:15:00+02:00",
                                            "arrival": "2026-07-04T22:50:00+02:00",
                                            "legs": [
                                                {
                                                    "origin": {"code": "BLQ"},
                                                    "destination": {"code": "OLB"},
                                                },
                                                {
                                                    "origin": {"code": "OLB"},
                                                    "destination": {"code": "BER"},
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
    _skip_warmup(provider)

    result = provider.get_flights("BLQ", "BER", "2026-07-04")

    assert len(result.flights) == 1
    flight = result.flights[0]
    assert flight.price == 392.68
    assert flight.currency == "EUR"
    assert flight.departure_time_local == "13:15"
    assert flight.source == "easyjet-flight-connections"
    assert flight.deeplink_url == "https://flightconnections.easyjet.com/es/checkout/demo"
    assert session.calls[1][0] == "https://flightconnections.easyjet.com/api/graphql"
    assert session.calls[1][1]["variables"].startswith('{"departureDateString": "2026-07-04"')


def test_get_flights_ignores_unavailable_or_invalid_fares() -> None:
    provider = EasyJetProvider()
    provider._session = _FakeSession(
        {
            "AvailableFlights": [
                {
                    "DepartureIata": "LGW",
                    "ArrivalIata": "BCN",
                    "LocalDepartureTime": "2026-07-14T06:30:00",
                    "FlightFares": [{"SeatsAvailable": 0, "Prices": {"Adult": {"Price": 80}}}],
                },
                {
                    "DepartureIata": "LGW",
                    "ArrivalIata": "BCN",
                    "LocalDepartureTime": "2026-07-14T07:30:00",
                    "FlightFares": [{"SeatsAvailable": 3, "Prices": {"Adult": {"Price": 0}}}],
                },
            ]
        }
    )
    _skip_warmup(provider)

    result = provider.get_flights("LGW", "BCN", "2026-07-14")

    assert result.flights == []
    assert result.warnings_structured is not None
    assert result.warnings_structured[0].code == "provider_empty_result"


def test_get_flights_raises_canonical_outage_when_request_fails() -> None:
    provider = EasyJetProvider()
    provider._session = _FakeSession(exc=RequestsError("blocked"))
    _skip_warmup(provider)

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("LGW", "BCN", "2026-07-14")

    assert exc_info.value.provider_id == "easyjet"
    assert "easyjet_provider_unavailable_total" in exc_info.value.warning_codes
    assert "provider_total_outage" in exc_info.value.warning_codes


def test_get_flights_raises_canonical_outage_when_response_is_not_json() -> None:
    provider = EasyJetProvider()
    provider._session = _InvalidJsonSession()
    _skip_warmup(provider)

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("LGW", "BCN", "2026-07-14")

    assert exc_info.value.provider_id == "easyjet"
    assert "easyjet_provider_unavailable_total" in exc_info.value.warning_codes
    assert "provider_total_outage" in exc_info.value.warning_codes
