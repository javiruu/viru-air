from __future__ import annotations

import json
from datetime import date as Date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class HotelSavedSearchCreateIn(BaseModel):
    schema_version: Literal["hotel-search-v1"] = "hotel-search-v1"
    query: dict[str, Any]
    label: str | None = Field(default=None, max_length=120)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: dict[str, Any]) -> dict[str, Any]:
        allowed_params = {
            "mode", "q", "city", "area", "area_lat", "area_lng", "area_country",
            "area_confidence", "area_source", "check_in", "check_out", "guests", "radius", "provider",
        }
        if set(value) != {"schema", "params"} or value.get("schema") != "hotel-search-v1":
            raise ValueError("invalid_saved_search_query")
        params = value.get("params")
        if not isinstance(params, dict) or not params or set(params) - allowed_params:
            raise ValueError("invalid_saved_search_query")
        if any(not isinstance(key, str) or not isinstance(param_value, str) for key, param_value in params.items()):
            raise ValueError("invalid_saved_search_query")
        try:
            if len(json.dumps(value, ensure_ascii=False)) > 8_000:
                raise ValueError("invalid_saved_search_query")
        except (TypeError, ValueError) as exc:
            if str(exc) == "invalid_saved_search_query":
                raise
            raise ValueError("invalid_saved_search_query") from exc
        return value


