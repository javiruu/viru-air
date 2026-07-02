from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import json
from typing import Final
from urllib.parse import urlencode

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight

type JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]

_SEARCH_OUTBOUND_QUERY: Final = """
    query searchOutbound($partner: Partner!, $origin: String!, $destination: String!, $passengerAges: [PositiveInt!]!, $metadata: Metadata!, $departureDateString: String!, $returnDateString: String, $sort: Sort, $limit: PositiveInt, $filters: OfferFiltersInput, $utmSource: String) {
  boundSearch: searchOutbound(
    partner: $partner
    origin: $origin
    destination: $destination
    passengerAges: $passengerAges
    metadata: $metadata
    departureDateString: $departureDateString
    returnDateString: $returnDateString
    sort: $sort
    limit: $limit
    filters: $filters
    utmSource: $utmSource
  ) {
    offers {
      id
      price
      pricePerPerson
      outboundPricePerPerson
      currency
      transferURL
      itinerary {
        outbound {
          id
          origin { code name city country airsideTransfer }
          destination { code name city country airsideTransfer }
          departure
          arrival
          duration
          legs {
            id
            origin { code name city country airsideTransfer }
            destination { code name city country airsideTransfer }
            departure
            arrival
            carrierType
            operatingCarrier { name code flightNumber }
            marketingCarrier { name code flightNumber }
          }
        }
      }
      isOneWay
    }
    noResultsReasons
  }
}
"""


@dataclass(frozen=True, slots=True)
class EasyJetFlightConnectionsSearch:
    origin: str
    destination: str
    travel_date: str
    currency: str
    language: str
    residency: str
    base_url: str


def build_flight_connections_params(search: EasyJetFlightConnectionsSearch) -> dict[str, str]:
    variables: dict[str, JsonValue] = {
        "departureDateString": search.travel_date,
        "destination": search.destination,
        "filters": {"cabinClass": None, "carrierCodes": None},
        "limit": 25,
        "metadata": {
            "country": search.residency,
            "currency": search.currency,
            "language": search.language.lower(),
        },
        "origin": search.origin,
        "partner": "easyjet",
        "passengerAges": [30],
        "returnDateString": None,
        "sort": "RECOMMENDED",
        "utmSource": None,
    }
    return {"query": _SEARCH_OUTBOUND_QUERY, "variables": json.dumps(variables)}


def extract_flight_connections_flights(
    payload: Mapping[str, JsonValue], search: EasyJetFlightConnectionsSearch
) -> list[ProviderFlight]:
    data = _object(payload.get("data"))
    bound_search = _object(data.get("boundSearch")) if data else None
    raw_offers = bound_search.get("offers") if bound_search else None
    if not isinstance(raw_offers, list):
        return []

    flights: list[ProviderFlight] = []
    for raw_offer in raw_offers:
        if not isinstance(raw_offer, dict):
            continue
        flight = _flight_from_offer(raw_offer, search)
        if flight is not None:
            flights.append(flight)
    return flights


def build_flight_connections_deeplink(search: EasyJetFlightConnectionsSearch) -> str:
    params = {
        "origins": search.origin,
        "destinations": search.destination,
        "departureDate": search.travel_date,
        "isOneWay": "true",
        "adults": "1",
        "currency": search.currency,
        "residency": search.residency,
    }
    return f"{search.base_url}/{search.language.lower()}/search?{urlencode(params)}"


def _flight_from_offer(
    offer: Mapping[str, JsonValue], search: EasyJetFlightConnectionsSearch
) -> ProviderFlight | None:
    route = _first_outbound_route(offer)
    if route is None or not _route_matches(route, search):
        return None

    departure_raw = _text(route.get("departure"))
    if _to_iso_date(departure_raw) != search.travel_date:
        return None

    amount = _positive_float(offer.get("pricePerPerson")) or _positive_float(
        offer.get("outboundPricePerPerson")
    ) or _positive_float(offer.get("price"))
    if amount is None:
        return None

    currency = _text(offer.get("currency")).upper().strip() or search.currency
    deeplink = _text(offer.get("transferURL")) or build_flight_connections_deeplink(search)
    return ProviderFlight(
        price=amount,
        currency=currency,
        departure_time_local=_to_time(departure_raw),
        captured_at=utc_now_naive(),
        source="easyjet-flight-connections",
        deeplink_url=deeplink,
    )


def _first_outbound_route(offer: Mapping[str, JsonValue]) -> Mapping[str, JsonValue] | None:
    itinerary = _object(offer.get("itinerary"))
    raw_outbound = itinerary.get("outbound") if itinerary else None
    if not isinstance(raw_outbound, list):
        return None
    for route in raw_outbound:
        if isinstance(route, dict):
            return route
    return None


def _route_matches(route: Mapping[str, JsonValue], search: EasyJetFlightConnectionsSearch) -> bool:
    origin = _station_code(route.get("origin"))
    destination = _station_code(route.get("destination"))
    if origin == search.origin and destination == search.destination:
        return True

    legs = route.get("legs")
    if not isinstance(legs, list) or not legs:
        return False
    first_leg = legs[0] if isinstance(legs[0], dict) else None
    last_leg = legs[-1] if isinstance(legs[-1], dict) else None
    if first_leg is None or last_leg is None:
        return False
    return (
        _station_code(first_leg.get("origin")) == search.origin
        and _station_code(last_leg.get("destination")) == search.destination
    )


def _station_code(value: JsonValue) -> str:
    station = _object(value)
    return _text(station.get("code")).upper().strip() if station else ""


def _object(value: JsonValue) -> Mapping[str, JsonValue] | None:
    return value if isinstance(value, dict) else None


def _text(value: JsonValue) -> str:
    return value if isinstance(value, str) else ""


def _to_iso_date(value: str) -> str | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _to_time(value: str) -> str | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%H:%M")
    except ValueError:
        return None


def _positive_float(value: JsonValue) -> float | None:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount if amount > 0.0 else None
