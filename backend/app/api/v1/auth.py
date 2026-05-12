from app.core.time import utc_now_naive

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.auth_errors import INVALID_AUTH
from app.api.deps import get_current_user
from app.core.security import (
    RESET_TOKEN_MINUTES,
    REFRESH_TOKEN_DAYS,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    hash_ip,
    hash_token,
)
from app.domain.schemas import AuthOut, ForgotPasswordIn, LoginIn, MeOut, RefreshIn, RegisterIn, ResetPasswordIn
from app.infrastructure.db.models import PasswordResetToken, RefreshToken, User, UserSession
from app.infrastructure.db.session import get_db
from app.services.security_activity import log_security_event

router = APIRouter()
pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
GENERIC_FORGOT_PASSWORD_MESSAGE = "Si el correo existe, te enviaremos instrucciones."


def _create_refresh_token_record(user_id: str, request: Request) -> tuple[str, RefreshToken]:
    raw_token = create_refresh_token()
    now = utc_now_naive()
    record = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        created_at=now,
        expires_at=now + timedelta(days=REFRESH_TOKEN_DAYS),
        user_agent=(request.headers.get("user-agent") or "")[:255] or None,
        ip_hash=hash_ip(request.client.host if request.client else None),
    )
    return raw_token, record


@router.post("/register", response_model=AuthOut)
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)) -> AuthOut:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="email_exists")
    user = User(email=payload.email.lower(), password_hash=pwd.hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    log_security_event(db, user.id, "register", request.client.host if request.client else None)
    db.commit()
    return AuthOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)) -> AuthOut:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not pwd.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail=INVALID_AUTH)
    client_ip = request.client.host if request.client else None
    agent = request.headers.get("user-agent") or "Este dispositivo"
    db.add(
        UserSession(
            user_id=user.id,
            device=agent[:200],
            ip=client_ip,
            last_seen=utc_now_naive(),
            created_at=utc_now_naive(),
            is_active=True,
        )
    )
    refresh_token, refresh_record = _create_refresh_token_record(user.id, request)
    db.add(refresh_record)
    log_security_event(db, user.id, "login", client_ip)
    db.commit()
    return AuthOut(access_token=create_access_token(user.id), refresh_token=refresh_token)


@router.get("/me", response_model=MeOut)
def me(current_user: User = Depends(get_current_user)) -> MeOut:
    return MeOut(
        id=current_user.id,
        email=current_user.email,
        locale=current_user.locale,
        is_admin=current_user.is_admin,
    )


@router.post("/refresh", response_model=AuthOut)
def refresh(payload: RefreshIn, request: Request, db: Session = Depends(get_db)) -> AuthOut:
    token_hash = hash_token(payload.refresh_token)
    refresh_record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = utc_now_naive()
    if not refresh_record or refresh_record.revoked_at is not None or refresh_record.expires_at <= now:
        raise HTTPException(status_code=401, detail=INVALID_AUTH)

    user = db.scalar(select(User).where(User.id == refresh_record.user_id))
    if not user:
        raise HTTPException(status_code=401, detail=INVALID_AUTH)

    next_token, next_record = _create_refresh_token_record(user.id, request)
    db.add(next_record)
    db.flush()
    refresh_record.revoked_at = now
    refresh_record.replaced_by_token_id = next_record.id
    log_security_event(db, user.id, "refresh", request.client.host if request.client else None)
    db.commit()
    return AuthOut(access_token=create_access_token(user.id), refresh_token=next_token)


@router.post("/logout")
def logout(
    payload: RefreshIn | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if payload and payload.refresh_token:
        token_hash = hash_token(payload.refresh_token)
        refresh_record = db.scalar(
            select(RefreshToken).where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.token_hash == token_hash,
            )
        )
        if refresh_record and refresh_record.revoked_at is None:
            refresh_record.revoked_at = utc_now_naive()
            db.commit()
    return {"status": "ok"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user:
        raw_token = create_reset_token()
        now = utc_now_naive()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                created_at=now,
                expires_at=now + timedelta(minutes=RESET_TOKEN_MINUTES),
            )
        )
        log_security_event(db, user.id, "forgot_password_requested", None)
        db.commit()
    return {"message": GENERIC_FORGOT_PASSWORD_MESSAGE}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)) -> dict[str, str]:
    token_hash = hash_token(payload.token)
    now = utc_now_naive()
    reset_record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if not reset_record or reset_record.used_at is not None or reset_record.expires_at <= now:
        raise HTTPException(status_code=401, detail=INVALID_AUTH)

    user = db.scalar(select(User).where(User.id == reset_record.user_id))
    if not user:
        raise HTTPException(status_code=401, detail=INVALID_AUTH)

    user.password_hash = pwd.hash(payload.new_password)
    reset_record.used_at = now
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    log_security_event(db, user.id, "password_reset", None)
    db.commit()
    return {"status": "ok"}
