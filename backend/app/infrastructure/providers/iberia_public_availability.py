from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final
from urllib.parse import urlencode

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight

_DEFAULT_CABIN: Final = "ECONOMY"
_PUBLIC_SOURCE: Final = "iberia-public-availability"


@dataclass(frozen=True, slots=True)
class IberiaPublicAvailabilitySearch:
    origin: str
    destination: str
    travel_date: str
    currency: str
    market: str
    language: str
    base_url: str


def build_public_availability_request(search: IberiaPublicAvailabilitySearch) -> dict[str, Any]:
    return {
        "slices": [{"origin": search.origin, "destination": search.destination, "date": search.travel_date}],
        "passengers": [{"passengerType": "ADULT", "count": 1}],
        "preferredCabin": _DEFAULT_CABIN,
    }


def extract_public_availability_flights(
    payload: Mapping[str, Any], search: IberiaPublicAvailabilitySearch
) -> list[ProviderFlight]:
    flights: list[ProviderFlight] = []
    seen: set[tuple[str | None, float, str]] = set()
    deeplink_url = build_public_booking_deeplink(search)
    for item in _walk_dicts(payload):
        if not _looks_like_offer(item):
            continue
        price = _extract_price(item, search.currency)
        if price is None:
            continue
        amount, currency = price
        departure_time = _extract_departure_time(item, search)
        dedupe_key = (departure_time, amount, currency)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        flights.append(
            ProviderFlight(
                price=amount,
                currency=currency,
                departure_time_local=departure_time,
                captured_at=utc_now_naive(),
                source=_PUBLIC_SOURCE,
                deeplink_url=deeplink_url,
            )
        )
    return flights


def build_public_booking_deeplink(search: IberiaPublicAvailabilitySearch) -> str:
    parsed_date = datetime.fromisoformat(search.travel_date)
    params = {
        "market": search.market,
        "language": search.language,
        "appliesOMB": "false",
        "splitEndCity": "false",
        "initializedOMB": "true",
        "flexible": "true",
        "TRIP_TYPE": "1",
        "BEGIN_CITY_01": search.origin,
        "END_CITY_01": search.destination,
        "BEGIN_DAY_01": f"{parsed_date.day:02d}",
        "BEGIN_MONTH_01": f"{parsed_date.year}{parsed_date.month:02d}",
        "BEGIN_YEAR_01": str(parsed_date.year),
        "END_DAY_01": "",
        "END_MONTH_01": "",
        "END_YEAR_01": "",
        "FARE_TYPE": "R",
        "quadrigam": "IBHMPA",
        "ADT": "1",
        "CHD": "0",
        "INF": "0",
        "residentCode": "",
        "familianumerosa": "",
        "BV_UseBVCookie": "no",
        "boton": "Buscar" if search.language == "es" else "Search",
        "bookingMarket": search.market,
    }
    return f"{search.base_url}/flights/?{urlencode(params)}"


def _looks_like_offer(item: Mapping[str, Any]) -> bool:
    keys = {str(key).lower() for key in item}
    return bool(
        {"totalprice", "total", "amount", "price", "fareprice", "totalamount"} & keys
        and {"offerid", "offeridnumber", "farefamily", "sliceoffers", "flights", "segments", "slices"} & keys
    )


def _extract_price(item: Mapping[str, Any], fallback_currency: str) -> tuple[float, str] | None:
    for candidate in _price_candidates(item):
        amount = _positive_float(
            candidate.get("amount")
            or candidate.get("total")
            or candidate.get("value")
            or candidate.get("price")
            or candidate.get("totalAmount")
        )
        if amount is None:
            continue
        currency = str(candidate.get("currency") or candidate.get("currencyCode") or fallback_currency).upper()
        return amount, currency
    amount = _positive_float(item.get("amount") or item.get("total") or item.get("price") or item.get("totalAmount"))
    if amount is None:
        return None
    currency = str(item.get("currency") or item.get("currencyCode") or fallback_currency).upper()
    return amount, currency


def _extract_departure_time(item: Mapping[str, Any], search: IberiaPublicAvailabilitySearch) -> str | None:
    for candidate in _walk_dicts(item):
        if not _matches_route(candidate, search):
            continue
        value = (
            candidate.get("departureDateTime")
            or candidate.get("departureTime")
            or candidate.get("departure")
            or candidate.get("dateTime")
        )
        time_value = _to_time(value)
        if time_value is not None:
            return time_value
    for key in ("departureDateTime", "departureTime", "departure", "dateTime"):
        time_value = _to_time(item.get(key))
        if time_value is not None:
            return time_value
    return None


def _matches_route(item: Mapping[str, Any], search: IberiaPublicAvailabilitySearch) -> bool:
    origin = _upper_str(item.get("origin") or item.get("originCode") or item.get("departureAirport"))
    destination = _upper_str(item.get("destination") or item.get("destinationCode") or item.get("arrivalAirport"))
    return (origin in ("", search.origin)) and (destination in ("", search.destination))


def _walk_dicts(value: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_dicts(item)


def _price_candidates(item: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    for key in ("totalPrice", "total", "price", "farePrice", "totalAmount"):
        value = item.get(key)
        if isinstance(value, Mapping):
            yield value


def _to_time(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%H:%M")
    except ValueError:
        return value[:5] if len(value) >= 5 and value[2] == ":" else None


def _positive_float(value: Any) -> float | None:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount if amount > 0.0 else None


def _upper_str(value: Any) -> str:
    return str(value or "").upper().strip()
