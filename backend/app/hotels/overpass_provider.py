"""Bounded OpenStreetMap Overpass catalog provider for hotels.

The provider intentionally exposes only hotel catalogue data from one small,
operator-configured bounding box. It never claims price, availability, or
booking capabilities.
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from typing import Final, Literal, Protocol, assert_never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.hotels.contracts import HotelProviderAdapter, ProviderCapabilities, ProviderHotelRecord
from app.hotels.overpass_transport import HttpxOverpassTransport, OverpassRequestError

_MAX_RESULTS: Final = 100
_MAX_BBOX_SPAN: Final = 0.1
_MAX_HOTEL_NAME_LENGTH: Final = 160
_MAX_ADDRESS_LENGTH: Final = 180
_COUNTRY_CODE = re.compile(r"[A-Z]{2}")
_SENSITIVE_TEXT = re.compile(
    r"(?i)(?:https?://|www\.|mailto:|@|(?:token|api[_-]?key|secret|password)\s*[=:]|\+?\d[\d .()/-]{7,}\d)"
)


@dataclass(frozen=True, slots=True)
class OverpassCatalogConfig:
    south: float
    west: float
    north: float
    east: float
    city: str
    country_code: str
    user_agent: str


class OverpassConfigurationError(Exception):
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
        super().__init__(error_code)


class OverpassTransport(Protocol):
    def fetch(self, *, query: str, user_agent: str) -> bytes: ...


class _OverpassCenter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    lat: float | None = None
    lon: float | None = None


class _OverpassElement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    type: Literal["node", "way", "relation"]
    id: int
    lat: float | None = None
    lon: float | None = None
    center: _OverpassCenter | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class _OverpassResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    elements: list[_OverpassElement] = Field(max_length=_MAX_RESULTS)
    remark: str | None = None


class OverpassHotelProviderAdapter(HotelProviderAdapter):
    provider_id = "osm_overpass"

    def __init__(self, *, config: OverpassCatalogConfig, transport: OverpassTransport) -> None:
        self._config = config
        self._transport = transport

    @classmethod
    def from_environment(cls) -> OverpassHotelProviderAdapter:
        return cls(config=_config_from_environment(), transport=HttpxOverpassTransport())

    def is_enabled(self) -> bool:
        return True

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.provider_id,
            contract_version=self.contract_version,
            supports_catalog=True,
            supports_area_search=False,
            supports_hotel_rates=False,
            supports_direct_revalidation=False,
            supports_parameterized_occupancy=False,
            supports_multiple_rooms=False,
            supports_children_ages=False,
            supports_total_fees=False,
            supports_room_type=False,
            supports_meal_plan=False,
            supports_cancellation_policy=False,
            supports_availability_status=False,
            supports_partner_deeplink=False,
        )

    def fetch_hotels(self) -> list[ProviderHotelRecord]:
        response_bytes = self._transport.fetch(
            query=_overpass_query(self._config),
            user_agent=self._config.user_agent,
        )
        try:
            payload = _OverpassResponse.model_validate_json(response_bytes)
        except ValidationError as exc:
            raise OverpassRequestError("invalid_response") from exc
        if payload.remark is not None:
            raise OverpassRequestError("invalid_response")
        return [record for element in payload.elements if (record := _hotel_record(element, self._config))]


def _config_from_environment() -> OverpassCatalogConfig:
    south, west, north, east = _parse_bbox(os.getenv("HOTEL_OVERPASS_BBOX", ""))
    city = os.getenv("HOTEL_OVERPASS_CITY", "").strip()
    country_code = os.getenv("HOTEL_OVERPASS_COUNTRY_CODE", "").strip().upper()
    user_agent = os.getenv("HOTEL_OVERPASS_USER_AGENT", "").strip()
    if not city or len(city) > 120 or any(ord(character) < 32 for character in city):
        raise OverpassConfigurationError("hotel_overpass_city_invalid")
    if not _COUNTRY_CODE.fullmatch(country_code):
        raise OverpassConfigurationError("hotel_overpass_country_code_invalid")
    if not user_agent or len(user_agent) > 200 or any(ord(character) < 32 for character in user_agent):
        raise OverpassConfigurationError("hotel_overpass_user_agent_invalid")
    return OverpassCatalogConfig(
        south=south,
        west=west,
        north=north,
        east=east,
        city=city,
        country_code=country_code,
        user_agent=user_agent,
    )


def _parse_bbox(raw_bbox: str) -> tuple[float, float, float, float]:
    try:
        south, west, north, east = (float(value.strip()) for value in raw_bbox.split(","))
    except ValueError as exc:
        raise OverpassConfigurationError("hotel_overpass_bbox_invalid") from exc
    values = (south, west, north, east)
    if (
        len(raw_bbox.split(",")) != 4
        or not all(math.isfinite(value) for value in values)
        or not -90 <= south < north <= 90
        or not -180 <= west < east <= 180
    ):
        raise OverpassConfigurationError("hotel_overpass_bbox_invalid")
    if north - south > _MAX_BBOX_SPAN or east - west > _MAX_BBOX_SPAN:
        raise OverpassConfigurationError("hotel_overpass_bbox_too_large")
    return south, west, north, east


def _overpass_query(config: OverpassCatalogConfig) -> str:
    return (
        "[out:json][timeout:10];"
        f'nwr["tourism"="hotel"]({config.south},{config.west},{config.north},{config.east});'
        f"out center tags {_MAX_RESULTS};"
    )


def _hotel_record(element: _OverpassElement, config: OverpassCatalogConfig) -> ProviderHotelRecord | None:
    name = _safe_text(element.tags.get("name"), maximum_length=_MAX_HOTEL_NAME_LENGTH)
    if not name:
        return None
    latitude, longitude = _coordinates(element)
    return ProviderHotelRecord(
        provider_hotel_id=f"osm:{element.type}:{element.id}",
        raw_name=name,
        raw_address=_address(element.tags),
        city=config.city,
        country_code=config.country_code,
        latitude=latitude,
        longitude=longitude,
        stars=_stars(element.tags.get("stars")),
        rates=[],
        raw_payload={
            "source": "openstreetmap_overpass",
            "element_id": str(element.id),
            "element_type": element.type,
            "tourism": "hotel",
        },
    )


def _coordinates(element: _OverpassElement) -> tuple[float | None, float | None]:
    match element.type:
        case "node":
            return _coordinate(element.lat, minimum=-90, maximum=90), _coordinate(
                element.lon,
                minimum=-180,
                maximum=180,
            )
        case "way" | "relation":
            center = element.center
            return (
                _coordinate(center.lat if center else None, minimum=-90, maximum=90),
                _coordinate(center.lon if center else None, minimum=-180, maximum=180),
            )
        case unreachable:
            assert_never(unreachable)


def _coordinate(value: float | None, *, minimum: int, maximum: int) -> float | None:
    if value is None or not math.isfinite(value) or not minimum <= value <= maximum:
        return None
    return value


def _address(tags: dict[str, str]) -> str | None:
    street = _safe_text(tags.get("addr:street"), maximum_length=_MAX_ADDRESS_LENGTH)
    house_number = _safe_text(tags.get("addr:housenumber"), maximum_length=24)
    address = " ".join(value for value in (street, house_number) if value)
    return address or None


def _safe_text(value: str | None, *, maximum_length: int) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split())
    if not text or len(text) > maximum_length or _SENSITIVE_TEXT.search(text):
        return None
    return text


def _stars(value: str | None) -> int | None:
    if value is None or not value.isascii() or not value.isdigit():
        return None
    stars = int(value)
    return stars if 1 <= stars <= 5 else None
