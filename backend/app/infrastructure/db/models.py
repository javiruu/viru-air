from datetime import date as date_type, datetime
from typing import Any, NotRequired, Optional, TypedDict

from app.core.time import utc_now_naive
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    BigInteger,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.domain.vocabulary import DELIVERY_STATUS_QUEUED, WATCH_STATUS_ACTIVE
from app.infrastructure.db.session import Base


class FareComparisonExtraData(TypedDict):
    kind: str
    selected: bool


class FareComparisonProfileData(TypedDict):
    travelers: int
    airline_id: NotRequired[str | None]
    flight_count: NotRequired[int]
    extras: list[FareComparisonExtraData]


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
    community_price_reports: Mapped[list["CommunityPriceReport"]] = relationship(
        back_populates="user",
    )


class FlightWatch(Base):
    __tablename__ = "flight_watch"
    __table_args__ = (
        Index(
            "uq_flight_watch_user_route_date",
            "user_id",
            "origin_iata",
            "destination_iata",
            "travel_date_local",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    origin_iata: Mapped[str] = mapped_column(String(3))
    destination_iata: Mapped[str] = mapped_column(String(3))
    travel_date_local: Mapped[date_type] = mapped_column(Date)
    target_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    group_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    fare_profile: Mapped[FareComparisonProfileData | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=WATCH_STATUS_ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    user: Mapped[User] = relationship(back_populates="watches")
    snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="watch")
    tracked_legs: Mapped[list["WatchTrackedFlightLeg"]] = relationship(
        back_populates="watch",
        cascade="all, delete-orphan",
        order_by="WatchTrackedFlightLeg.sequence",
    )
    community_price_report: Mapped["CommunityPriceReport | None"] = relationship(
        back_populates="watch",
        cascade="all, delete-orphan",
        uselist=False,
    )


class CommunityPriceReport(Base):
    __tablename__ = "community_price_report"
    __table_args__ = (
        UniqueConstraint("watch_id", name="uq_community_price_report_watch"),
        CheckConstraint(
            "(flew = false AND price_per_traveler IS NULL) "
            "OR (flew = true AND price_per_traveler > 0)",
            name="ck_community_price_report_flew_price",
        ),
        Index("ix_community_price_report_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    watch_id: Mapped[str] = mapped_column(
        ForeignKey("flight_watch.id", ondelete="CASCADE"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    trigger_reason: Mapped[str] = mapped_column(String(20))
    flew: Mapped[bool] = mapped_column(Boolean)
    price_per_traveler: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

    watch: Mapped[FlightWatch] = relationship(back_populates="community_price_report")
    user: Mapped[User] = relationship(back_populates="community_price_reports")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshot"
    __table_args__ = (
        Index("ix_price_snapshot_watch_captured", "watch_id", "captured_at_utc"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    watch_id: Mapped[str] = mapped_column(ForeignKey("flight_watch.id"), index=True)
    captured_at_utc: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    departure_time_local: Mapped[str | None] = mapped_column(String(5), nullable=True)
    raw_price: Mapped[float] = mapped_column(Numeric(10, 2))
    raw_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    provider: Mapped[str] = mapped_column(String(40), default="ryanair-py")
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)

    watch: Mapped[FlightWatch] = relationship(back_populates="snapshots")


class WatchTrackedFlightLeg(Base):
    __tablename__ = "watch_tracked_flight_leg"
    __table_args__ = (
        UniqueConstraint("watch_id", "sequence", name="uq_watch_tracked_flight_leg_sequence"),
        Index("ix_watch_tracked_flight_leg_instance", "flight_instance_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    watch_id: Mapped[str] = mapped_column(
        ForeignKey("flight_watch.id", ondelete="CASCADE"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    flight_instance_fingerprint: Mapped[str] = mapped_column(String(64))
    carrier_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    origin_iata: Mapped[str] = mapped_column(String(3))
    destination_iata: Mapped[str] = mapped_column(String(3))
    departure_date_local: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    scheduled_departure_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_arrival_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    identity_source: Mapped[str] = mapped_column(String(24), default="quick_search")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

    watch: Mapped[FlightWatch] = relationship(back_populates="tracked_legs")


class FlightOperationalSnapshot(Base):
    __tablename__ = "flight_operational_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "flight_instance_fingerprint",
            "provider",
            "observed_at",
            name="uq_flight_operational_snapshot_observation",
        ),
        Index(
            "ix_flight_operational_snapshot_instance_observed",
            "flight_instance_fingerprint",
            "observed_at",
        ),
        Index("ix_flight_operational_snapshot_expires", "expires_at"),
        Index(
            "ix_flight_operational_snapshot_provider_flight",
            "provider",
            "provider_flight_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    flight_instance_fingerprint: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(40))
    provider_flight_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    callsign: Mapped[str | None] = mapped_column(String(32), nullable=True)
    icao24: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(24))
    status_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    scheduled_departure_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_departure_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_departure_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_arrival_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_arrival_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_arrival_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    departure_terminal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    departure_gate: Mapped[str | None] = mapped_column(String(32), nullable=True)
    arrival_terminal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    arrival_gate: Mapped[str | None] = mapped_column(String(32), nullable=True)
    departure_delay_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arrival_delay_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    altitude_m: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    speed_mps: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    on_ground: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    registration: Mapped[str | None] = mapped_column(String(32), nullable=True)
    aircraft_iata: Mapped[str | None] = mapped_column(String(16), nullable=True)
    aircraft_icao: Mapped[str | None] = mapped_column(String(16), nullable=True)
    data_quality: Mapped[str] = mapped_column(String(24), default="observed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class FlightOperationalRefreshLock(Base):
    __tablename__ = "flight_operational_refresh_lock"
    __table_args__ = (
        Index("ix_flight_operational_refresh_lock_token", "lock_token", unique=True),
        Index("ix_flight_operational_refresh_lock_expires", "expires_at"),
    )

    flight_instance_fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    lock_token: Mapped[str] = mapped_column(String(64))
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    outcome: Mapped[str | None] = mapped_column(String(24), nullable=True)


class FlightProviderQuota(Base):
    __tablename__ = "flight_provider_quota"

    provider: Mapped[str] = mapped_column(String(40), primary_key=True)
    window_key: Mapped[str] = mapped_column(String(10))
    units_used: Mapped[int] = mapped_column(Integer, default=0)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    block_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class AlertRule(Base):
    __tablename__ = "alert_rule"
    __table_args__ = (
        Index("ix_alert_rule_watch_enabled", "watch_id", "enabled"),
    )

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
    __table_args__ = (
        Index("ix_notification_event_rule_created", "rule_id", "created_at"),
    )

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


class UserNotificationState(Base):
    __tablename__ = "user_notification_state"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_type",
            "source_id",
            name="uq_user_notification_state_source",
        ),
        Index("ix_user_notification_state_user_read", "user_id", "read_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(36), index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


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
    calendar_hint_bucket_mode_default: Mapped[str] = mapped_column(String(24), default="contextual")
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
    __table_args__ = (
        Index("ix_user_session_user_active_last_seen", "user_id", "is_active", "last_seen"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    device: Mapped[str] = mapped_column(String(200), default="Este dispositivo")
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    __table_args__ = (
        Index("ix_refresh_token_token_hash", "token_hash"),
    )

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
    __table_args__ = (
        Index("ix_password_reset_token_token_hash", "token_hash"),
    )

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
    __table_args__ = (
        Index("ix_security_activity_user_created", "user_id", "created_at"),
    )

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
        Index("ix_idempotency_record_created_at", "created_at"),
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
    # Fase 8: saved plans
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)


class DoorToDoorSavedPlace(Base):
    __tablename__ = "door_to_door_saved_place"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    label: Mapped[str] = mapped_column(String(180))
    note: Mapped[str] = mapped_column(String(280), default="")
    watch_id: Mapped[str | None] = mapped_column(ForeignKey("flight_watch.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


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


class HotelStayOffer(Base):
    __tablename__ = "hotel_stay_offer"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_hotel_id",
            "stay_query_fingerprint",
            "offer_fingerprint",
            name="uq_hotel_stay_offer_identity",
        ),
        Index("ix_hotel_stay_offer_hotel_provider", "canonical_hotel_id", "provider"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    canonical_hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    provider_hotel_id: Mapped[str] = mapped_column(String(120))
    fingerprint_version: Mapped[str] = mapped_column(String(24), default="hotel-stay-v2")
    stay_query_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    offer_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    canonical_query_json: Mapped[str] = mapped_column(Text)
    conditions_completeness: Mapped[str] = mapped_column(String(16), default="unknown")
    fee_semantics: Mapped[str] = mapped_column(String(16), default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelRateSnapshot(Base):
    __tablename__ = "hotel_rate_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    stay_offer_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_stay_offer.id"), nullable=True, index=True)
    tracked_offer_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_tracked_offer.id"), nullable=True, index=True)
    provider_run_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_provider_run.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    check_in: Mapped[date_type] = mapped_column(Date, index=True)
    check_out: Mapped[date_type] = mapped_column(Date, index=True)
    guests: Mapped[int] = mapped_column(Integer, default=2)
    room_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    meal_plan: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cancellation_policy: Mapped[str | None] = mapped_column(String(120), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    availability_status: Mapped[str] = mapped_column(String(20), default="available")
    deep_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    stay_query_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    offer_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    snapshot_outcome: Mapped[str | None] = mapped_column(String(24), nullable=True)
    price_semantics: Mapped[str | None] = mapped_column(String(16), nullable=True)
    amount_base: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    amount_total: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    fees_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions_completeness: Mapped[str | None] = mapped_column(String(16), nullable=True)

    @validates("deep_link")
    def _sanitize_deep_link(
        self,
        _key: str,
        value: str | None,
    ) -> str | None:
        # Enforce the same deny-by-default boundary for every ORM write,
        # including imports/admin scripts that bypass the hotel service.
        from app.hotels.partner_links import sanitize_hotel_deep_link

        return sanitize_hotel_deep_link(
            value,
            provider=getattr(self, "provider", None),
        )


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
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=60)
    evaluation_state: Mapped[str] = mapped_column(String(16), default="clear")
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_event_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class HotelProviderRun(Base):
    __tablename__ = "hotel_provider_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider: Mapped[str] = mapped_column(String(40), index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    client_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    execution_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tracked_outcomes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    latency_aggregates: Mapped[list["HotelProviderLatencyAggregate"]] = relationship(
        back_populates="provider_run",
        cascade="all, delete-orphan",
    )


class HotelProviderLatencyAggregate(Base):
    __tablename__ = "hotel_provider_latency_aggregate"
    __table_args__ = (
        UniqueConstraint(
            "provider_run_id",
            "provider",
            "operation",
            "outcome",
            "error_code",
            name="uq_hotel_provider_latency_aggregate_key",
        ),
        Index("ix_hotel_provider_latency_aggregate_run", "provider_run_id"),
        Index(
            "ix_hotel_provider_latency_aggregate_provider_operation_created",
            "provider",
            "operation",
            "created_at",
        ),
        CheckConstraint("sample_count >= 0", name="ck_hotel_provider_latency_sample_count_nonnegative"),
        CheckConstraint(
            "total_duration_ms >= 0",
            name="ck_hotel_provider_latency_total_duration_nonnegative",
        ),
        CheckConstraint(
            "min_duration_ms >= 0",
            name="ck_hotel_provider_latency_min_duration_nonnegative",
        ),
        CheckConstraint(
            "max_duration_ms >= 0",
            name="ck_hotel_provider_latency_max_duration_nonnegative",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider_run_id: Mapped[str] = mapped_column(
        ForeignKey("hotel_provider_run.id", ondelete="CASCADE"),
    )
    provider: Mapped[str] = mapped_column(String(40))
    operation: Mapped[str] = mapped_column(String(40))
    outcome: Mapped[str] = mapped_column(String(24))
    # ``none`` is the storage sentinel for the nullable in-memory error code;
    # keeping this dimension non-null makes the cross-dialect key deterministic.
    error_code: Mapped[str] = mapped_column(String(32))
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    min_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    max_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

    provider_run: Mapped[HotelProviderRun] = relationship(back_populates="latency_aggregates")


class HotelDailyMetric(Base):
    __tablename__ = "hotel_daily_metric"
    __table_args__ = (
        UniqueConstraint(
            "metric_date",
            "metric_name",
            "provider",
            "outcome",
            name="uq_hotel_daily_metric_key",
        ),
        Index("ix_hotel_daily_metric_date", "metric_date"),
        Index("ix_hotel_daily_metric_name_date", "metric_name", "metric_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    metric_date: Mapped[date_type] = mapped_column(Date)
    metric_name: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(40))
    outcome: Mapped[str] = mapped_column(String(24))
    count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelNotificationDelivery(Base):
    __tablename__ = "hotel_notification_delivery"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_hotel_notification_delivery_idempotency"),
        Index("ix_hotel_notification_delivery_queue", "status", "next_attempt_at", "created_at"),
        Index("ix_hotel_notification_delivery_recipient", "recipient_user_id", "created_at"),
        Index("ix_hotel_notification_delivery_source", "source_event_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_event_id: Mapped[str] = mapped_column(ForeignKey("hotel_alert_event.id", ondelete="CASCADE"))
    recipient_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    template_version: Mapped[str] = mapped_column(String(32), default="hotel-alert-v1")
    idempotency_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_class: Mapped[str | None] = mapped_column(String(24), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelSweepLease(Base):
    __tablename__ = "hotel_sweep_lease"
    __table_args__ = (
        Index("ix_hotel_sweep_lease_status_expires", "status", "lease_expires_at"),
        Index("ix_hotel_sweep_lease_token", "lock_token", unique=True),
    )

    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    lock_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lock_acquired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_provider_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelProviderCircuit(Base):
    __tablename__ = "hotel_provider_circuit"
    __table_args__ = (
        UniqueConstraint("provider", "operation", name="uq_hotel_provider_circuit_provider_operation"),
        Index("ix_hotel_provider_circuit_status_probe", "status", "next_probe_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider: Mapped[str] = mapped_column(String(40), index=True)
    operation: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16), default="closed")
    failure_threshold: Mapped[int] = mapped_column(Integer, default=3)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    state_version: Mapped[int] = mapped_column(Integer, default=0)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_probe_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    probe_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    probe_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelProviderBudgetReservation(Base):
    __tablename__ = "hotel_provider_budget_reservation"
    __table_args__ = (
        Index("ix_hotel_provider_budget_reservation_budget", "budget_id"),
        Index("ix_hotel_provider_budget_reservation_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    budget_id: Mapped[str] = mapped_column(ForeignKey("hotel_provider_budget.id", ondelete="CASCADE"))
    units: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="reserved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelProviderBudget(Base):
    __tablename__ = "hotel_provider_budget"
    __table_args__ = (
        UniqueConstraint("provider", "operation", "window_key", name="uq_hotel_provider_budget_window"),
        Index("ix_hotel_provider_budget_operation", "operation"),
        Index("ix_hotel_provider_budget_provider_operation", "provider", "operation"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider: Mapped[str] = mapped_column(String(40), index=True)
    operation: Mapped[str] = mapped_column(String(40))
    window_key: Mapped[str] = mapped_column(String(20))
    hard_limit: Mapped[int] = mapped_column(Integer, default=0)
    units_reserved: Mapped[int] = mapped_column(Integer, default=0)
    units_used: Mapped[int] = mapped_column(Integer, default=0)
    units_released: Mapped[int] = mapped_column(Integer, default=0)
    window_expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String(24), default="local_config")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelTrackedOffer(Base):
    __tablename__ = "hotel_tracked_offer"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "hotel_id", "check_in", "check_out", "guests", "provider",
            "room_label", "meal_plan", "cancellation_policy", "currency", "offer_fingerprint",
            name="uq_hotel_tracked_offer_identity",
        ),
        Index(
            "uq_hotel_tracked_offer_legacy_identity",
            "user_id",
            "hotel_id",
            "check_in",
            "check_out",
            "guests",
            "provider",
            unique=True,
            sqlite_where=text("offer_fingerprint IS NULL AND check_in IS NOT NULL AND check_out IS NOT NULL"),
            postgresql_where=text("offer_fingerprint IS NULL AND check_in IS NOT NULL AND check_out IS NOT NULL"),
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
    offer_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    initial_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    current_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    target_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    lifecycle_state: Mapped[str] = mapped_column(String(24), default="active", index=True)
    lifecycle_version: Mapped[int] = mapped_column(Integer, default=1)
    lifecycle_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelTrackedOfferLifecycleEvent(Base):
    __tablename__ = "hotel_tracked_offer_lifecycle_event"
    __table_args__ = (
        UniqueConstraint("tracked_offer_id", "state_version", name="uq_hotel_tracking_lifecycle_version"),
        Index("ix_hotel_tracking_lifecycle_offer_created", "tracked_offer_id", "created_at"),
        Index("ix_hotel_tracking_lifecycle_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tracked_offer_id: Mapped[str] = mapped_column(
        ForeignKey("hotel_tracked_offer.id", ondelete="CASCADE"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    from_state: Mapped[str] = mapped_column(String(24))
    to_state: Mapped[str] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(24))
    source: Mapped[str] = mapped_column(String(32))
    state_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class HotelUserStayWatch(Base):
    __tablename__ = "hotel_user_stay_watch"
    __table_args__ = (
        UniqueConstraint("user_id", "stay_offer_id", name="uq_hotel_user_stay_watch_identity"),
        UniqueConstraint("legacy_tracked_offer_id", name="uq_hotel_user_stay_watch_legacy"),
        Index("ix_hotel_user_stay_watch_user_status_updated", "user_id", "status", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stay_offer_id: Mapped[str] = mapped_column(ForeignKey("hotel_stay_offer.id"), index=True)
    legacy_tracked_offer_id: Mapped[str | None] = mapped_column(
        ForeignKey("hotel_tracked_offer.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelSavedSearch(Base):
    __tablename__ = "hotel_saved_search"
    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint", name="uq_hotel_saved_search_user_fingerprint"),
        Index("ix_hotel_saved_search_user_status_updated", "user_id", "status", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    schema_version: Mapped[str] = mapped_column(String(32), default="hotel-search-v1")
    fingerprint: Mapped[str] = mapped_column(String(64))
    canonical_query_json: Mapped[str] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class QuickSearchCacheEntry(Base):
    """Cache compartida persistente para quick-search (V2.1).

    Almacena resultados de provider por unidad exacta (origin, destination, date, provider).
    Cross-user: no tiene FK a users. La reutilizacion es anonima entre usuarios.
    """
    __tablename__ = "quick_search_cache_entry"
    __table_args__ = (
        UniqueConstraint(
            "origin_iata",
            "destination_iata",
            "travel_date",
            "provider",
            "source_hash",
            name="uq_quick_search_cache_unit",
        ),
        Index("ix_qs_cache_lookup", "origin_iata", "destination_iata", "travel_date", "provider"),
        Index("ix_qs_cache_expires", "expires_at_utc"),
        Index("ix_qs_cache_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    origin_iata: Mapped[str] = mapped_column(String(3))
    destination_iata: Mapped[str] = mapped_column(String(3))
    travel_date: Mapped[date_type] = mapped_column(Date)
    provider: Mapped[str] = mapped_column(String(40))
    search_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    canonical_request_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_set_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ready")
    freshness_status: Mapped[str] = mapped_column(String(32), default="fresh", index=True)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=86400)
    expires_at_utc: Mapped[datetime] = mapped_column(DateTime, index=True)
    captured_at_utc: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    last_accessed_at_utc: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    payload_json: Mapped[str] = mapped_column(Text)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    source_hash: Mapped[str] = mapped_column(String(64))
    provider_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)


class QuickSearchProviderLock(Base):
    __tablename__ = "quick_search_provider_lock"
    __table_args__ = (
        Index("ix_qs_provider_lock_expires", "expires_at"),
        Index("ix_qs_provider_lock_route", "origin_iata", "destination_iata", "travel_date", "provider"),
    )

    lock_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    origin_iata: Mapped[str] = mapped_column(String(3))
    destination_iata: Mapped[str] = mapped_column(String(3))
    travel_date: Mapped[date_type] = mapped_column(Date)
    provider: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    lock_token: Mapped[str] = mapped_column(String(64), index=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class CalendarPriceObservation(Base):
    __tablename__ = "calendar_price_observation"
    __table_args__ = (
        UniqueConstraint(
            "query_fingerprint",
            "route_signature",
            "provider",
            "observed_at",
            name="uq_calendar_price_observation_sample",
        ),
        Index(
            "ix_calendar_price_observation_reference",
            "reference_fingerprint",
            "observed_at",
        ),
        Index(
            "ix_calendar_price_observation_day",
            "query_fingerprint",
            "travel_date",
            "observed_at",
        ),
        Index("ix_calendar_price_observation_expires", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    query_fingerprint: Mapped[str] = mapped_column(String(64))
    reference_fingerprint: Mapped[str] = mapped_column(String(64))
    route_signature: Mapped[str] = mapped_column(String(255))
    travel_date: Mapped[date_type] = mapped_column(Date)
    leg: Mapped[str] = mapped_column(String(16), default="outbound")
    adults: Mapped[int] = mapped_column(Integer, default=1)
    cabin: Mapped[str] = mapped_column(String(32), default="economy")
    aggregation_mode: Mapped[str] = mapped_column(String(16), default="min")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    provider: Mapped[str] = mapped_column(String(80), default="calendar-aggregate")
    raw_price_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    raw_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    normalized_price_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    freshness_status: Mapped[str] = mapped_column(String(32), default="fresh")
    coverage_status: Mapped[str] = mapped_column(String(32), default="partial")
    validation_status: Mapped[str] = mapped_column(String(32), default="observed")
    source_kind: Mapped[str] = mapped_column(String(32), default="calendar_hint")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class FlightOfferCacheEntry(Base):
    __tablename__ = "flight_offer_cache_entry"
    __table_args__ = (
        UniqueConstraint("offer_fingerprint", name="uq_flight_offer_cache_fingerprint"),
        Index("ix_flight_offer_cache_route", "origin_airport", "destination_airport", "departure_at"),
        Index("ix_flight_offer_cache_provider", "provider", "departure_at"),
        Index("ix_flight_offer_cache_instance", "flight_instance_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    offer_fingerprint: Mapped[str] = mapped_column(String(64))
    flight_instance_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    carrier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    carrier_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    origin_airport: Mapped[str] = mapped_column(String(3))
    destination_airport: Mapped[str] = mapped_column(String(3))
    departure_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    arrival_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    departure_time_local: Mapped[str | None] = mapped_column(String(16), nullable=True)
    arrival_time_local: Mapped[str | None] = mapped_column(String(16), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stops_count: Mapped[int] = mapped_column(Integer, default=0)
    booking_url_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    deeplink_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(24), default="provider")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class FlightPriceObservation(Base):
    __tablename__ = "flight_price_observation"
    __table_args__ = (
        Index("ix_flight_price_observation_offer_observed", "offer_id", "observed_at"),
        Index("ix_flight_price_observation_expires", "expires_at"),
        Index("ix_flight_price_observation_freshness", "freshness_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    offer_id: Mapped[str] = mapped_column(ForeignKey("flight_offer_cache_entry.id"), index=True)
    search_cache_entry_id: Mapped[str | None] = mapped_column(
        ForeignKey("quick_search_cache_entry.id"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(40), index=True)
    price_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    fare_family: Mapped[str | None] = mapped_column(String(64), nullable=True)
    baggage_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    seats_left: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    freshness_status: Mapped[str] = mapped_column(String(32), default="fresh")
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), default="observed")
    price_changed_since_last_seen: Mapped[bool] = mapped_column(Boolean, default=False)
    delta_abs: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    delta_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)


class QuickSearchNegativeCacheEntry(Base):
    __tablename__ = "quick_search_negative_cache_entry"
    __table_args__ = (
        UniqueConstraint("negative_fingerprint", name="uq_qs_negative_cache_fingerprint"),
        Index("ix_qs_negative_cache_expires", "expires_at"),
        Index("ix_qs_negative_cache_provider", "provider", "expires_at"),
        Index("ix_qs_negative_cache_freshness", "freshness_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    negative_fingerprint: Mapped[str] = mapped_column(String(64))
    scope: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    canonical_request_json: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    freshness_status: Mapped[str] = mapped_column(String(32), default="negative_fresh")
    retry_after_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class QuickSearchPopularityCounter(Base):
    __tablename__ = "quick_search_popularity_counter"
    __table_args__ = (
        UniqueConstraint(
            "origin_iata",
            "destination_iata",
            "travel_date",
            "currency",
            name="uq_qs_popularity_route_day_currency",
        ),
        Index("ix_qs_popularity_count", "search_count"),
        Index("ix_qs_popularity_route", "origin_iata", "destination_iata", "travel_date"),
        Index("ix_qs_popularity_last_seen", "last_searched_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    origin_iata: Mapped[str] = mapped_column(String(3))
    destination_iata: Mapped[str] = mapped_column(String(3))
    travel_date: Mapped[date_type] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    search_count: Mapped[int] = mapped_column(Integer, default=1)
    first_searched_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    last_searched_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class QuickSearchPopularityDaily(Base):
    __tablename__ = "quick_search_popularity_daily"
    __table_args__ = (
        UniqueConstraint(
            "search_date",
            "origin_iata",
            "destination_iata",
            "currency",
            name="uq_qs_popularity_daily_route_currency",
        ),
        Index("ix_qs_popularity_daily_date_count", "search_date", "search_count"),
        Index(
            "ix_qs_popularity_daily_route",
            "origin_iata",
            "destination_iata",
            "search_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    search_date: Mapped[date_type] = mapped_column(Date)
    origin_iata: Mapped[str] = mapped_column(String(3))
    destination_iata: Mapped[str] = mapped_column(String(3))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    search_count: Mapped[int] = mapped_column(Integer, default=1)
    first_searched_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    last_searched_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class CommunityTrendingSnapshot(Base):
    __tablename__ = "community_trending_snapshot"
    __table_args__ = (
        Index(
            "ix_community_trending_snapshot_status_calculated",
            "status",
            "calculated_at_utc",
        ),
        Index(
            "ix_community_trending_snapshot_status_expires",
            "status",
            "expires_at_utc",
        ),
        Index("ix_community_trending_snapshot_reporting_date", "reporting_date"),
        CheckConstraint(
            "status IN ('building', 'published')",
            name="ck_community_trending_snapshot_status",
        ),
        CheckConstraint(
            "route_count >= 0",
            name="ck_community_trending_snapshot_route_count",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reporting_date: Mapped[date_type] = mapped_column(Date)
    window_start_date: Mapped[date_type] = mapped_column(Date)
    window_end_date: Mapped[date_type] = mapped_column(Date)
    calculated_at_utc: Mapped[datetime] = mapped_column(DateTime)
    published_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at_utc: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="building")
    route_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    routes: Mapped[list["CommunityTrendingSnapshotRoute"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
        order_by="CommunityTrendingSnapshotRoute.rank",
    )


class CommunityTrendingSnapshotRoute(Base):
    __tablename__ = "community_trending_snapshot_route"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "origin_iata",
            "destination_iata",
            name="uq_community_trending_snapshot_route",
        ),
        Index(
            "ix_community_trending_snapshot_route_snapshot_rank",
            "snapshot_id",
            "rank",
        ),
        Index(
            "ix_community_trending_snapshot_route_snapshot_route",
            "snapshot_id",
            "origin_iata",
            "destination_iata",
        ),
        CheckConstraint(
            "rank >= 1",
            name="ck_community_trending_snapshot_route_rank",
        ),
        CheckConstraint(
            "search_count >= 0",
            name="ck_community_trending_snapshot_route_search_count",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("community_trending_snapshot.id", ondelete="CASCADE"),
    )
    origin_iata: Mapped[str] = mapped_column(String(3))
    destination_iata: Mapped[str] = mapped_column(String(3))
    rank: Mapped[int] = mapped_column(Integer)
    search_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    snapshot: Mapped[CommunityTrendingSnapshot] = relationship(back_populates="routes")


class RevalidationJob(Base):
    __tablename__ = "revalidation_job"
    __table_args__ = (
        Index("ix_revalidation_job_due", "status", "scheduled_at", "priority"),
        Index("ix_revalidation_job_target", "target_type", "target_fingerprint", "provider", "status"),
        Index("ix_revalidation_job_lock_token", "lock_token"),
        Index(
            "uq_revalidation_job_active_target",
            "job_type",
            "target_type",
            "target_fingerprint",
            text("coalesce(provider, '')"),
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
            sqlite_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_type: Mapped[str] = mapped_column(String(32), index=True)
    target_type: Mapped[str] = mapped_column(String(16), index=True)
    target_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lock_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lock_acquired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class HotelAlertEvent(Base):
    __tablename__ = "hotel_alert_event"
    __table_args__ = (
        Index("uq_hotel_alert_event_fingerprint", "event_fingerprint", unique=True),
        Index("ix_hotel_alert_event_rule_created", "rule_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # Nullable for compatibility with historical sweep events created before
    # explicit event ownership existed. New events must always populate it.
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_alert_rule.id"), nullable=True, index=True)
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotel_property.id"), index=True)
    provider_run_id: Mapped[str | None] = mapped_column(ForeignKey("hotel_provider_run.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    trigger_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    event_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    snapshot_before_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    snapshot_after_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    baseline_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    baseline_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    baseline_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    baseline_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    comparability_key: Mapped[str | None] = mapped_column(String(180), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    eligibility_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evaluation_state: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)