class HotelSavedSearchUpdateIn(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    status: Literal["active", "paused"] | None = None


class HotelSavedSearchOut(BaseModel):
    id: str
    user_id: str
    schema_version: str
    fingerprint: str
    query: dict[str, Any]
    label: str | None = None
    status: Literal["active", "paused"]
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None


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
    cooldown_minutes: int = Field(default=60, ge=1, le=10080)
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
    cooldown_minutes: int | None = Field(default=None, ge=1, le=10080)
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
    cooldown_minutes: int = 60
    evaluation_state: str = "clear"
    last_fired_at: datetime | None = None
    is_active: bool


class HotelIngestOut(BaseModel):
    provider_id: str
    hotels_processed: int
    rates_ingested: int
    ambiguous_matches: int
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    needs_review: bool = False
    provider_run_id: str | None = None


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
    correlation_id: str | None = None
    client_event_id: str | None = None
    execution_id: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    items_processed: int
    error_message: str | None = None
    tracked_outcomes: dict[str, Any] | None = None


class HotelAlertEventOut(BaseModel):
    id: str
    rule_id: str | None = None
    hotel_id: str
    provider_run_id: str | None = None
    event_type: str
    message: str
    trigger_value: float | None = None
    event_fingerprint: str | None = None
    snapshot_before_id: str | None = None
    snapshot_after_id: str | None = None
    baseline_snapshot_id: str | None = None
    baseline_source: str | None = None
    baseline_amount: float | None = None
    baseline_currency: str | None = None
    comparability_key: str | None = None
    reason_code: str | None = None
    eligibility_status: str | None = None
    rule_version: str | None = None
    evaluation_state: str | None = None
    cooldown_until: datetime | None = None
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


HotelV2CapabilityState = Literal[
    "supported",
    "supported_with_caveat",
    "partial",
    "planned",
    "unavailable",
]


class HotelV2PriceOut(BaseModel):
    amount: float | None = None
    currency: str
    basis: Literal["total_stay", "per_night", "unknown"] = "unknown"
    status: Literal["observed", "unavailable", "not_comparable", "stale"]
    observed_at: datetime | None = None


class HotelV2StayContextOut(BaseModel):
    check_in: Date
    check_out: Date
    guests: int
    rooms: int | None = None


class HotelV2ResultExplanationOut(BaseModel):
    primary_reason: str
    codes: list[str]


class HotelV2AreaSearchResultOut(BaseModel):
    hotel_id: str
    canonical_name: str
    city: str
    country_code: str
    stars: int | None = None
    distance_km: float
    price: HotelV2PriceOut
    stay_context: HotelV2StayContextOut
    provider: str | None = None
    has_tracking: bool = False
    explanation: HotelV2ResultExplanationOut


class HotelV2WarningOut(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message_key: str
    provider: str | None = None
    scope: Literal["collection", "result", "field"] = "collection"
    result_ids: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class HotelV2ProviderOut(BaseModel):
    id: str
    operation: str
    status: Literal[
        "ok",
        "empty",
        "timeout",
        "rate_limited",
        "disabled",
        "failed",
        "not_configured",
    ]
    results_count: int = 0
    used_for_results: bool = False
    fallback_used: bool = False
    latency_ms: int | None = None


class HotelV2FreshnessOut(BaseModel):
    state: Literal["fresh", "recent", "cached", "historical", "stale", "expired", "unknown"] = "unknown"
    observed_at: datetime | None = None
    age_seconds: int | None = None
    expires_at: datetime | None = None
    mixed: bool = False
    requires_revalidation: bool = False
    policy_version: str | None = None
    provenance_kind: Literal[
        "provider_observed",
        "provider_revalidated",
        "cache_current",
        "historical_snapshot",
        "fixture_demo",
        "derived",
        "unknown",
    ] = "unknown"


class HotelV2PaginationOut(BaseModel):
    mode: Literal["none"] = "none"
    returned: int
    total: int
    has_next: bool = False
    next_cursor: str | None = None
    previous_cursor: str | None = None
    sort: str


class HotelV2ResultsMetaOut(BaseModel):
    contract_version: Literal["hotels.results.v2"] = "hotels.results.v2"
    request_id: str
    generated_at: str
    result_state: Literal["success", "empty", "partial"]
    query: dict[str, Any]
    pagination: HotelV2PaginationOut
    freshness: HotelV2FreshnessOut
    providers: list[HotelV2ProviderOut] = Field(default_factory=list)
    capabilities: dict[str, dict[str, HotelV2CapabilityState]]
    warnings: list[HotelV2WarningOut] = Field(default_factory=list)


class HotelV2AreaSearchOut(BaseModel):
    data: list[HotelV2AreaSearchResultOut]
    meta: HotelV2ResultsMetaOut


class HotelV2TrackingStayContextOut(BaseModel):
    check_in: Date | None = None
    check_out: Date | None = None
    guests: int
    currency: str


class HotelV2TrackingObservationOut(BaseModel):
    snapshot_id: str
    legacy_collected_at: datetime
    observed_at: datetime | None = None
    provider: str
    room_label: str | None = None
    meal_plan: str | None = None
    cancellation_policy: str | None = None
    availability_status: str
    conditions_completeness: str | None = None
    price: HotelV2PriceOut
    canonical_stay_offer_id: str | None = None
    freshness: HotelV2FreshnessOut


class HotelV2HistoryIdentityOut(BaseModel):
    comparability_key: str | None = None
    status: Literal["comparable", "legacy_comparison", "not_comparable"]
    check_in: Date | None = None
    check_out: Date | None = None
    guests: int
    currency: str
    provider_scope: str | None = None


class HotelV2HistoryPointOut(BaseModel):
    snapshot_id: str
    observed_at: datetime
    observation_time_source: Literal["provider_observed", "legacy_collected"]
    provider: str
    availability_status: str
    conditions_completeness: str | None = None
    canonical_stay_offer_id: str | None = None
    price_semantics: Literal["total", "unknown"]
    price: HotelV2PriceOut
    eligibility: Literal["eligible", "excluded"]
    excluded_reason: str | None = None


class HotelV2HistorySeriesOut(BaseModel):
    identity: HotelV2HistoryIdentityOut
    points: list[HotelV2HistoryPointOut] = Field(default_factory=list)
    gaps: list[dict[str, Any]] = Field(default_factory=list)
    segments: list[dict[str, Any]] = Field(default_factory=list)


class HotelV2HistoryAggregatesOut(BaseModel):
    sample_size_total: int = Field(ge=0)
    sample_size_eligible: int = Field(ge=0)
    min_price: float | None = None
    max_price: float | None = None
    median_price: float | None = None
    average_price: float | None = None
    currency: str
    price_semantics: Literal["total", "unknown"]
    exclusions: dict[str, int] = Field(default_factory=dict)


class HotelV2TrackedOfferHistoryOut(BaseModel):
    tracked_offer_id: str
    series: HotelV2HistorySeriesOut
    aggregates: HotelV2HistoryAggregatesOut
    comparisons: dict[str, None] = Field(
        default_factory=lambda: {
            "vs_initial": None,
            "vs_previous": None,
            "vs_minimum": None,
        }
    )
    freshness: HotelV2FreshnessOut
    capabilities: dict[str, HotelV2CapabilityState]


class HotelV2TrackedOfferOut(BaseModel):
    id: str
    hotel_id: str
    state_version: int = Field(ge=1)
    state: Literal[
        "active",
        "pending_context",
        "pending_first_observation",
        "partial",
        "paused",
        "unavailable",
        "expired",
        "archived",
    ]
    stay_context: HotelV2TrackingStayContextOut
    latest_observation: HotelV2TrackingObservationOut | None = None
    capabilities: dict[str, HotelV2CapabilityState]
    warnings: list[HotelV2WarningOut] = Field(default_factory=list)


class HotelV2TrackedOfferCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_rate_id: str = Field(
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )


class HotelV2TrackedOfferCreationMetaOut(BaseModel):
    outcome: Literal["created", "existing"]
    semantic_dedupe: bool


class HotelV2TrackedOfferCreateOut(BaseModel):
    tracking: HotelV2TrackedOfferOut
    creation: HotelV2TrackedOfferCreationMetaOut


class HotelV2TrackedOfferLifecycleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["pause", "resume", "archive"]
    expected_state_version: int = Field(ge=1)


class HotelV2TrackedOfferLifecycleOut(BaseModel):
    tracking: HotelV2TrackedOfferOut
    outcome: Literal["applied", "existing", "expired"]


class HotelV2TrackedOffersMetaOut(BaseModel):
    contract_version: Literal["hotels.tracking.v2"] = "hotels.tracking.v2"
    request_id: str
    generated_at: str
    result_state: Literal["success", "empty", "partial"]
    query: dict[str, Any]
    pagination: HotelV2PaginationOut
    freshness: HotelV2FreshnessOut
    capabilities: dict[str, HotelV2CapabilityState]
    warnings: list[HotelV2WarningOut] = Field(default_factory=list)


class HotelV2TrackedOffersOut(BaseModel):
    data: list[HotelV2TrackedOfferOut]
    meta: HotelV2TrackedOffersMetaOut
