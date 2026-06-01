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
    provider: str
    check_in: Date
    check_out: Date
    guests: int
    room_label: str | None = None
    meal_plan: str | None = None
    cancellation_policy: str | None = None
    currency: str
    amount: float
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


HotelAlertRuleType = Literal["price_below", "price_above", "parity_break"]


class HotelAlertRuleCreateIn(BaseModel):
    hotel_id: str
    rule_type: HotelAlertRuleType
    threshold_amount: float | None = Field(default=None, ge=0)
    threshold_percent: float | None = Field(default=None, ge=0, le=100)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_threshold_combination(self):
        if self.rule_type in {"price_below", "price_above"}:
            if self.threshold_amount is None and self.threshold_percent is None:
                raise ValueError("threshold_required_for_price_rule")
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
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_threshold_combination(self):
        effective_type = self.rule_type
        if effective_type is None:
            return self
        if effective_type in {"price_below", "price_above"}:
            if self.threshold_amount is None and self.threshold_percent is None:
                raise ValueError("threshold_required_for_price_rule")
        if effective_type == "parity_break":
            if self.threshold_percent is None:
                raise ValueError("threshold_percent_required_for_parity_break")
            if self.threshold_amount is not None:
                raise ValueError("threshold_amount_not_allowed_for_parity_break")
        return self


class HotelAlertRuleOut(BaseModel):
    id: str
    hotel_id: str
    rule_type: HotelAlertRuleType
    threshold_amount: float | None = None
    threshold_percent: float | None = None
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


class HotelRatesQueryIn(BaseModel):
    check_in: Date | None = None
    check_out: Date | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValueError("invalid_date_range")
        return self
