from datetime import datetime

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import (
    AlertRule,
    FlightWatch,
    HotelAlertEvent,
    HotelAlertRule,
    HotelProperty,
    HotelTrackedOffer,
    NotificationEvent,
    SecurityActivity,
    UserNotificationState,
)
from app.services.notification_inbox_sources import (
    READABLE_SOURCES,
    SOURCE_ALERT_EVENT,
    SOURCE_HOTEL_ALERT_EVENT,
    SOURCE_SECURITY_ACTIVITY,
    InboxItem,
    SourceRef,
    alert_item,
    alert_ref,
    hotel_alert_item,
    hotel_alert_ref,
    security_item,
    security_ref,
)


def _state_map(
    db: Session,
    *,
    user_id: str,
    source_refs: list[SourceRef],
) -> dict[SourceRef, datetime]:
    if not source_refs:
        return {}
    wanted = set(source_refs)
    rows = db.scalars(
        select(UserNotificationState).where(
            UserNotificationState.user_id == user_id,
            UserNotificationState.source_type.in_({ref.source_type for ref in source_refs}),
            UserNotificationState.source_id.in_({ref.source_id for ref in source_refs}),
        )
    ).all()
    return {
        SourceRef(row.source_type, row.source_id): row.read_at
        for row in rows
        if SourceRef(row.source_type, row.source_id) in wanted
    }


def _source_belongs_to_user(
    db: Session,
    *,
    user_id: str,
    ref: SourceRef,
) -> bool:
    if ref.source_type == SOURCE_SECURITY_ACTIVITY:
        return (
            db.scalar(
                select(SecurityActivity.id).where(
                    SecurityActivity.id == ref.source_id,
                    SecurityActivity.user_id == user_id,
                )
            )
            is not None
        )
    if ref.source_type == SOURCE_ALERT_EVENT:
        return (
            db.scalar(
                select(NotificationEvent.id)
                .join(AlertRule, NotificationEvent.rule_id == AlertRule.id)
                .join(FlightWatch, AlertRule.watch_id == FlightWatch.id)
                .where(
                    NotificationEvent.id == ref.source_id,
                    FlightWatch.user_id == user_id,
                )
            )
            is not None
        )
    if ref.source_type == SOURCE_HOTEL_ALERT_EVENT:
        rule_owned = db.scalar(
            select(HotelAlertEvent.id)
            .join(HotelAlertRule, HotelAlertEvent.rule_id == HotelAlertRule.id)
            .where(
                HotelAlertEvent.id == ref.source_id,
                HotelAlertRule.user_id == user_id,
            )
        )
        if rule_owned is not None:
            return True
        return (
            db.scalar(
                select(HotelAlertEvent.id)
                .join(HotelTrackedOffer, HotelAlertEvent.hotel_id == HotelTrackedOffer.hotel_id)
                .where(
                    HotelAlertEvent.id == ref.source_id,
                    HotelTrackedOffer.user_id == user_id,
                )
            )
            is not None
        )
    return False


def list_notification_inbox(db: Session, *, user_id: str, limit: int = 80) -> list[InboxItem]:
    bounded_limit = min(max(limit, 1), 200)
    security_limit = min(bounded_limit, 20)
    hotel_limit = min(bounded_limit, 40)
    rule_hotel_ids = select(HotelAlertRule.hotel_id).where(HotelAlertRule.user_id == user_id)
    tracked_hotel_ids = select(HotelTrackedOffer.hotel_id).where(HotelTrackedOffer.user_id == user_id)
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
    hotel_rows = list(
        db.execute(
            select(HotelAlertEvent, HotelProperty)
            .join(HotelProperty, HotelAlertEvent.hotel_id == HotelProperty.id)
            .where(
                or_(
                    HotelAlertEvent.hotel_id.in_(rule_hotel_ids),
                    HotelAlertEvent.hotel_id.in_(tracked_hotel_ids),
                )
            )
            .order_by(desc(HotelAlertEvent.created_at), desc(HotelAlertEvent.id))
            .limit(hotel_limit)
        ).all()
    )
    refs = (
        [alert_ref(event) for event, _, _ in alert_rows]
        + [hotel_alert_ref(event) for event, _ in hotel_rows]
        + [security_ref(activity) for activity in security_rows]
    )
    states = _state_map(db, user_id=user_id, source_refs=refs)

    items: list[InboxItem] = []
    for event, _, watch in alert_rows:
        items.append(alert_item(event, watch, states.get(alert_ref(event))))

    for event, hotel in hotel_rows:
        items.append(hotel_alert_item(event, hotel, states.get(hotel_alert_ref(event))))

    for activity in security_rows:
        items.append(security_item(activity, states.get(security_ref(activity))))

    return sorted(items, key=lambda item: (item.created_at, item.id), reverse=True)[:bounded_limit]


def mark_notification_read(
    db: Session,
    *,
    user_id: str,
    ref: SourceRef,
) -> datetime | None:
    if ref.source_type not in READABLE_SOURCES:
        return None
    if not _source_belongs_to_user(db, user_id=user_id, ref=ref):
        return None
    now = utc_now_naive()
    existing = db.scalar(
        select(UserNotificationState).where(
            UserNotificationState.user_id == user_id,
            UserNotificationState.source_type == ref.source_type,
            UserNotificationState.source_id == ref.source_id,
        )
    )
    if existing:
        existing.read_at = now
    else:
        db.add(
            UserNotificationState(
                user_id=user_id,
                source_type=ref.source_type,
                source_id=ref.source_id,
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
            ref=SourceRef(item.source_type, item.source_id),
        )
    return len(unread_items)
