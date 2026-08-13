from app.core.time import utc_now_naive

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from passlib.context import CryptContext
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.auth_errors import INVALID_AUTH
from app.domain.schemas import PasswordChangeIn, ProfileUpdateIn
from app.infrastructure.db.models import (
    AlertRule,
    FlightWatch,
    HotelAlertEvent,
    HotelAlertRule,
    HotelCompSet,
    HotelCompSetMember,
    HotelTrackedOffer,
    HotelWatchlistItem,
    NotificationEvent,
    PriceSnapshot,
    SecurityActivity,
    SupportFeedback,
    Suggestion,
    IdempotencyRecord,
    User,
    UserNote,
    UserPreference,
    UserPreferenceAppearance,
    UserPreferenceRegion,
    UserProfile,
    UserNotificationState,
    UserSession,
)
from app.infrastructure.db.session import get_db
from app.services.security_activity import log_security_event

router = APIRouter()
pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def ensure_profile(db: Session, user: User) -> UserProfile:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if profile:
        return profile
    display = user.email.split("@")[0] if user.email else "Usuario"
    profile = UserProfile(user_id=user.id, display_name=display, status="activa")
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile")
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    profile = ensure_profile(db, current_user)
    return {
        "display_name": profile.display_name,
        "email": current_user.email,
        "avatar_url": profile.avatar_url,
        "status": profile.status,
        "created_at": current_user.created_at,
        "locale": current_user.locale,
        "timezone": current_user.timezone,
    }


@router.put("/profile")
def update_profile(
    payload: ProfileUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    profile = ensure_profile(db, current_user)
    if payload.display_name is not None:
        profile.display_name = payload.display_name.strip()
    if payload.avatar_url is not None:
        profile.avatar_url = payload.avatar_url.strip() or None
    normalized_email = payload.email.strip().lower() if payload.email else None
    if normalized_email and normalized_email != current_user.email.lower():
        existing = db.scalar(select(User).where(User.email == normalized_email))
        if existing:
            raise HTTPException(status_code=409, detail="email_exists")
        current_user.email = normalized_email
    db.commit()
    return {
        "display_name": profile.display_name,
        "email": current_user.email,
        "avatar_url": profile.avatar_url,
        "status": profile.status,
        "created_at": current_user.created_at,
        "locale": current_user.locale,
        "timezone": current_user.timezone,
    }


@router.get("/sessions")
def get_sessions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=100_000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    sessions = db.scalars(
        select(UserSession)
        .where(UserSession.user_id == current_user.id)
        .order_by(UserSession.last_seen.desc(), UserSession.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    data = [
        {
            "id": session.id,
            "device": session.device,
            "ip": session.ip,
            "last_seen": session.last_seen,
            "created_at": session.created_at,
            "is_active": session.is_active,
        }
        for session in sessions
    ]
    return {"items": data}


@router.post("/sessions/close_all")
def close_all_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == current_user.id)
        .values(is_active=False, last_seen=utc_now_naive())
    )
    log_security_event(db, current_user.id, "close_all_sessions", None)
    db.commit()
    return {"status": "ok"}


@router.post("/security/password")
def change_password(
    payload: PasswordChangeIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not pwd.verify(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail=INVALID_AUTH)
    current_user.password_hash = pwd.hash(payload.new_password)
    log_security_event(db, current_user.id, "password_change", request.client.host if request.client else None)
    db.commit()
    return {"status": "ok"}


@router.get("/security/activity")
def security_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    items = db.scalars(
        select(SecurityActivity)
        .where(SecurityActivity.user_id == current_user.id)
        .order_by(SecurityActivity.created_at.desc(), SecurityActivity.id.desc())
        .limit(20)
    ).all()
    return {
        "items": [
            {
                "event_type": item.event_type,
                "ip": item.ip,
                "created_at": item.created_at,
            }
            for item in items
        ]
    }


@router.delete("")
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    watch_ids = db.scalars(select(FlightWatch.id).where(FlightWatch.user_id == current_user.id)).all()
    if watch_ids:
        db.execute(delete(NotificationEvent).where(NotificationEvent.rule_id.in_(
            select(AlertRule.id).where(AlertRule.watch_id.in_(watch_ids))
        )))
        db.execute(delete(AlertRule).where(AlertRule.watch_id.in_(watch_ids)))
        db.execute(delete(PriceSnapshot).where(PriceSnapshot.watch_id.in_(watch_ids)))
        db.execute(delete(FlightWatch).where(FlightWatch.id.in_(watch_ids)))

    hotel_rule_ids = db.scalars(select(HotelAlertRule.id).where(HotelAlertRule.user_id == current_user.id)).all()
    if hotel_rule_ids:
        db.execute(delete(HotelAlertEvent).where(HotelAlertEvent.rule_id.in_(hotel_rule_ids)))
        db.execute(delete(HotelAlertRule).where(HotelAlertRule.id.in_(hotel_rule_ids)))
    comp_set_ids = db.scalars(select(HotelCompSet.id).where(HotelCompSet.user_id == current_user.id)).all()
    if comp_set_ids:
        db.execute(delete(HotelCompSetMember).where(HotelCompSetMember.comp_set_id.in_(comp_set_ids)))
        db.execute(delete(HotelCompSet).where(HotelCompSet.id.in_(comp_set_ids)))
    # Events generated by tracked offers have no rule_id, so remove them
    # explicitly before deleting the owned offers. Rule-linked events were
    # removed above with the user's alert rules.
    db.execute(delete(HotelAlertEvent).where(HotelAlertEvent.user_id == current_user.id))
    db.execute(delete(HotelTrackedOffer).where(HotelTrackedOffer.user_id == current_user.id))
    db.execute(delete(HotelWatchlistItem).where(HotelWatchlistItem.user_id == current_user.id))

    db.execute(delete(UserNote).where(UserNote.user_id == current_user.id))
    db.execute(delete(Suggestion).where(Suggestion.user_id == current_user.id))
    db.execute(delete(UserPreference).where(UserPreference.user_id == current_user.id))
    db.execute(delete(UserPreferenceAppearance).where(UserPreferenceAppearance.user_id == current_user.id))
    db.execute(delete(UserPreferenceRegion).where(UserPreferenceRegion.user_id == current_user.id))
    db.execute(delete(UserProfile).where(UserProfile.user_id == current_user.id))
    db.execute(delete(UserNotificationState).where(UserNotificationState.user_id == current_user.id))
    db.execute(delete(UserSession).where(UserSession.user_id == current_user.id))
    db.execute(delete(SecurityActivity).where(SecurityActivity.user_id == current_user.id))
    db.execute(delete(SupportFeedback).where(SupportFeedback.user_id == current_user.id))
    db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.user_id == current_user.id))
    db.execute(delete(User).where(User.id == current_user.id))
    db.commit()
    return {"status": "ok"}
