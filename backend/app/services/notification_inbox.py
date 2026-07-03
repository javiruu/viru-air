from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import (
    AlertRule,
    FlightWatch,
    NotificationEvent,
    SecurityActivity,
    UserNotificationState,
)

SOURCE_ALERT_EVENT = "alert_event"
SOURCE_SECURITY_ACTIVITY = "security_activity"
READABLE_SOURCES = {SOURCE_ALERT_EVENT, SOURCE_SECURITY_ACTIVITY}


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


def _state_map(
    db: Session,
    *,
    user_id: str,
    source_refs: list[tuple[str, str]],
) -> dict[tuple[str, str], datetime]:
    if not source_refs:
        return {}
    wanted = set(source_refs)
    rows = db.scalars(
        select(UserNotificationState).where(
            UserNotificationState.user_id == user_id,
            UserNotificationState.source_type.in_({source_type for source_type, _ in source_refs}),
            UserNotificationState.source_id.in_({source_id for _, source_id in source_refs}),
        )
    ).all()
    return {
        (row.source_type, row.source_id): row.read_at
        for row in rows
        if (row.source_type, row.source_id) in wanted
    }


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


def _alert_title(event: NotificationEvent, category: str) -> str:
    if category == "worker":
        return "Worker de señales necesita atención"
    if category == "digest":
        return "Resumen de señales agrupadas"
    return "Movimiento de precio detectado"


def _security_title(event_type: str) -> str:
    titles = {
        "register": "Cuenta creada",
        "login": "Nuevo acceso a tu cuenta",
        "refresh": "Sesión renovada",
        "close_all_sessions": "Sesiones cerradas",
        "password_change": "Contraseña actualizada",
        "forgot_password_requested": "Recuperación solicitada",
        "password_reset": "Contraseña restablecida",
    }
    return titles.get(event_type, "Actividad de seguridad")


def _security_body(activity: SecurityActivity) -> str:
    if activity.ip:
        return f"Actividad registrada desde {activity.ip}."
    return "Actividad registrada en tu cuenta."


def _source_belongs_to_user(
    db: Session,
    *,
    user_id: str,
    source_type: str,
    source_id: str,
) -> bool:
    if source_type == SOURCE_SECURITY_ACTIVITY:
        return (
            db.scalar(
                select(SecurityActivity.id).where(
                    SecurityActivity.id == source_id,
                    SecurityActivity.user_id == user_id,
                )
            )
            is not None
        )
    if source_type == SOURCE_ALERT_EVENT:
        return (
            db.scalar(
                select(NotificationEvent.id)
                .join(AlertRule, NotificationEvent.rule_id == AlertRule.id)
                .join(FlightWatch, AlertRule.watch_id == FlightWatch.id)
                .where(
                    NotificationEvent.id == source_id,
                    FlightWatch.user_id == user_id,
                )
            )
            is not None
        )
    return False


def list_notification_inbox(db: Session, *, user_id: str, limit: int = 80) -> list[InboxItem]:
    bounded_limit = min(max(limit, 1), 200)
    security_limit = min(bounded_limit, 20)
    alert_rows = list(
        db.execute(
            select(NotificationEvent, AlertRule, FlightWatch)
            .join(AlertRule, NotificationEvent.rule_id == AlertRule.id)
            .join(FlightWatch, AlertRule.watch_id == FlightWatch.id)
            .where(FlightWatch.user_id == user_id)
            .order_by(desc(NotificationEvent.created_at), desc(NotificationEvent.id))
            .limit(bounded_limit)
        ).all()
    )
    security_rows = list(
        db.scalars(
            select(SecurityActivity)
            .where(SecurityActivity.user_id == user_id)
            .order_by(desc(SecurityActivity.created_at), desc(SecurityActivity.id))
            .limit(security_limit)
        ).all()
    )
    refs = [
        (SOURCE_ALERT_EVENT, event.id)
        for event, _, _ in alert_rows
    ] + [(SOURCE_SECURITY_ACTIVITY, activity.id) for activity in security_rows]
    states = _state_map(db, user_id=user_id, source_refs=refs)

    items: list[InboxItem] = []
    for event, _, watch in alert_rows:
        category = _alert_category(event)
        route_label = f"{watch.origin_iata} -> {watch.destination_iata}"
        items.append(
            InboxItem(
                id=f"{SOURCE_ALERT_EVENT}:{event.id}",
                source_type=SOURCE_ALERT_EVENT,
                source_id=event.id,
                category=category,
                tone=_alert_tone(event),
                title=_alert_title(event, category),
                body=event.message,
                route_label=route_label,
                action_href=f"/alerts?watch_id={watch.id}",
                created_at=event.created_at,
                read_at=states.get((SOURCE_ALERT_EVENT, event.id)),
            )
        )

    for activity in security_rows:
        items.append(
            InboxItem(
                id=f"{SOURCE_SECURITY_ACTIVITY}:{activity.id}",
                source_type=SOURCE_SECURITY_ACTIVITY,
                source_id=activity.id,
                category="security",
                tone="info",
                title=_security_title(activity.event_type),
                body=_security_body(activity),
                route_label=None,
                action_href="/cuenta/seguridad",
                created_at=activity.created_at,
                read_at=states.get((SOURCE_SECURITY_ACTIVITY, activity.id)),
            )
        )

    return sorted(items, key=lambda item: (item.created_at, item.id), reverse=True)[:bounded_limit]


def mark_notification_read(
    db: Session,
    *,
    user_id: str,
    source_type: str,
    source_id: str,
) -> datetime | None:
    if source_type not in READABLE_SOURCES:
        return None
    if not _source_belongs_to_user(db, user_id=user_id, source_type=source_type, source_id=source_id):
        return None
    now = utc_now_naive()
    existing = db.scalar(
        select(UserNotificationState).where(
            UserNotificationState.user_id == user_id,
            UserNotificationState.source_type == source_type,
            UserNotificationState.source_id == source_id,
        )
    )
    if existing:
        existing.read_at = now
    else:
        db.add(
            UserNotificationState(
                user_id=user_id,
                source_type=source_type,
                source_id=source_id,
                read_at=now,
            )
        )
    db.commit()
    return now


def mark_all_notifications_read(db: Session, *, user_id: str) -> int:
    items = list_notification_inbox(db, user_id=user_id, limit=200)
    unread_items = [item for item in items if not item.is_read]
    for item in unread_items:
        mark_notification_read(
            db,
            user_id=user_id,
            source_type=item.source_type,
            source_id=item.source_id,
        )
    return len(unread_items)
