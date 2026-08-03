from __future__ import annotations

from datetime import date as Date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class HotelSearchOut(BaseModel):
    id: str
    canonical_name: str
    city: str
    country_code: str
    stars: int | None = None


class HotelDetailOut(HotelSearchOut):
    normalized_name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime
    updated_at: datetime


class HotelRateOut(BaseModel):
    id: str
    hotel_id: str
    tracked_offer_id: str | None = None
    provider_run_id: str | None = None
    provider: str
    check_in: Date
    check_out: Date
    guests: int
    room_label: str | None = None
    meal_plan: str | None = None
    cancellation_policy: str | None = None
    currency: str
    amount: float
    availability_status: str = "available"
    deep_link: str | None = None
    collected_at: datetime


class HotelWatchlistItemCreateIn(BaseModel):
    hotel_id: str
    label: str | None = Field(default=None, max_length=80)


class HotelWatchlistItemOut(BaseModel):
    id: str
    hotel_id: str
    label: str | None = None
    created_at: datetime


class HotelCompSetCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    anchor_hotel_id: str


class HotelCompSetOut(BaseModel):
    id: str
    name: str
    anchor_hotel_id: str
    created_at: datetime


class HotelCompSetMemberCreateIn(BaseModel):
    hotel_id: str


class HotelCompSetMemberOut(BaseModel):
    id: str
    comp_set_id: str
    hotel_id: str


class HotelCompSetDetailOut(BaseModel):
    id: str
    name: str
    anchor_hotel_id: str
    created_at: datetime
    members: list[HotelCompSetMemberOut]


class HotelNearbySuggestionOut(BaseModel):
    hotel_id: str
    canonical_name: str
    city: str
    country_code: str
    stars: int | None = None
    distance_km: float


HotelAlertRuleType = Literal["price_below", "price_above", "percentage_drop", "percentage_increase", "provider_changed", "availability_returned", "parity_break"]


class HotelAlertRuleCreateIn(BaseModel):
    hotel_id: str
    tracked_offer_id: str | None = None
    rule_type: HotelAlertRuleType
    threshold_amount: float | None = Field(default=None, ge=0)
    threshold_percent: float | None = Field(default=None, ge=0, le=100)
    compare_against: str = Field(default="snapshot_previous", max_length=20)
    is_active: bool = True

    @field_validator("compare_against")
    @classmethod
    def validate_compare_against(cls, value: str) -> str:
        if value not in {"snapshot_previous", "initial_price"}:
            raise ValueError("invalid_compare_against")
        return value

    @model_validator(mode="after")
    def validate_threshold_combination(self):
        if self.rule_type in {"price_below", "price_above"} and self.threshold_amount is None and self.threshold_percent is None:
            raise ValueError("threshold_required_for_price_rule")
        if self.rule_type in {"percentage_drop", "percentage_increase"}:
            if self.threshold_percent is None:
                raise ValueError("threshold_percent_required_for_percentage_rule")
            if self.threshold_amount is not None:
                raise ValueError("threshold_amount_not_allowed_for_percentage_rule")
        if self.rule_type == "parity_break":
            if self.threshold_percent is None:
                raise ValueError("threshold_percent_required_for_parity_break")
            if self.threshold_amount is not None:
                raise ValueError("threshold_amount_not_allowed_for_parity_break")
        return self


class HotelAlertRuleUpdateIn(BaseModel):
    rule_type: HotelAlertRuleType | None = None
    threshold_amount: float | None = Field(default=None, ge=0)
    threshold_percent: float | None = Field(default=None, ge=0, le=100)
    compare_against: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None

    @field_validator("compare_against")
    @classmethod
    def validate_compare_against(cls, value: str | None) -> str | None:
        if value is not None and value not in {"snapshot_previous", "initial_price"}:
            raise ValueError("invalid_compare_against")
        return value

    @model_validator(mode="after")
    def validate_threshold_combination(self):
        effective_type = self.rule_type
        if effective_type is None:
            return self
        if effective_type in {"price_below", "price_above"} and self.threshold_amount is None and self.threshold_percent is None:
            raise ValueError("threshold_required_for_price_rule")
        if effective_type in {"percentage_drop", "percentage_increase"}:
            if self.threshold_percent is None:
                raise ValueError("threshold_percent_required_for_percentage_rule")
            if self.threshold_amount is not None:
                raise ValueError("threshold_amount_not_allowed_for_percentage_rule")
        if effective_type == "parity_break":
            if self.threshold_percent is None:
                raise ValueError("threshold_percent_required_for_parity_break")
            if self.threshold_amount is not None:
                raise ValueError("threshold_amount_not_allowed_for_parity_break")
        return self


