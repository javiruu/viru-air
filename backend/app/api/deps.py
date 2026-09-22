import logging
import os
import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import httpx
from jose import JWTError, jwt
from jose.jws import verify as jws_verify
from jose.jwt import _validate_claims  # type: ignore[attr-defined]
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

    Two mutually exclusive verification modes:
    - HS256 (legacy projects): access tokens verify against a shared secret —
      `SUPABASE_JWT_SECRET` (preferred) or `JWT_SECRET` (local fallback).
    - ES256 (new projects with `sb_publishable_` keys): tokens verify against
      the project's public JWKS; only `SUPABASE_URL` is required and no shared
      secret exists. In this mode an empty secret is valid and HS256 tokens
      are rejected outright (see `get_current_user`).

    python-jose accepts HS256 with an empty key, so an HS256 deployment must
    never run with an empty/placeholder secret — hence the explicit failure
    below whenever `SUPABASE_URL` (ES256 mode) is not configured.
    """
    source = os.environ if env is None else env
    supabase_secret = (source.get("SUPABASE_JWT_SECRET") or "").strip()
    legacy_secret = (source.get("JWT_SECRET") or "").strip()
    secret = supabase_secret or legacy_secret
    supabase_url = (source.get("SUPABASE_URL") or "").strip()
    es256_mode = bool(supabase_url)

    if not secret or secret in _PLACEHOLDER_SECRETS:
        if es256_mode:
            return ""  # ES256/JWKS mode: no shared secret exists or is needed.
        raise RuntimeError(
            "Authentication is not configured: set SUPABASE_URL (asymmetric "
            "ES256/JWKS verification, new Supabase projects) or provide "
            "SUPABASE_JWT_SECRET (or JWT_SECRET for local development). "
            "Refusing to start with an empty or placeholder JWT secret "
            "because HS256 tokens signed with an empty key would be accepted."
        )

    if not supabase_secret and legacy_secret:
        logger.warning(
            "SUPABASE_JWT_SECRET is not set; falling back to legacy JWT_SECRET. "
            "Tokens issued by Supabase Auth will NOT verify against this secret; "
            "only locally minted development tokens will."
        )
    return secret


SUPABASE_JWT_SECRET: str = resolve_supabase_jwt_secret()

# --- Asymmetric signing keys (new Supabase projects, ES256) -----------------
# Projects created with the new API-key system (sb_publishable_/sb_secret_) sign
# access tokens with an asymmetric ES256 key instead of the legacy shared
# HS256 secret. Verification uses the project's public JWKS document, fetched
# over HTTPS and cached in-process; `SUPABASE_URL` must point at the Supabase
# project so the cache can be built. No shared secret is involved.
_JWKS_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/") + "/auth/v1/.well-known/jwks.json"
_JWKS_TTL_SECONDS = 3600.0
_JWKS_CACHE: tuple[float, dict] | None = None  # (fetched_at, jwks document)


def _fetch_supabase_jwks(force_refresh: bool = False) -> dict:
    """Fetch (and cache) the Supabase project JWKS, keyed by `kid`.

    Cached for `_JWKS_TTL_SECONDS`. `force_refresh=True` bypasses the cache:
    per Supabase's signing-keys guidance, an unknown `kid` must trigger one
    refetch because the token may be signed by a key that just rotated while
    our cache is still fresh (revocation is not instantaneous for backends
    that verify JWTs locally).
    """
    global _JWKS_CACHE
    now = time.monotonic()
    if not force_refresh and _JWKS_CACHE is not None and now - _JWKS_CACHE[0] < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE[1]
    response = httpx.get(_JWKS_URL, timeout=10.0)
    response.raise_for_status()
    jwks = response.json()
    if not isinstance(jwks, dict) or not jwks.get("keys"):
        raise JWTError("Supabase JWKS document does not contain any keys")
    _JWKS_CACHE = (now, jwks)
    return jwks


def _decode_es256_with_jwks(token: str) -> dict:
    """Verify an ES256 token against the cached Supabase JWKS.

    python-jose's high-level `jwt.decode` resolves algorithms from a static
    allowlist and does not select a key by `kid`, so the signature check is
    done with `jose.jws.verify` against the matching JWKS key and the claim
    validation with `jwt._validate_claims` (same exp/nbf/iat semantics as the
    HS256 path above).
    """
    from jose import jwk as jose_jwk

    header = jwt.get_unverified_header(token)
    if header.get("alg") != "ES256":
        raise JWTError("Token is not ES256")
    kid = header.get("kid")
    if not kid:
        raise JWTError("ES256 token is missing a `kid` header")

    jwks = _fetch_supabase_jwks()
    jwk_entry = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
    if jwk_entry is None:
        # Official Supabase guidance (signing-keys docs): a JWKS entry missing
        # for the presented kid can mean the key just rotated while our cache
        # was still fresh — force one refetch before rejecting the token.
        jwks = _fetch_supabase_jwks(force_refresh=True)
        jwk_entry = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
    if jwk_entry is None:
        raise JWTError(f"No JWKS key matches kid={kid}")

    public_key = jose_jwk.construct(jwk_entry)
    try:
        payload_bytes = jws_verify(token, public_key, "ES256")
    except JWTError:
        raise
    except Exception as exc:
        raise JWTError(f"ES256 signature verification failed: {exc}") from exc

    import json as _json
    claims = _json.loads(payload_bytes.decode("utf-8"))
    _validate_claims(claims, algorithm="ES256", options={"verify_aud": False, "verify_at_hash": False})
    return claims


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
        header = jwt.get_unverified_header(token)
        if header.get("alg") == "ES256":
            # New Supabase projects sign with asymmetric ES256 keys verified
            # against the project's public JWKS (no shared secret involved).
            payload = _decode_es256_with_jwks(token)
        else:
            if not SUPABASE_JWT_SECRET:
                # ES256 mode with no shared secret configured: HS256 tokens
                # are rejected outright instead of failing an empty-key
                # signature check (which python-jose would accept).
                raise JWTError("HS256 token received while only ES256/JWKS verification is configured")
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
    # GoTrue puts the confirmation flag at the top level on most versions, but
    # some GoTrue builds carry it only inside `user_metadata` — accept both so
    # provisioning matches whichever claim the issuing Supabase version emits.
    email_verified = (
        payload.get("email_verified") is True
        or (payload.get("user_metadata") or {}).get("email_verified") is True
    )
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
        db.flush()
        db.commit()
        db.refresh(user)
    except Exception:
        # Concurrent first-logins can race on the primary key, and the same
        # email can also collide on `users.email` (e.g. the address was
        # re-registered in Supabase and now authenticates with a different
        # `sub`). The existing row wins either way, so re-read it — by id
        # first, then by email — instead of failing the request with a 500.
        db.rollback()
        return db.scalar(select(User).where(User.id == user_id)) or db.scalar(
            select(User).where(User.email == email)
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ADMIN_REQUIRED)
    return current_user
