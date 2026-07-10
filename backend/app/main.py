import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.exception_handlers import register_exception_handlers
from app.core.request_context import normalize_correlation_id, set_correlation_id
from app.core.request_diagnostics import AccessLogMiddleware

from app.api.v1.router import api_v1
from app.core.logging import configure_logging
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.schema_compat import (
    ensure_door_to_door_tables,
    ensure_notification_state_table,
    ensure_search_preference_columns,
)
from app.infrastructure.db.seed import ensure_seed_users
from app.infrastructure.db.session import Base, engine
from app.infrastructure.db.session import SessionLocal
from app.services.fare_memory_config import (
    FARE_MEMORY_BOOT_WARMUP_ENABLED,
    FARE_MEMORY_BOOT_WARMUP_JITTER_SECONDS,
    FARE_MEMORY_MAX_BOOT_JOBS,
    FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE,
    FARE_MEMORY_REVALIDATION_WORKER_BATCH_SIZE,
    FARE_MEMORY_REVALIDATION_WORKER_ENABLED,
    FARE_MEMORY_REVALIDATION_WORKER_INTERVAL_SECONDS,
    FARE_MEMORY_RETENTION_BATCH_SIZE,
    FARE_MEMORY_RETENTION_ENABLED,
)
from app.services.fare_memory_revalidation_worker import RevalidationWorkerConfig, run_periodic_revalidation_worker
from app.services.fare_memory_retention_job import run_startup_fare_memory_retention
from app.services.fare_memory_warmup import log_scheduled_boot_warmup_jobs
from app.services.watchlist_revalidation import (
    WATCHLIST_STARTUP_REFRESH_ENABLED,
    log_enqueued_startup_refresh_jobs,
    process_due_route_revalidation_jobs,
)

configure_logging()

run_db_init = os.getenv("RUN_DB_INIT", "false").lower() in {"1", "true", "yes"}
run_seed_users = os.getenv("RUN_SEED_USERS", "false").lower() in {"1", "true", "yes"}

if run_db_init:
    Base.metadata.create_all(bind=engine)
ensure_search_preference_columns(engine)
ensure_door_to_door_tables(engine)
ensure_notification_state_table(engine)
if run_seed_users:
    ensure_seed_users()

def _parse_cors_origins() -> list[str]:
    default_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3101",
        "http://127.0.0.1:3101",
        "http://45.136.18.49:3000",
        "http://45.136.18.49:3101",
        "http://45.136.18.49:3200",
        "http://45.136.18.49:3300",
        "http://192.168.56.1:3000",
    ]

    # Automatically add the configured DOMAIN (https) when set (e.g. via FreeDomain).
    domain = os.getenv("DOMAIN", "").strip()
    if domain:
        domain_origin = f"https://{domain}"
        if domain_origin not in default_origins:
            default_origins = [*default_origins, domain_origin]

    env_value = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if env_value:
        env_origins = [item.strip() for item in env_value.split(",") if item.strip()]
        if env_origins:
            # Keep dev-safe defaults even when env overrides are present.
            merged = list(dict.fromkeys([*default_origins, *env_origins]))
            return merged

    return default_origins


_warmup_logger = logging.getLogger("app.fare_memory.warmup")
_retention_logger = logging.getLogger("app.fare_memory.retention")
_watchlist_startup_logger = logging.getLogger("app.watchlist")


async def _run_startup_route_revalidation_jobs() -> None:
    await asyncio.to_thread(process_due_route_revalidation_jobs, SessionLocal)


