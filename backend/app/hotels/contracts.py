from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class ProviderRateRecord:
    check_in: date
    check_out: date
    amount: float
    currency: str = "EUR"
    guests: int = 2
    room_label: str | None = None
    meal_plan: str | None = None
    cancellation_policy: str | None = None


@dataclass
class ProviderHotelRecord:
    provider_hotel_id: str
    raw_name: str
    raw_address: str | None
    city: str
    country_code: str
    latitude: float | None = None
    longitude: float | None = None
    stars: int | None = None
    rates: list[ProviderRateRecord] = field(default_factory=list)
    raw_payload: dict[str, Any] | None = None


class HotelProviderAdapter(ABC):
    provider_id: str

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_hotels(self) -> list[ProviderHotelRecord]:
        raise NotImplementedError

