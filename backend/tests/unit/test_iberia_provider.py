import pytest

from app.domain.entities import ProviderSourceFetchError
from app.infrastructure.providers.iberia_provider import IberiaProvider


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self.text = payload

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def post(self, url: str, *, data: str, timeout: float, headers: dict[str, str]) -> _FakeResponse:
        self.calls.append((url, data, headers))
        return _FakeResponse(self.payload)


def test_get_flights_raises_when_iberia_not_configured() -> None:
    provider = IberiaProvider(api_key="", base_url="")

    with pytest.raises(ProviderSourceFetchError) as exc_info:
        provider.get_flights("MAD", "JFK", "2026-06-14")

    assert exc_info.value.provider_id == "iberia"
    assert exc_info.value.warning_codes == ["iberia_not_configured"]


def test_get_flights_maps_ndc_airshopping_offers_to_provider_flights() -> None:
    payload = """<?xml version="1.0" encoding="UTF-8"?>
<AirShoppingRS xmlns="http://www.iata.org/IATA/EDIST/2017.2">
  <OffersGroup>
    <AirlineOffers>
      <Offer OfferID="offer-1">
        <TotalPrice>
          <SimpleCurrencyPrice Code="EUR">183.40</SimpleCurrencyPrice>
        </TotalPrice>
        <OfferItem>
          <Service>
            <FlightRefs>SEG1</FlightRefs>
          </Service>
        </OfferItem>
      </Offer>
    </AirlineOffers>
  </OffersGroup>
  <DataLists>
    <FlightSegmentList>
      <FlightSegment SegmentKey="SEG1">
        <Departure>
          <AirportCode>MAD</AirportCode>
          <DateTime>2026-06-14T12:35:00</DateTime>
        </Departure>
        <Arrival>
          <AirportCode>JFK</AirportCode>
        </Arrival>
      </FlightSegment>
    </FlightSegmentList>
  </DataLists>
</AirShoppingRS>"""
    provider = IberiaProvider(api_key="iberia-test-key", base_url="https://ndc.example.test")
    session = _FakeSession(payload)
    provider._session = session

    result = provider.get_flights("mad", "jfk", "2026-06-14", currency="eur")

    assert len(result.flights) == 1
    flight = result.flights[0]
    assert flight.price == 183.40
    assert flight.currency == "EUR"
    assert flight.departure_time_local == "12:35"
    assert flight.source == "iberia-ndc-airshopping"
    assert flight.deeplink_url == "https://www.iberia.com"
    assert result.warnings_structured == []
    assert session.calls[0][0] == "https://ndc.example.test/AirShopping"
    assert session.calls[0][2]["apikey"] == "iberia-test-key"
    assert "<AirportCode>MAD</AirportCode>" in session.calls[0][1]


def test_get_flights_returns_empty_result_warning_for_ndc_without_matching_offers() -> None:
    provider = IberiaProvider(api_key="iberia-test-key", base_url="https://ndc.example.test")
    provider._session = _FakeSession("<AirShoppingRS />")

    result = provider.get_flights("MAD", "JFK", "2026-06-14")

    assert result.flights == []
    assert result.warnings_structured is not None
    assert result.warnings_structured[0].code == "provider_empty_result"
    assert result.warnings_structured[0].provider == "iberia"
