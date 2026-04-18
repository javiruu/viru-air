from dataclasses import dataclass
from datetime import datetime


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


@dataclass
class ProviderFetchResult:
    flights: list[ProviderFlight]
    warnings: list[str]


class ProviderSourceFetchError(Exception):
    def __init__(self, warning_codes: list[str], message: str) -> None:
        super().__init__(message)
        self.warning_codes = warning_codes