class HotelAlertRuleOut(BaseModel):
    id: str
    hotel_id: str
    tracked_offer_id: str | None = None
    rule_type: HotelAlertRuleType
    threshold_amount: float | None = None
    threshold_percent: float | None = None
    compare_against: str = "snapshot_previous"
    is_active: bool


class HotelIngestOut(BaseModel):
    provider_id: str
    hotels_processed: int
    rates_ingested: int
    ambiguous_matches: int


class HotelParityOut(BaseModel):
    check_in: Date
    check_out: Date
    guests: int
    currency: str
    provider_count: int
    lowest_price: float | None = None
    highest_price: float | None = None
    average_price: float | None = None
    spread_amount: float | None = None
    spread_percent: float | None = None
    is_parity_broken: bool = False
    status: str
    label: str


class HotelProviderRunOut(BaseModel):
    id: str
    provider: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    items_processed: int
    error_message: str | None = None


class HotelAlertEventOut(BaseModel):
    id: str
    rule_id: str | None = None
    hotel_id: str
    provider_run_id: str | None = None
    event_type: str
    message: str
    trigger_value: float | None = None
    created_at: datetime


class HotelSearchQueryIn(BaseModel):
    q: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=100)
    country_code: str | None = Field(default=None, max_length=2)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if len(cleaned) != 2 or not cleaned.isalpha():
            raise ValueError("invalid_country_code")
        return cleaned


class HotelTrackedOfferCreateIn(BaseModel):
    hotel_id: str
    area_label: str | None = Field(default=None, max_length=200)
    origin_query: str | None = Field(default=None, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: int | None = Field(default=None, ge=0)
    check_in: Date | None = None
    check_out: Date | None = None
    guests: int = Field(default=2, ge=1, le=20)
    room_label: str | None = Field(default=None, max_length=160)
    meal_plan: str | None = Field(default=None, max_length=80)
    cancellation_policy: str | None = Field(default=None, max_length=120)
    provider: str = Field(default="mock", max_length=40)
    initial_price: float | None = Field(default=None, ge=0)
    current_price: float | None = Field(default=None, ge=0)
    target_price: float | None = Field(default=None, ge=0)
    currency: str = Field(default="EUR", max_length=3)

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValueError("invalid_date_range")
        return self


class HotelTrackedOfferUpdateIn(BaseModel):
    area_label: str | None = Field(default=None, max_length=200)
    origin_query: str | None = Field(default=None, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: int | None = Field(default=None, ge=0)
    check_in: Date | None = None
    check_out: Date | None = None
    guests: int | None = Field(default=None, ge=1, le=20)
    room_label: str | None = Field(default=None, max_length=160)
    meal_plan: str | None = Field(default=None, max_length=80)
    cancellation_policy: str | None = Field(default=None, max_length=120)
    provider: str | None = Field(default=None, max_length=40)
    initial_price: float | None = Field(default=None, ge=0)
    current_price: float | None = Field(default=None, ge=0)
    target_price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=3)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        check_in = self.check_in
        check_out = self.check_out
        if check_in and check_out and check_out <= check_in:
            raise ValueError("invalid_date_range")
        return self


class HotelTrackedOfferOut(BaseModel):
    id: str
    user_id: str
    hotel_id: str
    area_label: str | None = None
    origin_query: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_km: int | None = None
    check_in: Date | None = None
    check_out: Date | None = None
    guests: int
    room_label: str | None = None
    meal_plan: str | None = None
    cancellation_policy: str | None = None
    provider: str
    initial_price: float | None = None
    current_price: float | None = None
    target_price: float | None = None
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class HotelRatesQueryIn(BaseModel):
    check_in: Date | None = None
    check_out: Date | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValueError("invalid_date_range")
        return self


class HotelAreaSearchQueryIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: int = Field(default=5, ge=1, le=50)
    check_in: Date
    check_out: Date
    guests: int = Field(default=2, ge=1, le=20)
    currency: str = Field(default="EUR", max_length=3)
    min_stars: int | None = Field(default=None, ge=1, le=5)
    max_price: float | None = Field(default=None, ge=0)
    sort: str = Field(default="price", max_length=10)

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"price", "distance", "stars"}:
            raise ValueError("invalid_sort_value")
        return cleaned

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.check_out <= self.check_in:
            raise ValueError("invalid_date_range")
        return self


class HotelAreaResolveQueryIn(BaseModel):
    q: str = Field(min_length=1, max_length=120)


class HotelAreaResolveOut(BaseModel):
    area_label: str
    latitude: float
    longitude: float
    country_code: str
    confidence: str
    source: str


class HotelAreaSearchResultOut(BaseModel):
    hotel_id: str
    canonical_name: str
    city: str
    country_code: str
    stars: int | None = None
    distance_km: float
    lowest_price: float | None = None
    currency: str = "EUR"
    provider: str | None = None
    check_in: Date
    check_out: Date
    guests: int
    has_tracking: bool = False
