from datetime import date as date_type, datetime
from typing import Optional

from app.core.time import utc_now_naive
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.vocabulary import DELIVERY_STATUS_QUEUED, WATCH_STATUS_ACTIVE
from app.infrastructure.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    locale: Mapped[str] = mapped_column(String(8), default="es")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Madrid")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    watches: Mapped[list["FlightWatch"]] = relationship(back_populates="user")
    notes: Mapped[list["UserNote"]] = relationship(back_populates="user")


class FlightWatch(Base):
    __tablename__ = "flight_watch"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    origin_iata: Mapped[str] = mapped_column(String(3))
    destination_iata: Mapped[str] = mapped_column(String(3))
    travel_date_local: Mapped[datetime.date] = mapped_column(Date)
    target_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=WATCH_STATUS_ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    user: Mapped[User] = relationship(back_populates="watches")
    snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="watch")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    watch_id: Mapped[str] = mapped_column(ForeignKey("flight_watch.id"), index=True)
    captured_at_utc: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    departure_time_local: Mapped[str | None] = mapped_column(String(5), nullable=True)
    raw_price: Mapped[float] = mapped_column(Numeric(10, 2))
    raw_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    provider: Mapped[str] = mapped_column(String(40), default="ryanair-py")
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)

    watch: Mapped[FlightWatch] = relationship(back_populates="snapshots")


class AlertRule(Base):
    __tablename__ = "alert_rule"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    watch_id: Mapped[str] = mapped_column(ForeignKey("flight_watch.id"), index=True)
    rule_type: Mapped[str] = mapped_column(String(30))
    threshold_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    min_change_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    notify_on_every_change: Mapped[bool] = mapped_column(Boolean, default=False)
    cooldown_minutes: Mapped[int] = mapped_column(default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class NotificationEvent(Base):
    __tablename__ = "notification_event"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    rule_id: Mapped[str] = mapped_column(ForeignKey("alert_rule.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    delivery_status: Mapped[str] = mapped_column(String(20), default=DELIVERY_STATUS_QUEUED)
    message: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    group_key: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    group_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_digest: Mapped[bool] = mapped_column(Boolean, default=False)
    grouped_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class UxEvent(Base):
    __tablename__ = "ux_event"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_name: Mapped[str] = mapped_column(String(64), index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)


class ClientErrorEvent(Base):
    __tablename__ = "client_error_event"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    section: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(String(500))
    stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)


class UserPreference(Base):
    __tablename__ = "user_preference"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    default_radius_km: Mapped[int] = mapped_column(default=150)
    include_stops_default: Mapped[bool] = mapped_column(Boolean, default=False)
    include_nearby_origins_default: Mapped[bool] = mapped_column(Boolean, default=False)
    include_nearby_destinations_default: Mapped[bool] = mapped_column(Boolean, default=False)
    country_price_hint_mode_default: Mapped[str] = mapped_column(String(16), default="min")
    calendar_hint_bucket_mode_default: Mapped[str] = mapped_column(String(24), default="monthly_terciles")
    calendar_hint_guideline_low_max_default: Mapped[float] = mapped_column(Numeric(10, 2), default=90.0)
    calendar_hint_guideline_mid_max_default: Mapped[float] = mapped_column(Numeric(10, 2), default=150.0)
    avoid_departure_before: Mapped[str | None] = mapped_column(String(5), nullable=True)
    depart_before_default: Mapped[str | None] = mapped_column(String(5), nullable=True)
    strict_filters_default: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    language: Mapped[str] = mapped_column(String(8), default="es")
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="activa")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class UserSession(Base):
    __tablename__ = "user_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    device: Mapped[str] = mapped_column(String(200), default="Este dispositivo")
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    replaced_by_token_id: Mapped[str | None] = mapped_column(ForeignKey("refresh_token.id"), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_token"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class UserPreferenceAppearance(Base):
    __tablename__ = "user_preference_appearance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    theme: Mapped[str] = mapped_column(String(16), default="system")
    density: Mapped[str] = mapped_column(String(16), default="comfortable")
    reduce_motion: Mapped[bool] = mapped_column(Boolean, default=False)
    high_contrast: Mapped[bool] = mapped_column(Boolean, default=False)


class UserPreferenceRegion(Base):
    __tablename__ = "user_preference_region"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    language: Mapped[str] = mapped_column(String(8), default="es")
    region: Mapped[str] = mapped_column(String(8), default="ES")
    time_format: Mapped[str] = mapped_column(String(8), default="24h")
    decimal_separator: Mapped[str] = mapped_column(String(2), default=",")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")


class SecurityActivity(Base):
    __tablename__ = "security_activity"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class SupportFeedback(Base):
    __tablename__ = "support_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class Suggestion(Base):
    __tablename__ = "suggestion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(String(8), default="es")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_record"
    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", "idempotency_key", name="uq_idempotency_user_endpoint_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    endpoint: Mapped[str] = mapped_column(String(200), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), index=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int] = mapped_column()
    response_body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class DoorToDoorSavedLocation(Base):
    __tablename__ = "door_to_door_saved_location"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    location_type: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(180))
    lat: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class DoorToDoorSearchHistory(Base):
    __tablename__ = "door_to_door_search_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    watch_id: Mapped[str] = mapped_column(ForeignKey("flight_watch.id"), index=True)
    origin_json: Mapped[str] = mapped_column(Text)
    final_destination_json: Mapped[str] = mapped_column(Text)
    preferences_json: Mapped[str] = mapped_column(Text)
    summary_json: Mapped[str] = mapped_column(Text)
    warnings_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)


