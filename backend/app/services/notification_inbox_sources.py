from dataclasses import dataclass
from datetime import datetime

from app.i18n import t
from app.infrastructure.db.models import (
    FlightWatch,
    HotelAlertEvent,
    HotelProperty,
    NotificationEvent,
    SecurityActivity,
)

SOURCE_ALERT_EVENT = "alert_event"
SOURCE_HOTEL_ALERT_EVENT = "hotel_alert_event"
SOURCE_SECURITY_ACTIVITY = "security_activity"
SOURCE_COMMUNITY_TRENDING = "community_trending"
READABLE_SOURCES = {
    SOURCE_ALERT_EVENT,
    SOURCE_HOTEL_ALERT_EVENT,
    SOURCE_SECURITY_ACTIVITY,
    SOURCE_COMMUNITY_TRENDING,
}


@dataclass(frozen=True, slots=True)
class SourceRef:
    source_type: str
    source_id: str


@dataclass(frozen=True, slots=True)
class InboxItem:
    id: str
    source_type: str
    source_id: str
    category: str
    tone: str
    title: str
    body: str
    route_label: str | None
    action_href: str | None
    created_at: datetime
    read_at: datetime | None

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


def alert_ref(event: NotificationEvent) -> SourceRef:
    return SourceRef(SOURCE_ALERT_EVENT, event.id)


def hotel_alert_ref(event: HotelAlertEvent) -> SourceRef:
    return SourceRef(SOURCE_HOTEL_ALERT_EVENT, event.id)


def security_ref(activity: SecurityActivity) -> SourceRef:
    return SourceRef(SOURCE_SECURITY_ACTIVITY, activity.id)


def alert_item(event: NotificationEvent, watch: FlightWatch, read_at: datetime | None) -> InboxItem:
    ref = alert_ref(event)
    category = _alert_category(event)
    route_label = f"{watch.origin_iata} -> {watch.destination_iata}"
    return InboxItem(
        id=f"{ref.source_type}:{ref.source_id}",
        source_type=ref.source_type,
        source_id=ref.source_id,
        category=category,
        tone=_alert_tone(event),
        title=_alert_title(category),
        body=event.message,
        route_label=route_label,
        action_href=f"/notifications?view=rules&watch_id={watch.id}",
        created_at=event.created_at,
        read_at=read_at,
    )


def hotel_alert_item(
    event: HotelAlertEvent,
    hotel: HotelProperty,
    read_at: datetime | None,
) -> InboxItem:
    ref = hotel_alert_ref(event)
    return InboxItem(
        id=f"{ref.source_type}:{ref.source_id}",
        source_type=ref.source_type,
        source_id=ref.source_id,
        category="price",
        tone=_hotel_alert_tone(event.event_type),
        title=_hotel_alert_title(event.event_type),
        body=event.message,
        route_label=f"{hotel.city}, {hotel.country_code}",
        action_href=f"/hoteles?hotel_id={hotel.id}",
        created_at=event.created_at,
        read_at=read_at,
    )


def security_item(activity: SecurityActivity, read_at: datetime | None) -> InboxItem:
    ref = security_ref(activity)
    return InboxItem(
        id=f"{ref.source_type}:{ref.source_id}",
        source_type=ref.source_type,
        source_id=ref.source_id,
        category="security",
        tone="info",
        title=_security_title(activity.event_type),
        body=_security_body(activity),
        route_label=None,
        action_href="/cuenta/seguridad",
        created_at=activity.created_at,
        read_at=read_at,
    )


def community_trending_item(event: NotificationEvent, read_at: datetime | None) -> InboxItem:
    """Build an InboxItem for a community trending notification."""
    return InboxItem(
        id=f"{SOURCE_COMMUNITY_TRENDING}:{event.id}",
        source_type=SOURCE_COMMUNITY_TRENDING,
        source_id=event.id,
        category="community",
        tone="info",
        title=t("es", "notifications.community_trending_title"),
        body=event.message,
        route_label=None,
        action_href="/dashboard",
        created_at=event.created_at,
        read_at=read_at,
    )


def _alert_category(event: NotificationEvent) -> str:
    if event.delivery_status in {"failed", "error"} or event.group_reason == "revalidation_failed":
        return "worker"
    if event.is_digest or event.grouped_count > 1:
        return "digest"
    return "price"


def _alert_tone(event: NotificationEvent) -> str:
    if event.delivery_status in {"failed", "error"}:
        return "error"
    if event.delivery_status == "queued":
        return "warning"
    if event.is_digest or event.grouped_count > 1:
        return "info"
    return "success"


def _alert_title(category: str) -> str:
    if category == "worker":
        return t("es", "notifications.worker_needs_attention")
    if category == "digest":
        return t("es", "notifications.grouped_summary")
    return t("es", "notifications.price_movement")


def _hotel_alert_title(event_type: str) -> str:
    if event_type in {"price_below", "percentage_drop", "availability_returned"}:
        return t("es", "hotels.alert.favorable")
    if event_type in {"price_above", "percentage_increase"}:
        return t("es", "hotels.alert.to_watch")
    return t("es", "hotels.alert.radar_updated")


def _hotel_alert_tone(event_type: str) -> str:
    if event_type in {"price_below", "percentage_drop", "availability_returned"}:
        return "success"
    if event_type in {"price_above", "percentage_increase", "parity_break"}:
        return "warning"
    return "info"


def _security_title(event_type: str) -> str:
    key_map = {
        "register": "security.title.register",
        "login": "security.title.login",
        "refresh": "security.title.refresh",
        "close_all_sessions": "security.title.close_all_sessions",
        "password_change": "security.title.password_change",
        "forgot_password_requested": "security.title.forgot_password_requested",
        "password_reset": "security.title.password_reset",
    }
    key = key_map.get(event_type, "security.title.default")
    return t("es", key)


def _security_body(activity: SecurityActivity) -> str:
    if activity.ip:
        return t("es", "security.body.with_ip", ip=str(activity.ip))
    return t("es", "security.body.without_ip")
