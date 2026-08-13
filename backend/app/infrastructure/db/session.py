import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_configured_db_url = os.getenv("DB_URL", "").strip()
if _configured_db_url:
    DB_URL = _configured_db_url
else:
    _default_sqlite_path = (Path(__file__).resolve().parents[3] / "viru.db").as_posix()
    DB_URL = f"sqlite:///{_default_sqlite_path}"


class Base(DeclarativeBase):
    pass


_connect_args: dict[str, object] = {}
if DB_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

_engine_options: dict[str, object] = {
    "future": True,
    "connect_args": _connect_args,
    "pool_pre_ping": True,
}
if not DB_URL.startswith("sqlite"):
    _engine_options.update(
        pool_size=max(1, int(os.getenv("DB_POOL_SIZE", "10"))),
        max_overflow=max(0, int(os.getenv("DB_MAX_OVERFLOW", "20"))),
        pool_timeout=max(1, int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "30"))),
        pool_recycle=max(0, int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800"))),
    )

engine = create_engine(DB_URL, **_engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
