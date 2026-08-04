from datetime import datetime

from sqlalchemy import and_, case, desc, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.domain.vocabulary import WATCH_STATUS_ACTIVE
from app.i18n import t
from app.infrastructure.db.models import (
    AlertRule,
    CommunityTrendingSnapshot,
    CommunityTrendingSnapshotRoute,
    FlightWatch,
    HotelAlertEvent,
    HotelAlertRule,
    HotelProperty,
    HotelTrackedOffer,
    NotificationEvent,
    SecurityActivity,
    UserNotificationState,
)
from app.services.community_trending_notifier import (
    build_community_trending_source_id,
    parse_community_trending_source_id,
)
from app.services.notification_inbox_sources import (
    READABLE_SOURCES,
    SOURCE_ALERT_EVENT,
    SOURCE_COMMUNITY_TRENDING,
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

COMMUNITY_INBOX_LIMIT = 20


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


def _latest_visible_community_snapshot(
    db: Session,
    *,
    now: datetime,
) -> CommunityTrendingSnapshot | None:
    return db.scalar(
        select(CommunityTrendingSnapshot)
        .where(
            CommunityTrendingSnapshot.status == "published",
            CommunityTrendingSnapshot.expires_at_utc > now,
        )
        .order_by(
            CommunityTrendingSnapshot.calculated_at_utc.desc(),
            CommunityTrendingSnapshot.id.desc(),
        )
        .limit(1)
    )


def _community_trending_items(
    db: Session,
    *,
    user_id: str,
    now: datetime | None = None,
    limit: int = COMMUNITY_INBOX_LIMIT,
) -> list[InboxItem]:
    visible_at = now or utc_now_naive()
    snapshot = _latest_visible_community_snapshot(db, now=visible_at)
    if snapshot is None:
        return []

    active_watch_for_route = exists(
        select(FlightWatch.id).where(
            FlightWatch.origin_iata == CommunityTrendingSnapshotRoute.origin_iata,
            FlightWatch.destination_iata == CommunityTrendingSnapshotRoute.destination_iata,
            FlightWatch.user_id == user_id,
            FlightWatch.status == WATCH_STATUS_ACTIVE,
        )
    )
    routes = db.scalars(
        select(CommunityTrendingSnapshotRoute)
        .where(
            CommunityTrendingSnapshotRoute.snapshot_id == snapshot.id,
            active_watch_for_route,
        )
        .order_by(
            CommunityTrendingSnapshotRoute.rank.asc(),
            CommunityTrendingSnapshotRoute.origin_iata.asc(),
            CommunityTrendingSnapshotRoute.destination_iata.asc(),
        )
        .limit(max(limit, 1))
    ).all()

    refs: list[SourceRef] = []
    item_data: list[tuple[SourceRef, str, datetime]] = []
    created_at = snapshot.published_at_utc or snapshot.calculated_at_utc
    for route in routes:
        source_id = build_community_trending_source_id(
            snapshot.reporting_date,
            route.origin_iata,
            route.destination_iata,
        )
        ref = SourceRef(SOURCE_COMMUNITY_TRENDING, source_id)
        refs.append(ref)
        item_data.append((ref, f"{route.origin_iata} → {route.destination_iata}", created_at))

    states = _state_map(db, user_id=user_id, source_refs=refs)
    return [
        InboxItem(
            id=f"{SOURCE_COMMUNITY_TRENDING}:{ref.source_id}",
            source_type=SOURCE_COMMUNITY_TRENDING,
            source_id=ref.source_id,
            category="community",
            tone="info",
            title=t("es", "notifications.community_trending_title"),
            body=f"{route_label} es una ruta en tendencia esta semana.",
            route_label=route_label,
            action_href="/dashboard",
            created_at=created_at,
            read_at=states.get(ref),
        )
        for ref, route_label, created_at in item_data
    ]


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
    if ref.source_type == SOURCE_COMMUNITY_TRENDING:
        parsed = parse_community_trending_source_id(ref.source_id)
        if parsed is None:
            return False
        reporting_date, origin_iata, destination_iata = parsed
        snapshot = _latest_visible_community_snapshot(db, now=utc_now_naive())
        if snapshot is None or snapshot.reporting_date != reporting_date:
            return False
        return (
            db.scalar(
                select(CommunityTrendingSnapshotRoute.id)
                .join(
                    FlightWatch,
                    and_(
                        FlightWatch.origin_iata == CommunityTrendingSnapshotRoute.origin_iata,
                        FlightWatch.destination_iata == CommunityTrendingSnapshotRoute.destination_iata,
                        FlightWatch.user_id == user_id,
                        FlightWatch.status == WATCH_STATUS_ACTIVE,
                    ),
                )
                .where(
                    CommunityTrendingSnapshotRoute.snapshot_id == snapshot.id,
                    CommunityTrendingSnapshotRoute.origin_iata == origin_iata,
                    CommunityTrendingSnapshotRoute.destination_iata == destination_iata,
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


def list_notification_inbox(
    db: Session,
    *,
    user_id: str,
    limit: int = 80,
    community_limit: int = COMMUNITY_INBOX_LIMIT,
) -> list[InboxItem]:
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
    trending_items = _community_trending_items(
        db,
        user_id=user_id,
        limit=min(max(community_limit, 1), 200),
    )
    refs = (
        [alert_ref(event) for event, _, _ in alert_rows]
        + [hotel_alert_ref(event) for event, _ in hotel_rows]
        + [security_ref(activity) for activity in security_rows]
    )
    states = _state_map(db, user_id=user_id, source_refs=refs)

    items: list[InboxItem] = list(trending_items)
    items.extend(
        alert_item(event, watch, states.get(alert_ref(event)))
        for event, _, watch in alert_rows
    )
    items.extend(
        hotel_alert_item(event, hotel, states.get(hotel_alert_ref(event)))
        for event, hotel in hotel_rows
    )
    items.extend(
        security_item(activity, states.get(security_ref(activity)))
        for activity in security_rows
    )

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
    items = list_notification_inbox(
        db,
        user_id=user_id,
        limit=200,
        community_limit=200,
    )
    community_items = _community_trending_items(db, user_id=user_id, limit=200)
    existing_item_keys = {(item.source_type, item.source_id) for item in items}
    items.extend(
        item
        for item in community_items
        if (item.source_type, item.source_id) not in existing_item_keys
    )
    unread_items = [item for item in items if not item.is_read]
    if not unread_items:
        return 0

    now = utc_now_naive()
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

    new_items = [
        item
        for item in unread_items
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
    alert_count = db.scalar(
        select(func.count(NotificationEvent.id))
        .join(AlertRule, NotificationEvent.rule_id == AlertRule.id)
        .join(FlightWatch, AlertRule.watch_id == FlightWatch.id)
        .where(FlightWatch.user_id == user_id)
    ) or 0

    security_count = db.scalar(
        select(func.count(SecurityActivity.id))
        .where(SecurityActivity.user_id == user_id)
    ) or 0

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

    community_items = _community_trending_items(
        db,
        user_id=user_id,
        limit=COMMUNITY_INBOX_LIMIT,
    )
    community_count = len(community_items)
    total = alert_count + security_count + hotel_count + community_count

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

    read_security_ids = select(UserNotificationState.source_id).where(
        UserNotificationState.user_id == user_id,
        UserNotificationState.source_type == SOURCE_SECURITY_ACTIVITY,
    )
    unread_security = db.scalar(
        select(func.count(SecurityActivity.id))
        .where(SecurityActivity.user_id == user_id, SecurityActivity.id.not_in(read_security_ids))
    ) or 0

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

    community_refs = [SourceRef(item.source_type, item.source_id) for item in community_items]
    community_states = _state_map(db, user_id=user_id, source_refs=community_refs)
    unread_community = sum(
        1
        for item in community_items
        if community_states.get(SourceRef(item.source_type, item.source_id)) is None
    )
    unread = unread_alerts + unread_security + unread_hotels + unread_community

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
        "community": community_count,
    }
