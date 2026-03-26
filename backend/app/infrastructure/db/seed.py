from passlib.context import CryptContext
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.infrastructure.db.models import User
from app.infrastructure.db.session import SessionLocal

pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

DEFAULT_USERS = [
    {
        "email": "user@viru.local",
        "password": "ViruUser123",
        "is_admin": False,
        "is_verified": True,
    },
    {
        "email": "admin@viru.local",
        "password": "ViruAdmin123",
        "is_admin": True,
        "is_verified": True,
    },
]


def _ensure_admin_column(db: Session) -> None:
    inspector = inspect(db.bind)
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "is_admin" not in columns:
        db.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
        db.commit()


def _ensure_snapshot_time_column(db: Session) -> None:
    inspector = inspect(db.bind)
    if "price_snapshot" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("price_snapshot")}
    if "departure_time_local" not in columns:
        db.execute(text("ALTER TABLE price_snapshot ADD COLUMN departure_time_local VARCHAR(5)"))
        db.commit()


def ensure_seed_users() -> None:
    db = SessionLocal()
    try:
        _ensure_admin_column(db)
        _ensure_snapshot_time_column(db)
        for seed in DEFAULT_USERS:
            existing = db.query(User).filter(User.email == seed["email"]).first()
            if existing:
                if existing.is_admin != seed["is_admin"]:
                    existing.is_admin = seed["is_admin"]
                    db.commit()
                continue
            user = User(
                email=seed["email"],
                password_hash=pwd.hash(seed["password"]),
                is_admin=seed["is_admin"],
                is_verified=seed["is_verified"],
            )
            db.add(user)
            db.commit()
    finally:
        db.close()
