from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Literal, Sequence


_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_MEAL_PLANS = frozenset({"RO", "BB", "HB", "FB", "AI", "UNKNOWN"})
_ROOM_TYPES = frozenset({"standard", "superior", "deluxe", "suite", "apartment", "other", "unknown"})
_CANCELLATION_TYPES = frozenset({"refundable", "non_refundable", "partially_refundable", "unknown"})
_COMPLETENESS = frozenset({"complete", "partial", "unknown"})
_AVAILABILITY = frozenset({"available", "sold_out", "limited", "unknown", "provider_error", "not_checked"})

OccupancySource = Literal["explicit", "legacy_inferred"]
PriceSemantics = Literal["base", "total", "unknown"]
SnapshotStatus = Literal[
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


def _require_currency(value: str) -> str:
    if not _CURRENCY_RE.fullmatch(value):
        raise ValueError("hotel_currency_invalid")
    return value


def _require_non_negative(value: Decimal | None, error_code: str) -> None:
    if value is not None and value < 0:
        raise ValueError(error_code)


def _fingerprint(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class OccupancyRoom:
    adults: int
    children_ages: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.adults, bool) or self.adults < 1:
            raise ValueError("hotel_occupancy_room_requires_adult")
        normalized_ages = tuple(sorted(self.children_ages))
        if any(isinstance(age, bool) or not isinstance(age, int) or age < 0 or age > 17 for age in normalized_ages):
            raise ValueError("hotel_occupancy_child_age_invalid")
        if normalized_ages != self.children_ages:
            object.__setattr__(self, "children_ages", normalized_ages)

    @classmethod
    def from_values(cls, *, adults: int, children_ages: Sequence[int] = ()) -> "OccupancyRoom":
        return cls(adults=adults, children_ages=tuple(children_ages))


@dataclass(frozen=True, slots=True)
class Occupancy:
    rooms: tuple[OccupancyRoom, ...]
    source: OccupancySource = "explicit"

    def __post_init__(self) -> None:
        if not self.rooms:
            raise ValueError("hotel_occupancy_requires_room")
        if self.source not in {"explicit", "legacy_inferred"}:
            raise ValueError("hotel_occupancy_source_invalid")

    @classmethod
    def from_rooms(cls, rooms: Sequence[OccupancyRoom], *, source: OccupancySource = "explicit") -> "Occupancy":
        return cls(rooms=tuple(rooms), source=source)

    @property
    def total_adults(self) -> int:
        return sum(room.adults for room in self.rooms)

    @property
    def total_children(self) -> int:
        return sum(len(room.children_ages) for room in self.rooms)

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "rooms": [
                {"adults": room.adults, "children_ages": list(room.children_ages)}
                for room in self.rooms
            ],
        }


@dataclass(frozen=True, slots=True)
class StayQuery:
    check_in: date
    check_out: date
    occupancy: Occupancy
    currency: str
    canonical_hotel_id: str | None = None
    area_key: str | None = None
    room_preferences: tuple[str, ...] = ()
    meal_preferences: tuple[str, ...] = ()
    cancellation_preferences: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.check_out <= self.check_in:
            raise ValueError("hotel_stay_dates_invalid")
        if not self.canonical_hotel_id and not self.area_key:
            raise ValueError("hotel_stay_target_required")
        _require_currency(self.currency)
        for preference_name in ("room_preferences", "meal_preferences", "cancellation_preferences"):
            raw_values = getattr(self, preference_name)
            normalized = tuple(sorted({value.strip().lower() for value in raw_values if value.strip()}))
            if normalized != raw_values:
                object.__setattr__(self, preference_name, normalized)

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "canonical_hotel_id": self.canonical_hotel_id,
            "area_key": self.area_key,
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat(),
            "occupancy": self.occupancy.fingerprint_payload(),
            "currency": self.currency,
            "room_preferences": list(self.room_preferences),
            "meal_preferences": list(self.meal_preferences),
            "cancellation_preferences": list(self.cancellation_preferences),
        }

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.fingerprint_payload())


@dataclass(frozen=True, slots=True)
class RoomSignature:
    provider_room_id: str | None = None
    room_type_normalized: str = "unknown"
    room_count: int = 1
    room_label_raw: str | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.room_type_normalized not in _ROOM_TYPES:
            raise ValueError("hotel_room_type_invalid")
        if isinstance(self.room_count, bool) or self.room_count < 1:
            raise ValueError("hotel_room_count_invalid")

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "provider_room_id": self.provider_room_id,
            "room_type_normalized": self.room_type_normalized,
            "room_count": self.room_count,
        }


@dataclass(frozen=True, slots=True)
class CancellationPolicy:
    cancellation_type: str = "unknown"
    conditions_completeness: str = "unknown"
    free_until: datetime | None = None
    penalty_amount: Decimal | None = None
    penalty_currency: str | None = None
    policy_text_raw: str | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.cancellation_type not in _CANCELLATION_TYPES:
            raise ValueError("hotel_cancellation_type_invalid")
        if self.conditions_completeness not in _COMPLETENESS:
            raise ValueError("hotel_conditions_completeness_invalid")
        _require_non_negative(self.penalty_amount, "hotel_cancellation_penalty_invalid")
        if self.penalty_amount is not None and self.penalty_currency is None:
            raise ValueError("hotel_cancellation_penalty_currency_required")
        if self.penalty_currency is not None:
            _require_currency(self.penalty_currency)

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "cancellation_type": self.cancellation_type,
            "conditions_completeness": self.conditions_completeness,
            "free_until": self.free_until.isoformat() if self.free_until else None,
            "penalty_amount": str(self.penalty_amount) if self.penalty_amount is not None else None,
            "penalty_currency": self.penalty_currency,
        }


