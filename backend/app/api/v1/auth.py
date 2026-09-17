from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import AuthOut, ForgotPasswordIn, LoginIn, MeOut, RefreshIn, RegisterIn, ResetPasswordIn
from app.infrastructure.db.models import User
from app.infrastructure.db.session import get_db

router = APIRouter()


@router.post("/register", response_model=AuthOut)
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="auth_managed_by_supabase",
    )


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="auth_managed_by_supabase",
    )


@router.post("/refresh", response_model=AuthOut)
def refresh(payload: RefreshIn, request: Request, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="auth_managed_by_supabase",
    )


@router.get("/me", response_model=MeOut)
def me(current_user: User = Depends(get_current_user)) -> MeOut:
    return MeOut(
        id=current_user.id,
        email=current_user.email,
        is_verified=current_user.is_verified,
        is_admin=current_user.is_admin,
        locale=current_user.locale,
        timezone=current_user.timezone,
    )


@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user)) -> dict:
    return {"status": "ok"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)) -> dict:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="auth_managed_by_supabase",
    )


@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)) -> dict:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="auth_managed_by_supabase",
    )

