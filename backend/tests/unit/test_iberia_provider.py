import pytest

from app.domain.entities import ProviderSourceFetchError
from app.infrastructure.providers.iberia_provider import IberiaProvider


class _FakeResponse:
    def __init__(self, payload, *, json_error: bool = False) -> None:
        self.payload = payload
        self.json_error = json_error
        self.text = payload if isinstance(payload, str) else ""

    def raise_for_status(self) -> None:
        return None

    def json(self):
        if self.json_error:
            raise ValueError("not json")
        return self.payload


class _FakeSession:
    def __init__(self, payload, *, json_error: bool = False) -> None:
        self.payload = payload
        self.json_error = json_error
        self.calls: list[tuple[str, dict, dict[str, str]]] = []

    def post(self, url: str, *, json: dict, timeout: float, headers: dict[str, str]) -> _FakeResponse:
        self.calls.append((url, json, headers))
        return _FakeResponse(self.payload, json_error=self.json_error)


def test_provider_is_enabled_without_api_credentials() -> None:
    provider = IberiaProvider(api_base_url="https://api.example.test", authorization="Basic public-token")

    assert provider.is_enabled() is True


def test_get_flights_uses_public_booking_availability() -> None:
    payload = {
        "responseId": "response-1",
        "originDestinations": [
            {
                "slices": [
                    {
                        "origin": "MAD",
                        "destination": "JFK",
                        "departureDateTime": "2026-06-14T12:35:00",
                    }
                ],
                "offers": [
                    {
                        "offerId": "offer-1",
                        "totalPrice": {"amount": 183.4, "currency": "EUR"},
                        "segments": [
                            {
                                "origin": "MAD",
                                "destination": "JFK",
                                "departureDateTime": "2026-06-14T12:35:00",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    provider = IberiaProvider(
        api_base_url="https://ibisservices.example.test/api",
        base_url="https://www.iberia.example.test",
        authorization="Basic public-token",
        market="ES",
        language="es",
    )
    session = _FakeSession(payload)
    provider._session = session

    result = provider.get_flights("mad", "jfk", "2026-06-14", currency="eur")

    assert len(result.flights) == 1
    flight = result.flights[0]
    assert flight.price == 183.4
    assert flight.currency == "EUR"
    assert flight.departure_time_local == "12:35"
    assert flight.source == "iberia-public-availability"
    assert flight.deeplink_url is not None
    assert "BEGIN_CITY_01=MAD" in flight.deeplink_url
    assert "END_CITY_01=JFK" in flight.deeplink_url
    assert result.warnings_structured == []
    assert session.calls[0][0] == "https://ibisservices.example.test/api/sse-avm/rs/v2/availability"
    assert session.calls[0][1] == {
        "slices": [{"origin": "MAD", "destination": "JFK", "date": "2026-06-14"}],
        "passengers": [{"passengerType": "ADULT", "count": 1}],
        "preferredCabin": "ECONOMY",
    }
    assert session.calls[0][2]["Authorization"] == "Basic public-token"
    assert session.calls[0][2]["Origin"] == "https://www.iberia.example.test"


def test_get_flights_returns_empty_result_warning_for_public_payload_without_offers() -> None:
    provider = IberiaProvider(api_base_url="https://api.example.test", authorization="Basic public-token")
    provider._session = _FakeSession({"originDestinations": []})

    result = provider.get_flights("MAD", "JFK", "2026-06-14")

    assert result.flights == []
    assert result.warnings_structured is not None
    assert result.warnings_structured[0].code == "provider_empty_result"
    assert result.warnings_structured[0].provider == "iberia"


def test_get_flights_raises_canonical_outage_when_public_response_is_not_json() -> None:
    provider = IberiaProvider(api_base_url="https://api.example.test", authorization="Basic public-token")
    provider._session = _FakeSession("<html>Access Denied</html>", json_error=True)

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("MAD", "JFK", "2026-06-14")

    assert exc_info.value.provider_id == "iberia"
    assert exc_info.value.warning_codes == ["iberia_provider_unavailable_total", "provider_total_outage"]
