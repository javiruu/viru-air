from datetime import date as Date, datetime

import re

from pydantic import BaseModel, Field, field_validator, model_validator
from app.domain.vocabulary import (
    ALERT_RULE_TYPE_THRESHOLD_HIGH,
    ALERT_RULE_TYPE_THRESHOLD_LOW,
    ALLOWED_RULE_TYPES,
    RULE_TYPE_ALIASES,
    WATCH_STATUS_UPDATABLE,
)


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("invalid_email")
        return email


class LoginIn(RegisterIn):
    pass


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    id: str
    email: str
    locale: str
    is_admin: bool


class AdminUserOut(BaseModel):
    id: str
    email: str
    is_admin: bool
    is_verified: bool
    locale: str
    timezone: str
    created_at: datetime


class AdminUserUpdateIn(BaseModel):
    is_admin: bool | None = None
    is_verified: bool | None = None
    locale: str | None = None
    timezone: str | None = None


class AdminPasswordIn(BaseModel):
    password: str = Field(min_length=8)


class UxEventIn(BaseModel):
    event_name: str = Field(min_length=1, max_length=64)
    duration_ms: int | None = Field(default=None, ge=0, le=300000)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ClientErrorIn(BaseModel):
    section: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=500)
    stack: str | None = Field(default=None, max_length=8000)


class AdminProductMetricsOut(BaseModel):
    dashboard_views: int
    quick_search_executed: int
    search_empty_results: int
    search_empty_rate_pct: float
    quick_search_avg_ms: float
    watchlist_refresh: int
    alert_created: int
    alert_triggered: int
    watchlist_refresh_to_alert_created_pct: float
    alert_created_rate_pct: float