class DoorToDoorChosenOption(Base):
    __tablename__ = "door_to_door_chosen_option"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    watch_id: Mapped[str] = mapped_column(ForeignKey("flight_watch.id"), index=True)
    history_id: Mapped[str | None] = mapped_column(ForeignKey("door_to_door_search_history.id"), nullable=True)
    option_id: Mapped[str] = mapped_column(String(80))
    option_label: Mapped[str] = mapped_column(String(120))
    option_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    chosen_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)


class UserNote(Base):
    __tablename__ = "user_note"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    user: Mapped[User] = relationship(back_populates="notes")


class Airport(Base):
    __tablename__ = "airport"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    iata: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    icao: Mapped[str | None] = mapped_column(String(4), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    latitude: Mapped[float] = mapped_column(Numeric(10, 6))
    longitude: Mapped[float] = mapped_column(Numeric(10, 6))
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    airport_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(50), default="ourairports")


class HotelProperty(Base):
    __tablename__ = "hotel_property"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    canonical_name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), index=True)
    normalized_city: Mapped[str] = mapped_column(String(100), index=True, default="")
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelProviderAlias(Base):
    __tablename__ = "hotel_provider_alias"
    __table_args__ = (
        UniqueConstraint("provider", "provider_hotel_id", name="uq_hotel_provider_alias_provider_hotel_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    provider_hotel_id: Mapped[str] = mapped_column(String(120))
    raw_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)


class HotelRateSnapshot(Base):
    __tablename__ = "hotel_rate_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    tracked_offer_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_tracked_offer.id"), nullable=True, index=True)
    provider_run_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_provider_run.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    check_in: Mapped[datetime.date] = mapped_column(Date, index=True)
    check_out: Mapped[datetime.date] = mapped_column(Date, index=True)
    guests: Mapped[int] = mapped_column(Integer, default=2)
    room_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    meal_plan: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cancellation_policy: Mapped[str | None] = mapped_column(String(120), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    availability_status: Mapped[str] = mapped_column(String(20), default="available")
    deep_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)


class HotelWatchlistItem(Base):
    __tablename__ = "hotel_watchlist_item"
    __table_args__ = (
        UniqueConstraint("user_id", "hotel_id", name="uq_hotel_watchlist_item_user_hotel"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class HotelCompSet(Base):
    __tablename__ = "hotel_comp_set"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    anchor_hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class HotelCompSetMember(Base):
    __tablename__ = "hotel_comp_set_member"
    __table_args__ = (
        UniqueConstraint("comp_set_id", "hotel_id", name="uq_hotel_comp_set_member_comp_hotel"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    comp_set_id: Mapped[str] = mapped_column(ForeignKey("hotel_comp_set.id"), index=True)
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)


class HotelAlertRule(Base):
    __tablename__ = "hotel_alert_rule"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    tracked_offer_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_tracked_offer.id"), nullable=True, index=True)
    rule_type: Mapped[str] = mapped_column(String(40))
    threshold_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    threshold_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    compare_against: Mapped[str] = mapped_column(String(20), default="snapshot_previous")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class HotelProviderRun(Base):
    __tablename__ = "hotel_provider_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider: Mapped[str] = mapped_column(String(40), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)


class HotelTrackedOffer(Base):
    __tablename__ = "hotel_tracked_offer"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "hotel_id", "check_in", "check_out", "guests", "provider",
            name="uq_hotel_tracked_offer_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    area_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    origin_query: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    radius_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    check_in: Mapped[Optional[date_type]] = mapped_column(Date, nullable=True)
    check_out: Mapped[Optional[date_type]] = mapped_column(Date, nullable=True)
    guests: Mapped[int] = mapped_column(Integer, default=2)
    room_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    meal_plan: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cancellation_policy: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider: Mapped[str] = mapped_column(String(40))
    initial_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    current_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    target_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelAlertEvent(Base):
    __tablename__ = "hotel_alert_event"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_alert_rule.id"), nullable=True, index=True)
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    provider_run_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_provider_run.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    trigger_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)

