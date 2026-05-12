import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import jwt


def _get_jwt_secret() -> str | None:
    secret = os.getenv("JWT_SECRET")
    if secret:
        return secret

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "JWT_SECRET":
            candidate = value.strip().strip("'\"")
            if candidate:
                os.environ["JWT_SECRET"] = candidate
                return candidate
    return None


JWT_SECRET = _get_jwt_secret()
if not JWT_SECRET or JWT_SECRET == "change-me":
    raise RuntimeError(
        "JWT_SECRET must be set to a secure value "
        "(environment variable or backend/.env)"
    )
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "30"))
RESET_TOKEN_MINUTES = int(os.getenv("RESET_TOKEN_MINUTES", "30"))
TOKEN_HASH_SECRET = os.getenv("TOKEN_HASH_SECRET", JWT_SECRET)


def create_access_token(subject: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {"sub": subject, "exp": expires}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_reset_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(f"{TOKEN_HASH_SECRET}:{token}".encode("utf-8")).hexdigest()


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(f"{TOKEN_HASH_SECRET}:{ip}".encode("utf-8")).hexdigest()
