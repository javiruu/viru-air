import os
import sys
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_raw_db_url = os.getenv("DB_URL", "").strip()

if not _raw_db_url:
    _test_url = os.getenv("TEST_DB_URL", "").strip()
    if _test_url and ("pytest" in sys.modules or os.getenv("APP_ENV") == "test"):
        _raw_db_url = _test_url
    else:
        raise RuntimeError(
            "FATAL: DB_URL environment variable is required. "
            "Supabase PostgreSQL is the sole database authority."
        )

parsed = urlparse(_raw_db_url)
if parsed.scheme in ("postgresql", "postgres"):
    _raw_db_url = _raw_db_url.replace(f"{parsed.scheme}://", "postgresql+psycopg://", 1)
    parsed = urlparse(_raw_db_url)

if (
    "postgresql" in parsed.scheme
    and parsed.hostname
    and "localhost" not in parsed.hostname
    and "127.0.0.1" not in parsed.hostname
):
    query_params = parse_qs(parsed.query)
    if "sslmode" not in query_params:
        query_params["sslmode"] = ["require"]
        new_query = urlencode(query_params, doseq=True)
        _raw_db_url = urlunparse(parsed._replace(query=new_query))

DB_URL = _raw_db_url


class Base(DeclarativeBase):
    pass


_engine_options: dict[str, object] = {
    "future": True,
    "pool_pre_ping": True,
}

if DB_URL.startswith("postgresql"):
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

