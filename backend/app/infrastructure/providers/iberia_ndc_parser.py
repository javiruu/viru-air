from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import xml.etree.ElementTree as ET

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight


@dataclass(frozen=True, slots=True)
class IberiaAirShoppingQuery:
    origin: str
    destination: str
    travel_date: str
    currency: str


@dataclass(frozen=True, slots=True)
class _IberiaSegment:
    segment_id: str
    origin: str
    destination: str
    departure_time_local: str | None
    departure_date: str | None


def parse_air_shopping_flights(
    root: ET.Element, search: IberiaAirShoppingQuery, *, booking_base_url: str
) -> list[ProviderFlight]:
    segments = _extract_segments(root)
    flights: list[ProviderFlight] = []
    for offer in _iter_children_by_local_name(root, "Offer"):
        price = _price_from_offer(offer)
        if price is None:
            continue
        segment = _matching_segment(offer, segments, search)
        if segment is None:
            continue
        flights.append(
            ProviderFlight(
                price=price[0],
                currency=price[1] or search.currency,
                departure_time_local=segment.departure_time_local,
                captured_at=utc_now_naive(),
                source="iberia-ndc-airshopping",
                deeplink_url=booking_base_url,
            )
        )
    return flights


def _extract_segments(root: ET.Element) -> dict[str, _IberiaSegment]:
    segments: dict[str, _IberiaSegment] = {}
    for segment in _iter_children_by_local_name(root, "FlightSegment"):
        segment_id = (
            segment.attrib.get("SegmentKey")
            or segment.attrib.get("FlightSegmentID")
            or segment.attrib.get("SegmentID")
            or segment.attrib.get("refs")
            or ""
        ).strip()
        origin = _first_text(segment, ("Departure", "AirportCode"))
        destination = _first_text(segment, ("Arrival", "AirportCode"))
        departure_raw = _first_text(segment, ("Departure", "DateTime"))
        departure_date = _first_text(segment, ("Departure", "Date"))
        if departure_raw:
            departure_date = _to_iso_date(departure_raw)
        if not segment_id or not origin or not destination:
            continue
        segments[segment_id] = _IberiaSegment(
            segment_id=segment_id,
            origin=origin.upper(),
            destination=destination.upper(),
            departure_time_local=_to_time(departure_raw),
            departure_date=departure_date,
        )
    return segments


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_children_by_local_name(root: ET.Element, local_name: str) -> list[ET.Element]:
    return [item for item in root.iter() if _local_name(item.tag) == local_name]


def _first_child(element: ET.Element, local_name: str) -> ET.Element | None:
    for child in element:
        if _local_name(child.tag) == local_name:
            return child
    return None


def _first_text(element: ET.Element, path: tuple[str, ...]) -> str | None:
    current: ET.Element | None = element
    for local_name in path:
        if current is None:
            return None
        current = _first_child(current, local_name)
    if current is None or current.text is None:
        return None
    value = current.text.strip()
    return value or None


def _price_from_offer(offer: ET.Element) -> tuple[float, str | None] | None:
    for item in offer.iter():
        if _local_name(item.tag) not in {"TotalAmount", "SimpleCurrencyPrice", "Total"}:
            continue
        if item.text is None:
            continue
        try:
            amount = float(item.text.strip())
        except ValueError:
            continue
        if amount <= 0:
            continue
        currency = item.attrib.get("Code") or item.attrib.get("CurCode") or item.attrib.get("CurrencyCode")
        return amount, currency.upper() if currency else None
    return None


def _matching_segment(
    offer: ET.Element, segments: dict[str, _IberiaSegment], search: IberiaAirShoppingQuery
) -> _IberiaSegment | None:
    refs = _offer_refs(offer)
    for ref in refs:
        segment = segments.get(ref)
        if segment is None:
            continue
        if segment.origin != search.origin or segment.destination != search.destination:
            continue
        if segment.departure_date is not None and segment.departure_date != search.travel_date:
            continue
        return segment
    for segment in segments.values():
        if segment.origin == search.origin and segment.destination == search.destination:
            if segment.departure_date is None or segment.departure_date == search.travel_date:
                return segment
    return None


def _offer_refs(offer: ET.Element) -> list[str]:
    refs: list[str] = []
    for item in offer.iter():
        for attr_name in ("refs", "SegmentReferences", "FlightSegmentReference", "SegmentKey"):
            attr_value = item.attrib.get(attr_name)
            if attr_value:
                refs.extend(part.strip() for part in attr_value.split() if part.strip())
        if _local_name(item.tag) in {"FlightRefs", "FlightSegmentReference", "SegmentReference"} and item.text:
            refs.extend(part.strip() for part in item.text.split() if part.strip())
    return refs


def _to_iso_date(value: str) -> str | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _to_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%H:%M")
    except ValueError:
        return None
