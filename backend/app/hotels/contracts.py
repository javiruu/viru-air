from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Generic, Literal, TypeVar


ProviderResultStatus = Literal[
    "success",
    "empty",
    "partial",
    "unsupported",
    "rate_limited",
    "timeout",
    "unavailable",
    "invalid_response",
    "failed",
]
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    provider_id: str
    contract_version: str = "hotel-provider-v2"
    supports_catalog: bool | None = None
    supports_area_search: bool | None = None
    supports_hotel_rates: bool | None = None
    supports_direct_revalidation: bool | None = None
    supports_parameterized_occupancy: bool | None = None
    supports_multiple_rooms: bool | None = None
    supports_children_ages: bool | None = None
    supports_total_fees: bool | None = None
    supports_room_type: bool | None = None
    supports_meal_plan: bool | None = None
    supports_cancellation_policy: bool | None = None
    supports_availability_status: bool | None = None
    supports_partner_deeplink: bool | None = None


@dataclass(frozen=True, slots=True)
class ProviderWarning:
    code: str
    severity: Literal["info", "warning", "error"] = "warning"
    retryable: bool = False
    scope: Literal["operation", "item"] = "operation"


@dataclass(frozen=True, slots=True)
class ProviderError:
    code: str
    category: Literal["configuration", "security", "client", "capability", "domain", "network", "provider", "contract", "unknown"]
    retryable: bool = False
    http_status: int | None = None
    retry_after_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderResult(Generic[T]):
    provider_id: str
    operation: str
    request_id: str
    status: ProviderResultStatus
    items: tuple[T, ...] = ()
    item_errors: tuple[ProviderError, ...] = ()
    warnings: tuple[ProviderWarning, ...] = ()
    error: ProviderError | None = None
    contract_version: str = "hotel-provider-v2"

    def __post_init__(self) -> None:
        if not self.provider_id or not self.operation or not self.request_id:
            raise ValueError("hotel_provider_result_identity_required")
        if self.status in {"success", "empty"} and self.error is not None:
            raise ValueError("hotel_provider_result_fatal_error_invalid")
        if self.status == "empty" and self.items:
            raise ValueError("hotel_provider_result_empty_items_invalid")
        if self.status == "partial" and not self.items and not self.item_errors:
            raise ValueError("hotel_provider_result_partial_evidence_required")
        if self.status in {"unsupported", "rate_limited", "timeout", "unavailable", "invalid_response", "failed"} and self.error is None:
            raise ValueError("hotel_provider_result_error_required")

    @property
    def is_usable(self) -> bool:
        return self.status in {"success", "partial", "empty"}


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
    availability_status: str = "available"
    deep_link: str | None = None
    provider_offer_id: str | None = None
    room_type_normalized: str = "unknown"
    meal_plan_normalized: str = "UNKNOWN"
    cancellation_type: str = "unknown"
    price_semantics: Literal["base", "total", "unknown"] = "unknown"
    amount_total: float | None = None
    conditions_completeness: Literal["complete", "partial", "unknown"] = "unknown"


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
    contract_version = "hotel-provider-v1"

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_hotels(self) -> list[ProviderHotelRecord]:
        raise NotImplementedError

    def fetch_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int = 2,
        currency: str = "EUR",
    ) -> list[ProviderRateRecord]:
        """Optional: fetch rates for a specific hotel with search parameters.

        Providers that support parameterized search (e.g. Makcorps with date/guest filters)
        should override this method. The default implementation returns an empty list,
        which means the sweep will fall back to reusing unlinked snapshots from the
        general ingestion pool.
        """
        return []

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.provider_id,
            contract_version=self.contract_version,
        )

