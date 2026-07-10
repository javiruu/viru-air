from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class ProviderPrice:
    price: float
    currency: str
    captured_at: datetime
    source: str = "ryanair-public"


@dataclass
class ProviderFlight:
    price: float
    currency: str
    departure_time_local: str | None
    captured_at: datetime
    source: str = "ryanair-public"
    provider: str | None = None
    origin_iata: str | None = None
    destination_iata: str | None = None
    travel_date: date | str | None = None
    deeplink_url: str | None = None
    carrier_code: str | None = None
    flight_number: str | None = None


@dataclass
class ProviderFetchResult:
    flights: list[ProviderFlight]
    warnings: list[str]
    warnings_structured: list["ProviderWarning"] | None = None


class ProviderSourceFetchError(Exception):
    def __init__(
        self,
        warning_codes: list[str],
        message: str,
        *,
        provider_id: str | None = None,
        severity: str = "error",
        meta: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.warning_codes = warning_codes
        self.provider_id = provider_id
        self.severity = severity
        self.meta = meta or {}


@dataclass(frozen=True)
class ProviderWarning:
    code: str
    provider: str
    severity: str = "warning"
    meta: dict[str, Any] | None = None
