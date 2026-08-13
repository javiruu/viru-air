from __future__ import annotations

import asyncio
import logging

from app.infrastructure.db.session import SessionLocal
from app.services.fare_memory_config import (
    FARE_MEMORY_BOOT_WARMUP_ENABLED,
    FARE_MEMORY_BOOT_WARMUP_JITTER_SECONDS,
    FARE_MEMORY_MAX_BOOT_JOBS,
    FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE,
    FARE_MEMORY_REVALIDATION_WORKER_BATCH_SIZE,
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
)

logger = logging.getLogger("app.revalidation_worker")


def _schedule_jobs() -> None:
    db = SessionLocal()
    try:
        if FARE_MEMORY_BOOT_WARMUP_ENABLED:
            log_scheduled_boot_warmup_jobs(
                db,
                limit=FARE_MEMORY_MAX_BOOT_JOBS,
                provider_rate_limit_per_minute=FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE,
                jitter_seconds=FARE_MEMORY_BOOT_WARMUP_JITTER_SECONDS,
            )
        if WATCHLIST_STARTUP_REFRESH_ENABLED:
            log_enqueued_startup_refresh_jobs(db)
        if FARE_MEMORY_RETENTION_ENABLED:
            logger.info(
                "fare_memory_retention_completed report=%s",
                run_startup_fare_memory_retention(SessionLocal, batch_size=FARE_MEMORY_RETENTION_BATCH_SIZE),
            )
    finally:
        db.close()


async def main() -> None:
    _schedule_jobs()
    await run_periodic_revalidation_worker(
        SessionLocal,
        RevalidationWorkerConfig(
            interval_seconds=FARE_MEMORY_REVALIDATION_WORKER_INTERVAL_SECONDS,
            batch_size=FARE_MEMORY_REVALIDATION_WORKER_BATCH_SIZE,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
