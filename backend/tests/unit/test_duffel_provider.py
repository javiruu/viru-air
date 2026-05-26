import pytest

from app.domain.entities import ProviderSourceFetchError
from app.infrastructure.providers.duffel_provider import DuffelProvider


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def post(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse(self.payload)


def test_get_flights_raises_when_duffel_not_configured() -> None:
    provider = DuffelProvider(api_key="")

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("MAD", "JFK", "2026-06-14")

    assert exc_info.value.warning_codes == ["duffel_not_configured"]


def test_get_flights_maps_offers_to_provider_flights() -> None:
    provider = DuffelProvider(api_key="duffel_test_key")
    provider._session = _FakeSession(
        {
            "data": {
                "offers": [
                    {
                        "total_amount": "123.45",
                        "total_currency": "EUR",
                        "slices": [{"segments": [{"departing_at": "2026-06-14T09:10:00Z"}]}],
                    }
                ]
            }
        }
    )

    result = provider.get_flights("MAD", "JFK", "2026-06-14")

    assert len(result.flights) == 1
    assert result.flights[0].price == 123.45
    assert result.flights[0].currency == "EUR"
    assert result.flights[0].departure_time_local == "09:10"
    assert result.flights[0].source == "duffel-offers"
