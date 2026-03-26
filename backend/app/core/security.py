import os
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


def create_access_token(subject: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {"sub": subject, "exp": expires}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
