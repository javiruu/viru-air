from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from datetime import timedelta

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.time import utc_now_naive
from app.domain.schemas import (
    AdminPasswordIn,
    AdminProductMetricsOut,
    AdminUserOut,
    AdminUserUpdateIn,
    WatchCreateIn,
    WatchOut,
)
from app.infrastructure.db.models import (
    AlertRule,
    FlightWatch,
    NotificationEvent,
    PriceSnapshot,
    Suggestion,
    ClientErrorEvent,
    User,
    UserPreference,
    UxEvent,
)
from app.infrastructure.db.session import get_db

router = APIRouter()
pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _delete_watch(db: Session, watch_id: str) -> None:
    rule_ids = db.scalars(select(AlertRule.id).where(AlertRule.watch_id == watch_id)).all()
    if rule_ids:
        db.execute(delete(NotificationEvent).where(NotificationEvent.rule_id.in_(rule_ids)))
        db.execute(delete(AlertRule).where(AlertRule.id.in_(rule_ids)))
    db.execute(delete(PriceSnapshot).where(PriceSnapshot.watch_id == watch_id))
    db.execute(delete(FlightWatch).where(FlightWatch.id == watch_id))


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[AdminUserOut]:
    users = db.scalars(select(User)).all()
    return [
        AdminUserOut(
            id=u.id,
            email=u.email,
            is_admin=u.is_admin,
            is_verified=u.is_verified,
            locale=u.locale,
            timezone=u.timezone,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: str,
    payload: AdminUserUpdateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminUserOut:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.is_verified is not None:
        user.is_verified = payload.is_verified
    if payload.locale is not None:
        user.locale = payload.locale
    if payload.timezone is not None:
        user.timezone = payload.timezone
    db.commit()
    db.refresh(user)
    return AdminUserOut(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        is_verified=user.is_verified,
        locale=user.locale,
        timezone=user.timezone,
        created_at=user.created_at,
    )


@router.put("/users/{user_id}/password")
def reset_password(
    user_id: str,
    payload: AdminPasswordIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    user.password_hash = pwd.hash(payload.password)
    db.commit()
    return {"status": "ok"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")

    watch_ids = db.scalars(select(FlightWatch.id).where(FlightWatch.user_id == user_id)).all()
    for watch_id in watch_ids:
        _delete_watch(db, watch_id)

    db.execute(delete(UserPreference).where(UserPreference.user_id == user_id))
    db.execute(delete(Suggestion).where(Suggestion.user_id == user_id))
    db.execute(delete(User).where(User.id == user_id))
    db.commit()
    return {"status": "ok"}


@router.get("/users/{user_id}/watchlist", response_model=list[WatchOut])
def list_user_watchlist(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[WatchOut]:
    watches = db.scalars(select(FlightWatch).where(FlightWatch.user_id == user_id)).all()
    return [
        WatchOut(
            id=w.id,
            origin_iata=w.origin_iata,
            destination_iata=w.destination_iata,
            travel_date_local=w.travel_date_local,
            target_price=w.target_price,
            status=w.status,
        )
        for w in watches
    ]


@router.post("/users/{user_id}/watchlist", response_model=WatchOut)
def create_watch_for_user(
    user_id: str,
    payload: WatchCreateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> WatchOut:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    watch = FlightWatch(
        user_id=user_id,
        origin_iata=payload.origin_iata,
        destination_iata=payload.destination_iata,
        travel_date_local=payload.travel_date_local,
        target_price=payload.target_price,
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return WatchOut(
        id=watch.id,
        origin_iata=watch.origin_iata,
        destination_iata=watch.destination_iata,
        travel_date_local=watch.travel_date_local,
        target_price=watch.target_price,
        status=watch.status,
    )


@router.delete("/watchlist/{watch_id}")
def delete_watch(
    watch_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    _delete_watch(db, watch_id)
    db.commit()
    return {"status": "ok"}


@router.get("/product-health")
def product_health(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    now = utc_now_naive()
    daily_from = now - timedelta(days=1)
    weekly_from = now - timedelta(days=7)

    core_events = [
        "dashboard_view",
        "quick_search_executed",
        "watchlist_refresh",
        "alert_created",
        "alert_triggered",
        "search_empty_results",
    ]

    usage: dict[str, dict[str, int | str]] = {}
    for event in core_events:
        daily_count = int(
            db.scalar(
                select(func.count(UxEvent.id)).where(
                    UxEvent.event_name == event,
                    UxEvent.created_at >= daily_from,
                )
            )
            or 0
        )
        weekly_count = int(
            db.scalar(
                select(func.count(UxEvent.id)).where(
                    UxEvent.event_name == event,
                    UxEvent.created_at >= weekly_from,
                )
            )
            or 0
        )
        usage[event] = {
            "daily": daily_count,
            "weekly": weekly_count,
            "trend": "up" if daily_count > 0 else "flat",
        }

    quick_search_count = usage["quick_search_executed"]["weekly"] if isinstance(usage["quick_search_executed"]["weekly"], int) else 0
    empty_count = usage["search_empty_results"]["weekly"] if isinstance(usage["search_empty_results"]["weekly"], int) else 0
    refresh_count = usage["watchlist_refresh"]["weekly"] if isinstance(usage["watchlist_refresh"]["weekly"], int) else 0
    alert_created_count = usage["alert_created"]["weekly"] if isinstance(usage["alert_created"]["weekly"], int) else 0
    dashboard_views = usage["dashboard_view"]["weekly"] if isinstance(usage["dashboard_view"]["weekly"], int) else 0

    quick_search_avg = float(
        db.scalar(
            select(func.avg(UxEvent.duration_ms)).where(
                UxEvent.event_name == "quick_search_executed",
                UxEvent.created_at >= weekly_from,
                UxEvent.duration_ms.is_not(None),
            )
        )
        or 0
    )
    dashboard_avg = float(
        db.scalar(
            select(func.avg(UxEvent.duration_ms)).where(
                UxEvent.event_name == "dashboard_view",
                UxEvent.created_at >= weekly_from,
                UxEvent.duration_ms.is_not(None),
            )
        )
        or 0
    )
    refresh_avg = float(
        db.scalar(
            select(func.avg(UxEvent.duration_ms)).where(
                UxEvent.event_name == "watchlist_refresh",
                UxEvent.created_at >= weekly_from,
                UxEvent.duration_ms.is_not(None),
            )
        )
        or 0
    )

    recent_errors = list(
        db.execute(
            select(ClientErrorEvent)
            .order_by(desc(ClientErrorEvent.created_at))
            .limit(10)
        ).scalars()
    )
    frequent_errors = list(
        db.execute(
            select(
                ClientErrorEvent.message,
                func.count(ClientErrorEvent.id).label("count"),
                func.max(ClientErrorEvent.created_at).label("last_seen"),
            )
            .group_by(ClientErrorEvent.message)
            .order_by(desc("count"))
            .limit(5)
        )
    )

    last_alert_execution = db.scalar(
        select(func.max(UxEvent.created_at)).where(UxEvent.event_name == "alert_triggered")
    )
    last_data_update = db.scalar(select(func.max(UxEvent.created_at)))

    error_count_weekly = int(
        db.scalar(select(func.count(ClientErrorEvent.id)).where(ClientErrorEvent.created_at >= weekly_from)) or 0
    )
    system_status = "ok"
    if error_count_weekly >= 25:
        system_status = "critical"
    elif error_count_weekly >= 5:
        system_status = "degraded"

    return {
        "usage": usage,
        "indicators": {
            "search_empty_rate_pct": round((empty_count / quick_search_count * 100.0), 2) if quick_search_count else 0.0,
            "watchlist_refresh_to_action_pct": round((alert_created_count / refresh_count * 100.0), 2) if refresh_count else 0.0,
            "alert_create_rate_pct": round((alert_created_count / dashboard_views * 100.0), 2) if dashboard_views else 0.0,
        },
        "performance": {
            "quick_search_avg_ms": round(quick_search_avg, 2),
            "dashboard_avg_ms": round(dashboard_avg, 2),
            "watchlist_refresh_avg_ms": round(refresh_avg, 2),
        },
        "errors": {
            "recent": [
                {
                    "section": item.section,
                    "message": item.message,
                    "created_at": item.created_at.isoformat(),
                }
                for item in recent_errors
            ],
            "frequent": [
                {
                    "message": row._mapping["message"],
                    "count": int(row._mapping["count"]),
                    "last_seen": row._mapping["last_seen"].isoformat() if row._mapping["last_seen"] else None,
                }
                for row in frequent_errors
            ],
            "last_occurrence": recent_errors[0].created_at.isoformat() if recent_errors else None,
        },
        "system": {
            "status": system_status,
            "last_data_update": last_data_update.isoformat() if last_data_update else None,
            "last_alert_execution": last_alert_execution.isoformat() if last_alert_execution else None,
        },
    }


@router.get("/product-metrics", response_model=AdminProductMetricsOut)
def product_metrics(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> AdminProductMetricsOut:
    def _count(event_name: str) -> int:
        return int(db.scalar(select(func.count(UxEvent.id)).where(UxEvent.event_name == event_name)) or 0)

    dashboard_views = _count("dashboard_view")
    quick_search_executed = _count("quick_search_executed")
    search_empty_results = _count("search_empty_results")
    watchlist_refresh = _count("watchlist_refresh")
    alert_created = _count("alert_created")
    alert_triggered = _count("alert_triggered")

    quick_search_avg_ms = float(
        db.scalar(
            select(func.avg(UxEvent.duration_ms)).where(
                UxEvent.event_name == "quick_search_executed",
                UxEvent.duration_ms.is_not(None),
            )
        )
        or 0
    )

    search_empty_rate_pct = (search_empty_results / quick_search_executed * 100.0) if quick_search_executed else 0.0
    watchlist_refresh_to_alert_created_pct = (alert_created / watchlist_refresh * 100.0) if watchlist_refresh else 0.0
    alert_created_rate_pct = (alert_created / dashboard_views * 100.0) if dashboard_views else 0.0

    return AdminProductMetricsOut(
        dashboard_views=dashboard_views,
        quick_search_executed=quick_search_executed,
        search_empty_results=search_empty_results,
        search_empty_rate_pct=round(search_empty_rate_pct, 2),
        quick_search_avg_ms=round(quick_search_avg_ms, 2),
        watchlist_refresh=watchlist_refresh,
        alert_created=alert_created,
        alert_triggered=alert_triggered,
        watchlist_refresh_to_alert_created_pct=round(watchlist_refresh_to_alert_created_pct, 2),
        alert_created_rate_pct=round(alert_created_rate_pct, 2),
    )
