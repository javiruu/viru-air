from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import NotificationInboxOut, NotificationInboxSummaryOut
from app.infrastructure.db.models import User
from app.infrastructure.db.session import get_db
from app.services.notification_inbox import (
    SourceRef,
    count_notification_summary,
    list_notification_inbox,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter()


@router.get("", response_model=NotificationInboxOut)
def get_notifications(
    limit: int = 80,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    items = list_notification_inbox(db, user_id=current_user.id, limit=limit)
    return {
        "items": [
            {
                "id": item.id,
                "source_type": item.source_type,
                "source_id": item.source_id,
                "category": item.category,
                "tone": item.tone,
                "title": item.title,
                "body": item.body,
                "route_label": item.route_label,
                "action_href": item.action_href,
                "created_at": item.created_at,
                "read_at": item.read_at,
                "is_read": item.is_read,
            }
            for item in items
        ],
        "summary": count_notification_summary(db, user_id=current_user.id),
    }


@router.get("/summary", response_model=NotificationInboxSummaryOut)
def get_notifications_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    return count_notification_summary(db, user_id=current_user.id)


@router.post("/{source_type}/{source_id}/read")
def mark_read(
    source_type: str,
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    read_at = mark_notification_read(
        db,
        user_id=current_user.id,
        ref=SourceRef(source_type, source_id),
    )
    if read_at is None:
        raise HTTPException(status_code=404, detail="notification_not_found")
    return {"status": "ok", "read_at": read_at.isoformat()}


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int | str]:
    updated = mark_all_notifications_read(db, user_id=current_user.id)
    return {"status": "ok", "updated": updated}
