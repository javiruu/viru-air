from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Protocol

import anyio
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.watchlist_revalidation import process_due_route_revalidation_jobs

logger = logging.getLogger("app.watchlist")

SessionFactory = Callable[[], Session]


@dataclass(frozen=True, slots=True)
class RevalidationWorkerConfig:
    interval_seconds: float
    batch_size: int


class RevalidationProcessor(Protocol):
    def __call__(self, session_factory: SessionFactory, *, max_jobs: int | None = None) -> dict[str, object]: ...


async def run_periodic_revalidation_worker(
    session_factory: SessionFactory,
    config: RevalidationWorkerConfig,
    *,
    processor: RevalidationProcessor = process_due_route_revalidation_jobs,
) -> None:
    interval_seconds = max(0.001, float(config.interval_seconds))
    batch_size = max(1, int(config.batch_size))

    while True:
        try:
            report = await anyio.to_thread.run_sync(partial(processor, session_factory, max_jobs=batch_size))
        except anyio.get_cancelled_exc_class():
            raise
        except (SQLAlchemyError, RuntimeError, TypeError, ValueError) as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "fare_memory_revalidation_worker_failed",
                        "batch_size": batch_size,
                        "interval_seconds": interval_seconds,
                        "error": str(exc)[:500],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            logger.info(
                json.dumps(
                    {
                        "event": "fare_memory_revalidation_worker_tick",
                        "batch_size": batch_size,
                        "interval_seconds": interval_seconds,
                        "report": report,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

        await anyio.sleep(interval_seconds)