async def _run_startup_fare_memory_retention_job() -> None:
    try:
        report = await asyncio.to_thread(
            run_startup_fare_memory_retention,
            SessionLocal,
            batch_size=FARE_MEMORY_RETENTION_BATCH_SIZE,
        )
    except (SQLAlchemyError, TypeError, ValueError) as exc:
        _retention_logger.error(
            json.dumps(
                {
                    "event": "fare_memory_retention_failed",
                    "batch_size": FARE_MEMORY_RETENTION_BATCH_SIZE,
                    "error": str(exc)[:500],
                },
                ensure_ascii=False,
            )
        )
        return
    _retention_logger.info(
        json.dumps(
            {
                "event": "fare_memory_retention_completed",
                **report,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


async def _run_periodic_fare_memory_revalidation_worker() -> None:
    await run_periodic_revalidation_worker(
        SessionLocal,
        RevalidationWorkerConfig(
            interval_seconds=FARE_MEMORY_REVALIDATION_WORKER_INTERVAL_SECONDS,
            batch_size=FARE_MEMORY_REVALIDATION_WORKER_BATCH_SIZE,
        ),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_route_task = None
    retention_task = None
    revalidation_worker_task = None
    if FARE_MEMORY_BOOT_WARMUP_ENABLED:
        db = SessionLocal()
        try:
            log_scheduled_boot_warmup_jobs(
                db,
                limit=FARE_MEMORY_MAX_BOOT_JOBS,
                provider_rate_limit_per_minute=FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE,
                jitter_seconds=FARE_MEMORY_BOOT_WARMUP_JITTER_SECONDS,
            )
        except (SQLAlchemyError, TypeError, ValueError) as exc:
            _warmup_logger.error(
                json.dumps(
                    {
                        "event": "fare_memory_boot_warmup_schedule_failed",
                        "limit": FARE_MEMORY_MAX_BOOT_JOBS,
                        "provider_rate_limit_per_minute": FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE,
                        "jitter_seconds": FARE_MEMORY_BOOT_WARMUP_JITTER_SECONDS,
                        "error": str(exc)[:500],
                    },
                    ensure_ascii=False,
                )
            )
        finally:
            db.close()
    if WATCHLIST_STARTUP_REFRESH_ENABLED:
        db = SessionLocal()
        try:
            log_enqueued_startup_refresh_jobs(db)
        except (SQLAlchemyError, TypeError, ValueError) as exc:
            _watchlist_startup_logger.error(
                json.dumps(
                    {
                        "event": "watchlist_startup_refresh_schedule_failed",
                        "max_age_seconds": os.getenv("WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS", "86400"),
                        "error": str(exc)[:500],
                    },
                    ensure_ascii=False,
                )
            )
        finally:
            db.close()
    if WATCHLIST_STARTUP_REFRESH_ENABLED or FARE_MEMORY_BOOT_WARMUP_ENABLED:
        startup_route_task = asyncio.create_task(_run_startup_route_revalidation_jobs())
        app.state.startup_route_revalidation_task = startup_route_task
    if FARE_MEMORY_RETENTION_ENABLED:
        retention_task = asyncio.create_task(_run_startup_fare_memory_retention_job())
        app.state.fare_memory_retention_task = retention_task
    if FARE_MEMORY_REVALIDATION_WORKER_ENABLED:
        revalidation_worker_task = asyncio.create_task(_run_periodic_fare_memory_revalidation_worker())
        app.state.fare_memory_revalidation_worker_task = revalidation_worker_task
    yield
    if revalidation_worker_task is not None:
        revalidation_worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await revalidation_worker_task
    if retention_task is not None:
        retention_task.cancel()
        with suppress(asyncio.CancelledError):
            await retention_task
    if startup_route_task is not None:
        startup_route_task.cancel()
        with suppress(asyncio.CancelledError):
            await startup_route_task


app = FastAPI(title="Viru API", version="0.1.0", lifespan=lifespan)


_env_regex = os.getenv("CORS_ALLOW_ORIGIN_REGEX")
if _env_regex is None:
    _allow_origin_regex: str | None = (
        r"^https?://(45\.136\.18\.49|localhost|127\.0\.0\.1)(?::\d+)?$"
    )
elif _env_regex.strip() == "":
    _allow_origin_regex = None  # Explicitly disabled
else:
    _allow_origin_regex = _env_regex

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AccessLogMiddleware)
app.include_router(api_v1, prefix="/api/v1")
register_exception_handlers(app)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = normalize_correlation_id(request.headers.get("x-correlation-id"))
    request.state.correlation_id = correlation_id
    set_correlation_id(correlation_id)
    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}