@dataclass(frozen=True, slots=True)
class FeeLine:
    fee_code: str
    amount: Decimal | None
    currency: str | None
    scope: Literal["per_stay", "per_night", "per_room", "per_guest", "percentage", "unknown"] = "unknown"
    status: Literal["included", "excluded", "estimated", "unknown", "not_applicable"] = "unknown"
    mandatory: bool | None = None
    label_raw: str | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        _require_non_negative(self.amount, "hotel_fee_amount_invalid")
        if self.amount is not None and self.currency is None:
            raise ValueError("hotel_fee_currency_required")
        if self.currency is not None:
            _require_currency(self.currency)


@dataclass(frozen=True, slots=True)
class FeeBreakdown:
    currency: str
    semantics: PriceSemantics = "unknown"
    amount_base: Decimal | None = None
    amount_total: Decimal | None = None
    fees: tuple[FeeLine, ...] = ()
    conditions_completeness: str = "unknown"

    def __post_init__(self) -> None:
        _require_currency(self.currency)
        _require_non_negative(self.amount_base, "hotel_base_amount_invalid")
        _require_non_negative(self.amount_total, "hotel_total_amount_invalid")
        if self.semantics not in {"base", "total", "unknown"}:
            raise ValueError("hotel_price_semantics_invalid")
        if self.conditions_completeness not in _COMPLETENESS:
            raise ValueError("hotel_conditions_completeness_invalid")
        if self.semantics == "total" and self.amount_total is None:
            raise ValueError("hotel_total_amount_required")
        if self.semantics != "total" and self.amount_total is not None:
            raise ValueError("hotel_total_amount_semantics_invalid")
        if any(line.currency not in {None, self.currency} for line in self.fees):
            raise ValueError("hotel_fee_currency_mismatch")

    @property
    def is_total_comparable(self) -> bool:
        return self.semantics == "total" and self.amount_total is not None and self.conditions_completeness == "complete"

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "currency": self.currency,
            "semantics": self.semantics,
            "conditions_completeness": self.conditions_completeness,
            "fees": [
                {
                    "fee_code": line.fee_code,
                    "scope": line.scope,
                    "status": line.status,
                    "mandatory": line.mandatory,
                }
                for line in self.fees
            ],
        }


@dataclass(frozen=True, slots=True)
class OfferIdentity:
    provider_id: str
    provider_hotel_id: str
    stay_query: StayQuery
    room: RoomSignature = field(default_factory=RoomSignature)
    meal_plan_normalized: str = "UNKNOWN"
    cancellation: CancellationPolicy = field(default_factory=CancellationPolicy)
    fees: FeeBreakdown | None = None
    provider_offer_id: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_id or not self.provider_hotel_id:
            raise ValueError("hotel_provider_identity_required")
        if self.meal_plan_normalized not in _MEAL_PLANS:
            raise ValueError("hotel_meal_plan_invalid")
        if self.fees is not None and self.fees.currency != self.stay_query.currency:
            raise ValueError("hotel_offer_currency_mismatch")

    @property
    def fingerprint(self) -> str:
        return _fingerprint(
            {
                "provider_id": self.provider_id,
                "provider_hotel_id": self.provider_hotel_id,
                "stay_query_fingerprint": self.stay_query.fingerprint,
                "provider_offer_id": self.provider_offer_id,
                "room": self.room.fingerprint_payload(),
                "meal_plan_normalized": self.meal_plan_normalized,
                "cancellation": self.cancellation.fingerprint_payload(),
                "fees": self.fees.fingerprint_payload() if self.fees else None,
            }
        )


@dataclass(frozen=True, slots=True)
class SnapshotOutcome:
    status: SnapshotStatus
    availability_status: str = "unknown"
    replay: bool = False

    def __post_init__(self) -> None:
        if self.availability_status not in _AVAILABILITY:
            raise ValueError("hotel_availability_status_invalid")
        if self.status == "success" and self.availability_status == "provider_error":
            raise ValueError("hotel_success_provider_error_invalid")

    @property
    def is_price_eligible(self) -> bool:
        return self.status in {"success", "partial"} and self.availability_status in {"available", "limited"} and not self.replay


def stay_query_from_legacy(
    *,
    canonical_hotel_id: str | None,
    area_key: str | None,
    check_in: date,
    check_out: date,
    guests: int,
    currency: str = "EUR",
) -> StayQuery:
    occupancy = Occupancy.from_rooms(
        (OccupancyRoom(adults=guests),),
        source="legacy_inferred",
    )
    return StayQuery(
        canonical_hotel_id=canonical_hotel_id,
        area_key=area_key,
        check_in=check_in,
        check_out=check_out,
        occupancy=occupancy,
        currency=currency,
    )
