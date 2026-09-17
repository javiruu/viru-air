import logging
import os

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_errors import ADMIN_REQUIRED, INVALID_AUTH
from app.core.time import utc_now_naive
from app.infrastructure.db.models import SecurityActivity, User, UserSession
from app.infrastructure.db.session import get_db

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

_PLACEHOLDER_SECRETS = frozenset({"change-me", "dev-secret-token-key-placeholder"})


def resolve_supabase_jwt_secret(env: dict[str, str] | None = None) -> str:
    """Resolve the JWT verification secret, failing closed on empty/placeholder values.

    Access tokens are Supabase-issued (HS256). `SUPABASE_JWT_SECRET` is preferred;
    `JWT_SECRET` is kept as a local-development fallback (the launcher-generated
    backend/.env provides it) so the app can still boot, but Supabase-issued
    tokens will never verify against a legacy app secret, hence the warning.

    python-jose accepts HS256 with an empty key, so an unconfigured deployment
    would trust forged tokens. We refuse to start instead of failing open.
    """
    source = os.environ if env is None else env
    supabase_secret = (source.get("SUPABASE_JWT_SECRET") or "").strip()
    legacy_secret = (source.get("JWT_SECRET") or "").strip()
    secret = supabase_secret or legacy_secret

    if not secret or secret in _PLACEHOLDER_SECRETS:
        raise RuntimeError(
            "Authentication is not configured: SUPABASE_JWT_SECRET "
            "(or JWT_SECRET for local development) must be set to a strong, "
            "non-placeholder value. Refusing to start with an empty or "
            "placeholder JWT secret because HS256 tokens signed with an empty "
            "key would be accepted."
        )

    if not supabase_secret and legacy_secret:
        logger.warning(
            "SUPABASE_JWT_SECRET is not set; falling back to legacy JWT_SECRET. "
            "Tokens issued by Supabase Auth will NOT verify against this secret; "
            "only locally minted development tokens will."
        )
    return secret


SUPABASE_JWT_SECRET: str = resolve_supabase_jwt_secret()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=INVALID_AUTH,
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise credentials_exception from exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        user = _provision_user_from_claims(request, db, payload, user_id)
    if not user:
        raise credentials_exception

    return user


def _provision_user_from_claims(
    request: Request,
    db: Session,
    payload: dict,
    user_id: str,
) -> User | None:
    """Create the local user row for a Supabase-verified identity (first login).

    Hardening policy (2026-09-16):
    - Provision only when the token carries a confirmed email claim
      (`email_verified` is set by Supabase once the address is confirmed).
    - Never derive admin rights from token claims; `is_admin` is granted
      explicitly in the database by an operator.
    - Record security activity with the real client IP and user agent instead
      of placeholder values, so the audit trail stays truthful.
    """
    email = (payload.get("email") or "").strip()
    email_verified = payload.get("email_verified") is True
    if not email or not email_verified:
        return None

    client = request.client
    ip = client.host if client and client.host else "desconocida"
    user_agent = (request.headers.get("user-agent") or "Desconocido")[:255]

    user = User(
        id=user_id,
        email=email,
        password_hash="[SUPABASE_AUTH_MANAGED]",
        is_verified=True,
        is_admin=False,
    )
    db.add(user)
    db.flush()
    db.add(UserSession(
        user_id=user.id,
        device=user_agent,
        ip=ip,
        last_seen=utc_now_naive(),
        created_at=utc_now_naive(),
        is_active=True,
    ))
    db.add(SecurityActivity(
        user_id=user.id,
        event_type="login",
        ip=ip,
        created_at=utc_now_naive(),
    ))
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        # Concurrent first-logins can race on the primary key; the winner
        # committed the row, so re-read it instead of failing the request.
        db.rollback()
        return db.scalar(select(User).where(User.id == user_id))
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ADMIN_REQUIRED)
    return current_user
