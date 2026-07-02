from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight

type JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class EasyJetPublicAvailabilitySearch:
    origin: str
    destination: str
    travel_date: str
    currency: str
    language: str
    base_url: str


def build_public_availability_params(search: EasyJetPublicAvailabilitySearch) -> dict[str, str]:
    return {
        "AdditionalSeats": "0",
        "AdultSeats": "1",
        "ArrivalIata": search.destination,
        "ChildSeats": "0",
        "DepartureIata": search.origin,
        "IncludeAdminFees": "true",
        "IncludeFlexiFares": "false",
        "IncludeLowestFareSeats": "true",
        "IncludePrices": "true",
        "Infants": "0",
        "IsTransfer": "false",
        "LanguageCode": search.language,
        "MaxDepartureDate": search.travel_date,
        "MaxReturnDate": search.travel_date,
        "MinDepartureDate": search.travel_date,
        "MinReturnDate": search.travel_date,
    }


def extract_public_availability_flights(
    payload: Mapping[str, JsonValue], search: EasyJetPublicAvailabilitySearch
) -> list[ProviderFlight]:
    raw_flights = payload.get("AvailableFlights")
    if not isinstance(raw_flights, list):
        return []
    flights: list[ProviderFlight] = []
    for item in raw_flights:
        if not isinstance(item, dict):
            continue
        flight = _flight_from_item(item, search)
        if flight is not None:
            flights.append(flight)
    return flights


def _flight_from_item(
    item: Mapping[str, JsonValue], search: EasyJetPublicAvailabilitySearch
) -> ProviderFlight | None:
    if _normalized_text(item.get("DepartureIata")) != search.origin:
        return None
    if _normalized_text(item.get("ArrivalIata")) != search.destination:
        return None

    departure_raw = _text(item.get("LocalDepartureTime"))
    if _to_iso_date(departure_raw) != search.travel_date:
        return None

    amount = _lowest_adult_price(item.get("FlightFares"))
    if amount is None:
        return None

    return ProviderFlight(
        price=amount,
        currency=search.currency,
        departure_time_local=_to_time(departure_raw),
        captured_at=utc_now_naive(),
        source="easyjet-public-availability",
        deeplink_url=_build_deeplink(search),
    )


def _lowest_adult_price(raw_fares: JsonValue) -> float | None:
    if not isinstance(raw_fares, list):
        return None
    prices: list[float] = []
    for raw_fare in raw_fares:
        if not isinstance(raw_fare, dict):
            continue
        seats_available = raw_fare.get("SeatsAvailable")
        if isinstance(seats_available, int) and seats_available <= 0:
            continue
        amount = _positive_float(_adult_price_from_fare(raw_fare))
        if amount is not None:
            prices.append(amount)
    return min(prices) if prices else None


def _adult_price_from_fare(fare: Mapping[str, JsonValue]) -> JsonValue:
    raw_prices = fare.get("Prices")
    if not isinstance(raw_prices, dict):
        return None
    raw_adult = raw_prices.get("Adult")
    return raw_adult.get("Price") if isinstance(raw_adult, dict) else None


def _build_deeplink(search: EasyJetPublicAvailabilitySearch) -> str:
    params = {
        "lang": search.language,
        "dep": search.origin,
        "dest": search.destination,
        "dd": search.travel_date,
        "apax": "1",
        "cpax": "0",
        "ipax": "0",
        "isOneWay": "on",
        "pid": "www.easyjet.com",
    }
    return f"{search.base_url}/deeplink?{urlencode(params)}"


def _normalized_text(value: JsonValue) -> str:
    return _text(value).upper().strip()


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
