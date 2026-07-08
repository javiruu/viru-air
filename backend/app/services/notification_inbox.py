from datetime import datetime

from sqlalchemy import and_, case, desc, func, or_, select
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
    """Mark all unread notifications as read using bulk SQL operations."""
    items = list_notification_inbox(db, user_id=user_id, limit=200)
    unread_items = [item for item in items if not item.is_read]
    if not unread_items:
        return 0

    now = utc_now_naive()
    # Bulk-update existing rows
    existing_pairs = {
        (item.source_type, item.source_id)
        for item in unread_items
    }
    existing_rows = db.scalars(
        select(UserNotificationState).where(
            UserNotificationState.user_id == user_id,
            UserNotificationState.source_type.in_({p[0] for p in existing_pairs}),
            UserNotificationState.source_id.in_({p[1] for p in existing_pairs}),
        )
    ).all()
    existing_pairs_found: set[tuple[str, str]] = set()
    for row in existing_rows:
        row.read_at = now
        existing_pairs_found.add((row.source_type, row.source_id))

    # Insert new rows for items not yet in state table
    new_items = [
        item for item in unread_items
        if (item.source_type, item.source_id) not in existing_pairs_found
    ]
    if new_items:
        db.add_all([
            UserNotificationState(
                user_id=user_id,
                source_type=item.source_type,
                source_id=item.source_id,
                read_at=now,
            )
            for item in new_items
        ])

    db.commit()
    return len(unread_items)


def count_notification_summary(db: Session, *, user_id: str) -> dict[str, int]:
    """Lightweight summary using SQL COUNT queries instead of fetching full rows."""
    # Count alert events for this user
    alert_count = db.scalar(
        select(func.count(NotificationEvent.id))
        .join(AlertRule, NotificationEvent.rule_id == AlertRule.id)
        .join(FlightWatch, AlertRule.watch_id == FlightWatch.id)
        .where(FlightWatch.user_id == user_id)
    ) or 0

    # Count security activities
    security_count = db.scalar(
        select(func.count(SecurityActivity.id))
        .where(SecurityActivity.user_id == user_id)
    ) or 0

    # Count hotel alert events
    rule_hotel_ids = select(HotelAlertRule.hotel_id).where(HotelAlertRule.user_id == user_id)
    tracked_hotel_ids = select(HotelTrackedOffer.hotel_id).where(HotelTrackedOffer.user_id == user_id)
    hotel_count = db.scalar(
        select(func.count(HotelAlertEvent.id))
        .where(
            or_(
                HotelAlertEvent.hotel_id.in_(rule_hotel_ids),
                HotelAlertEvent.hotel_id.in_(tracked_hotel_ids),
            )
        )
    ) or 0

    total = alert_count + security_count + hotel_count

    # Count unread: items NOT in user_notification_state
    # For alerts
    read_alert_ids = select(UserNotificationState.source_id).where(
        UserNotificationState.user_id == user_id,
        UserNotificationState.source_type == SOURCE_ALERT_EVENT,
    )
    unread_alerts = db.scalar(
        select(func.count(NotificationEvent.id))
        .join(AlertRule, NotificationEvent.rule_id == AlertRule.id)
        .join(FlightWatch, AlertRule.watch_id == FlightWatch.id)
        .where(FlightWatch.user_id == user_id, NotificationEvent.id.not_in(read_alert_ids))
    ) or 0

    # For security
    read_security_ids = select(UserNotificationState.source_id).where(
        UserNotificationState.user_id == user_id,
        UserNotificationState.source_type == SOURCE_SECURITY_ACTIVITY,
    )
    unread_security = db.scalar(
        select(func.count(SecurityActivity.id))
        .where(SecurityActivity.user_id == user_id, SecurityActivity.id.not_in(read_security_ids))
    ) or 0

    # For hotels
    read_hotel_ids = select(UserNotificationState.source_id).where(
        UserNotificationState.user_id == user_id,
        UserNotificationState.source_type == SOURCE_HOTEL_ALERT_EVENT,
    )
    unread_hotels = db.scalar(
        select(func.count(HotelAlertEvent.id))
        .where(
            or_(
                HotelAlertEvent.hotel_id.in_(rule_hotel_ids),
                HotelAlertEvent.hotel_id.in_(tracked_hotel_ids),
            ),
            HotelAlertEvent.id.not_in(read_hotel_ids),
        )
    ) or 0

    unread = unread_alerts + unread_security + unread_hotels

    # Category breakdown from alert events using SQL CASE/WHEN (matching _alert_category logic)
    # _alert_category priority: worker > digest > price
    is_worker = or_(
        NotificationEvent.delivery_status.in_({"failed", "error"}),
        NotificationEvent.group_reason == "revalidation_failed",
    )
    is_digest = or_(
        NotificationEvent.is_digest == True,  # noqa: E712
        NotificationEvent.grouped_count > 1,
    )
    cat_row = db.execute(
        select(
            func.count(NotificationEvent.id).label("total_alerts"),
            func.sum(case((is_worker, 1), else_=0)).label("worker"),
            func.sum(case((and_(~is_worker, is_digest), 1), else_=0)).label("digest"),
        )
        .join(AlertRule, NotificationEvent.rule_id == AlertRule.id)
        .join(FlightWatch, AlertRule.watch_id == FlightWatch.id)
        .where(FlightWatch.user_id == user_id)
    ).one()
    total_alerts = int(cat_row.total_alerts or 0)
    worker_count = int(cat_row.worker or 0)
    digest_count = int(cat_row.digest or 0)
    price_count = total_alerts - worker_count - digest_count

    return {
        "total": total,
        "unread": unread,
        "price": price_count + hotel_count,
        "security": security_count,
        "digest": digest_count,
        "worker": worker_count,
    }
