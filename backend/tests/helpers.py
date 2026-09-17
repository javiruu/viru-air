from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
from jose import jwt

from app.api.deps import SUPABASE_JWT_SECRET, get_db
from app.core.time import utc_now_naive
from app.infrastructure.db.models import SecurityActivity, User, UserSession


def _open_register_and_token_session(client: TestClient):
    """Resolve the DB session backing the test client.

    Under pytest the conftest overrides `get_db` with a per-test temporary
    database; the user must be inserted there so API calls can see it.
    Outside tests (scripts) there is no override and the global SessionLocal
    is the right target.
    """
    override = client.app.dependency_overrides.get(get_db)
    if override is None:
        from app.infrastructure.db.session import SessionLocal

        return SessionLocal(), None
    generator = override()
    return next(generator), generator


def register_and_token(client: TestClient, email: str = "qa@viru.dev", password: str = "password123") -> str:
    user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, email))
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "email_verified": True,
        "exp": now + timedelta(hours=24),
        "role": "authenticated",
        "app_metadata": {"provider": "email"},
        "user_metadata": {},
    }
    db, generator = _open_register_and_token_session(client)
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(
                id=user_id,
                email=email,
                password_hash="[SUPABASE_AUTH_MANAGED]",
                is_verified=True,
                is_admin="admin" in email,
            )
            db.add(user)
            db.flush()
        if not db.query(UserSession).filter(UserSession.user_id == user_id).first():
            db.add(UserSession(
                user_id=user_id,
                device="testclient",
                ip="127.0.0.1",
                last_seen=utc_now_naive(),
                created_at=utc_now_naive(),
                is_active=True,
            ))
        if not db.query(SecurityActivity).filter(SecurityActivity.user_id == user_id).first():
            db.add(SecurityActivity(
                user_id=user_id,
                event_type="login",
                ip="127.0.0.1",
                created_at=utc_now_naive(),
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        if generator is not None:
            try:
                next(generator)
            except StopIteration:
                pass

    return jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