class WatchCreateIn(BaseModel):
    origin_iata: str = Field(min_length=3, max_length=3)
    destination_iata: str = Field(min_length=3, max_length=3)
    travel_date_local: Date
    target_price: float | None = Field(default=None, ge=0)

    @field_validator("origin_iata", "destination_iata")
    @classmethod
    def validate_iata(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("iata_invalido")
        return cleaned


class WatchOut(BaseModel):
    id: str
    origin_iata: str
    destination_iata: str
    travel_date_local: Date
    target_price: float | None
    status: str


class WatchDetailOut(WatchOut):
    latest_snapshot: "SnapshotOut | None" = None


class WatchUpdateIn(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in WATCH_STATUS_UPDATABLE:
            raise ValueError("invalid_watch_status")
        return normalized


class SnapshotOut(BaseModel):
    captured_at_utc: datetime
    raw_price: float
    raw_currency: str
    departure_time_local: str | None = None


class SnapshotBatchIn(BaseModel):
    watch_ids: list[str] = Field(
        default_factory=list,
        max_length=500,
        description="Lista de watch_ids (max 500) para recuperar histórico en lote",
    )
    captured_since_utc: datetime | None = Field(
        default=None,
        description="Filtra snapshots capturados desde este timestamp UTC (inclusive)",
    )
    max_rows: int = Field(
        default=5000,
        ge=1,
        le=20000,
        description="Límite duro de filas a devolver en la respuesta batch",
    )


class SnapshotBatchOut(BaseModel):
    watch_id: str
    captured_at_utc: datetime
    raw_price: float
    raw_currency: str
    departure_time_local: str | None = None


class WatchRefreshBulkIn(BaseModel):
    watch_ids: list[str] = Field(default_factory=list, min_length=1, max_length=100)


class AlertRuleIn(BaseModel):
    watch_id: str
    rule_type: str
    threshold_value: float | None = Field(default=None, ge=0)
    notify_on_every_change: bool = False
    cooldown_minutes: int = Field(default=60, ge=1, le=10080)
    min_change_pct: float | None = Field(default=None, ge=0, le=100)

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_RULE_TYPES:
            raise ValueError("invalid_rule_type")
        return RULE_TYPE_ALIASES.get(normalized, normalized)

    @model_validator(mode="after")
    def validate_threshold_requirement(self):
        if self.rule_type in {ALERT_RULE_TYPE_THRESHOLD_LOW, ALERT_RULE_TYPE_THRESHOLD_HIGH} and self.threshold_value is None:
            raise ValueError("threshold_value_required")
        return self


class AlertRuleUpdateIn(BaseModel):
    rule_type: str | None = None
    threshold_value: float | None = Field(default=None, ge=0)
    notify_on_every_change: bool | None = None
    cooldown_minutes: int | None = Field(default=None, ge=1, le=10080)
    enabled: bool | None = None
    min_change_pct: float | None = Field(default=None, ge=0, le=100)

    @field_validator("rule_type")
    @classmethod
    def validate_optional_rule_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ALLOWED_RULE_TYPES:
            raise ValueError("invalid_rule_type")
        return RULE_TYPE_ALIASES.get(normalized, normalized)


class AlertEvaluateIn(BaseModel):
    watch_id: str


class PreferenceIn(BaseModel):
    default_radius_km: int = Field(default=150, ge=0, le=500)
    include_stops_default: bool = False
    include_nearby_origins_default: bool = False
    include_nearby_destinations_default: bool = False
    avoid_departure_before: str | None = None
    depart_before_default: str | None = None
    strict_filters_default: bool = True
    preferred_currency: str = "EUR"
    language: str = "es"

    @field_validator("avoid_departure_before", "depart_before_default")
    @classmethod
    def validate_departure_before(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", value.strip()):
            raise ValueError("invalid_time_format")
        return value.strip()

    @field_validator("preferred_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        currency = value.strip().upper()
        if currency not in {"EUR", "USD", "GBP"}:
            raise ValueError("invalid_currency")
        return currency

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        language = value.strip().lower()
        if language not in {"es", "en"}:
            raise ValueError("invalid_language")
        return language


class AppearancePreferenceIn(BaseModel):
    theme: str = "system"
    density: str = "comfortable"
    reduce_motion: bool = False
    high_contrast: bool = False

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        theme = value.strip().lower()
        if theme not in {"light", "dark", "system"}:
            raise ValueError("invalid_theme")
        return theme

    @field_validator("density")
    @classmethod
    def validate_density(cls, value: str) -> str:
        density = value.strip().lower()
        if density not in {"compact", "comfortable"}:
            raise ValueError("invalid_density")
        return density


class RegionPreferenceIn(BaseModel):
    language: str = "es"
    region: str = "ES"
    time_format: str = "24h"
    decimal_separator: str = ","
    currency: str = "EUR"

    @field_validator("language")
    @classmethod
    def validate_region_language(cls, value: str) -> str:
        language = value.strip().lower()
        if language not in {"es", "en"}:
            raise ValueError("invalid_language")
        return language

    @field_validator("region")
    @classmethod
    def validate_region(cls, value: str) -> str:
        region = value.strip().upper()
        if region not in {"ES", "EU", "US", "UK"}:
            raise ValueError("invalid_region")
        return region

    @field_validator("time_format")
    @classmethod
    def validate_time_format(cls, value: str) -> str:
        time_format = value.strip().lower()
        if time_format not in {"24h", "12h"}:
            raise ValueError("invalid_time_format")
        return time_format

    @field_validator("decimal_separator")
    @classmethod
    def validate_decimal_separator(cls, value: str) -> str:
        separator = value.strip()
        if separator not in {",", "."}:
            raise ValueError("invalid_decimal_separator")
        return separator

    @field_validator("currency")
    @classmethod
    def validate_region_currency(cls, value: str) -> str:
        currency = value.strip().upper()
        if currency not in {"EUR", "USD", "GBP"}:
            raise ValueError("invalid_currency")
        return currency


class ProfileUpdateIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    email: str | None = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("display_name_required")
        return trimmed

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise ValueError("invalid_avatar_url")
        return trimmed


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)


class FeedbackIn(BaseModel):
    feedback_type: str = Field(min_length=3, max_length=20)
    message: str = Field(min_length=3, max_length=5000)
    attachment_url: str | None = Field(default=None, max_length=500)

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, value: str) -> str:
        feedback_type = value.strip().lower()
        if feedback_type not in {"bug", "idea", "general"}:
            raise ValueError("invalid_feedback_type")
        return feedback_type

    @field_validator("attachment_url")
    @classmethod
    def validate_attachment_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise ValueError("invalid_attachment_url")
        return trimmed


class SuggestionIn(BaseModel):
    text: str = Field(min_length=3, max_length=1000)
    locale: str = "es"


class NoteIn(BaseModel):
    title: str = Field(default="", max_length=120)
    body: str = Field(default="", max_length=6000)


class NoteUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None, max_length=6000)


class NoteOut(BaseModel):
    id: str
    title: str
    body: str
    created_at: datetime
    updated_at: datetime


class RecommendationWeights(BaseModel):
    price: float = Field(default=0.4, ge=0, le=1)
    speed: float = Field(default=0.2, ge=0, le=1)
    climate: float = Field(default=0.2, ge=0, le=1)
    trend: float = Field(default=0.1, ge=0, le=1)
    novelty: float = Field(default=0.1, ge=0, le=1)


class RecommendationRequest(BaseModel):
    origin_iata: str | list[str] | None = None
    destination_iata: str | list[str] | None = None
    travel_date: Date | None = None
    date: Date | None = None
    days_before: int = Field(default=0, ge=0, le=30)
    days_after: int = Field(default=0, ge=0, le=30)
    radius_km: int | None = Field(default=None, ge=0, le=500)
    include_nearby_origins: bool | None = None
    include_nearby_destinations: bool | None = None
    exclude_origins: str | list[str] | None = None
    exclude_destinations: str | list[str] | None = None
    include_stops: bool | None = None
    max_stops: int | None = None
    depart_after: str | None = None
    depart_before: str | None = None
    strict_filters: bool | None = None
    soft_filters_weight: float | None = None
    locale: str = "es"
    weights: RecommendationWeights | None = None


    @field_validator("depart_after", "depart_before")
    @classmethod
    def validate_departure_window(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", cleaned):
            raise ValueError("invalid_time_format")
        return cleaned


class RecommendationAiMeta(BaseModel):
    used: bool
    model: str | None = None
    error: str | None = None
    reasoning_mode: str = "heuristic"
    summary: str | None = None
    active_signals: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    query: dict
    items: list[dict]
    ai: RecommendationAiMeta
