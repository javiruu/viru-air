from __future__ import annotations

import json
import math
import re
from datetime import date
from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit

from app.hotels.contracts import ProviderHotelRecord, ProviderRateRecord


_TOTAL_PRICE_TYPES = frozenset({"total", "total_stay", "total price", "total_price"})
_AVAILABLE = frozenset({"instock", "preorder", "limitedavailability"})
_SOLD_OUT = frozenset({"outofstock", "soldout", "discontinued"})
_MAX_JSON_LD_VALUES = 2_048
_NUMBER = re.compile(r"[+-]?(?:\d+\.\d+|\d+|\.\d+)")
_OPAQUE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


def hotel_records_from_document(
    *,
    document: str,
    check_in: date,
    check_out: date,
    guests: int,
) -> list[ProviderHotelRecord]:
    try:
        payload = json.loads(document)
    except (json.JSONDecodeError, RecursionError):
        return []
    records: list[ProviderHotelRecord] = []
    for node in _iter_nodes(payload):
        record = _hotel_record_from_node(node, check_in=check_in, check_out=check_out, guests=guests)
        if record is not None:
            records.append(record)
    return records


def _iter_nodes(value: object) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []
    pending = [value]
    values_seen = 0
    while pending:
        values_seen += 1
        if values_seen > _MAX_JSON_LD_VALUES:
            return []
        item = pending.pop()
        if isinstance(item, list):
            pending.extend(reversed(item))
        elif isinstance(item, dict):
            node = _mapping(item)
            nodes.append(node)
            pending.extend(reversed(list(node.values())))
    return nodes


def _hotel_record_from_node(
    node: dict[str, object],
    *,
    check_in: date,
    check_out: date,
    guests: int,
) -> ProviderHotelRecord | None:
    if not _is_hotel(node):
        return None
    name = _text(node.get("name"))
    address = _mapping(node.get("address"))
    city = _text(address.get("addressLocality"))
    country = _country_code(address.get("addressCountry"))
    if not name or not city or not country:
        return None
    identifier = _safe_provider_identifier(_text(node.get("@id")) or _text(node.get("url")))
    identifier = identifier or _stable_identifier(name, city, country)
    geo = _mapping(node.get("geo"))
    return ProviderHotelRecord(
        provider_hotel_id=identifier,
        raw_name=name,
        raw_address=_text(address.get("streetAddress")) or None,
        city=city,
        country_code=country,
        latitude=_coordinate(geo.get("latitude"), minimum=-90, maximum=90),
        longitude=_coordinate(geo.get("longitude"), minimum=-180, maximum=180),
        stars=_positive_int(_mapping(node.get("starRating")).get("ratingValue")),
        rates=_rates_from_offers(
            offers=node.get("makesOffer", node.get("offers")),
            check_in=check_in,
            check_out=check_out,
            guests=guests,
        ),
        raw_payload={"source": "local_html_json_ld", "identifier": identifier},
    )


def _rates_from_offers(
    *,
    offers: object,
    check_in: date,
    check_out: date,
    guests: int,
) -> list[ProviderRateRecord]:
    rates: list[ProviderRateRecord] = []
    for item in _items(offers):
        if not isinstance(item, dict):
            continue
        rate = _rate_from_offer(_mapping(item), check_in=check_in, check_out=check_out, guests=guests)
        if rate is not None:
            rates.append(rate)
    return rates


def _rate_from_offer(
    offer: dict[str, object],
    *,
    check_in: date,
    check_out: date,
    guests: int,
) -> ProviderRateRecord | None:
    amount = _number(offer.get("price"))
    currency = _text(offer.get("priceCurrency")).upper()
    if amount is None or not math.isfinite(amount) or amount <= 0 or not re.fullmatch(r"[A-Z]{3}", currency):
        return None
    description = _text(offer.get("description"))
    price_specification = _mapping(offer.get("priceSpecification"))
    is_total = _text(price_specification.get("priceType")).strip().lower() in _TOTAL_PRICE_TYPES
    conditions_complete = bool(description) and is_total
    return ProviderRateRecord(
        check_in=check_in,
        check_out=check_out,
        amount=amount,
        amount_total=amount if is_total else None,
        currency=currency,
        guests=guests,
        room_label=_text(offer.get("name")) or None,
        cancellation_policy=description or None,
        availability_status=_availability(offer.get("availability")),
        deep_link=_text(offer.get("url")) or None,
        provider_offer_id=_safe_provider_identifier(_text(offer.get("@id")) or _text(offer.get("sku"))) or None,
        price_semantics="total" if is_total else "unknown",
        conditions_completeness="complete" if conditions_complete else "partial",
    )


def _is_hotel(node: dict[str, object]) -> bool:
    return any(_text(value).strip().lower() in {"hotel", "lodgingbusiness"} for value in _items(node.get("@type")))


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _items(value: object) -> list[object]:
    return value if isinstance(value, list) else [value]


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    raw_value = value.strip() if isinstance(value, str) else str(value)
    if not _NUMBER.fullmatch(raw_value):
        return None
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None


def _coordinate(value: object, *, minimum: int, maximum: int) -> float | None:
    numeric = _number(value)
    if numeric is None or not math.isfinite(numeric) or not minimum <= numeric <= maximum:
        return None
    return numeric


def _positive_int(value: object) -> int | None:
    numeric = _number(value)
    return int(numeric) if numeric is not None and math.isfinite(numeric) and numeric > 0 else None


def _country_code(value: object) -> str:
    country = _text(value).upper()
    return country if re.fullmatch(r"[A-Z]{2}", country) else ""


def _availability(value: object) -> str:
    identifier = _text(value).rsplit("/", 1)[-1].replace("_", "").lower()
    if identifier in _AVAILABLE:
        return "limited" if identifier == "limitedavailability" else "available"
    if identifier in _SOLD_OUT:
        return "sold_out"
    return "unknown"


def _stable_identifier(name: str, city: str, country: str) -> str:
    digest = sha256(f"{name}|{city}|{country}".encode("utf-8")).hexdigest()[:20]
    return f"local-html-{digest}"


def _safe_provider_identifier(value: str) -> str:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return _opaque_identifier(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not hostname:
        return _opaque_identifier(value)
    if not (parsed.username or parsed.password or parsed.query or parsed.fragment):
        return value
    public_url = _public_url(parsed.scheme, hostname, port, parsed.path)
    digest = sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"{public_url}#local-html-{digest}"


def _opaque_identifier(value: str) -> str:
    if _OPAQUE_IDENTIFIER.fullmatch(value):
        return value
    return f"local-html-{sha256(value.encode('utf-8')).hexdigest()[:20]}" if value else ""


def _public_url(scheme: str, hostname: str, port: int | None, path: str) -> str:
    host = f"[{hostname}]" if ":" in hostname else hostname
    suffix = f":{port}" if port is not None else ""
    return urlunsplit((scheme, f"{host}{suffix}", path, "", ""))
