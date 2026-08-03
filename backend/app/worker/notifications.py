from __future__ import annotations

import argparse
import json
import logging
import os
import time

from sqlalchemy.orm import sessionmaker

from app.core.logging import configure_logging
from app.infrastructure.db.session import SessionLocal
from app.services.community_trending_notifier import notify_trending_routes
from app.services.notification_service import dispatch_pending_events

DEFAULT_WORKER_ENABLED = os.getenv("NOTIFICATION_WORKER_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
}
DEFAULT_WORKER_BATCH_SIZE = int(os.getenv("NOTIFICATION_WORKER_BATCH_SIZE", "50"))
DEFAULT_WORKER_INTERVAL_SECONDS = int(os.getenv("NOTIFICATION_WORKER_INTERVAL_SECONDS", "60"))

logger = logging.getLogger("app.worker.notifications")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Notification pending-events worker")
    parser.add_argument("--limit", type=int, default=DEFAULT_WORKER_BATCH_SIZE)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Run one processing cycle and exit.")
    mode.add_argument("--loop", action="store_true", help="Run continuously with sleep intervals.")
    mode.add_argument("--trending", action="store_true", help="Run community trending check and exit.")
    parser.add_argument("--sleep-seconds", type=int, default=DEFAULT_WORKER_INTERVAL_SECONDS)
    args = parser.parse_args()
    if not args.once and not args.loop and not args.trending:
        args.once = True
    return args


def _log_cycle(result, *, once: bool, limit: int) -> None:
    logger.info(
        json.dumps(
            {
                "event": "notification_worker_cycle",
                "mode": "once" if once else "loop",
                "limit": limit,
                "processed": result.processed,
                "delivered": result.delivered,
                "failed": result.failed,
                "skipped": result.skipped,
                "retried": result.retried,
            },
            ensure_ascii=False,
        )
    )


def run_once(*, session_factory: sessionmaker = SessionLocal, limit: int = DEFAULT_WORKER_BATCH_SIZE):
    db = session_factory()
    try:
        result = dispatch_pending_events(db, limit=limit)
        _log_cycle(result, once=True, limit=limit)
        return result
    finally:
        db.close()


def run_trending(*, session_factory: sessionmaker = SessionLocal) -> int:
    """Run community trending check and return number of notifications created."""
    db = session_factory()
    try:
        created = notify_trending_routes(db)
        logger.info(
            json.dumps(
                {
                    "event": "notification_trending_cycle",
                    "created": created,
                },
                ensure_ascii=False,
            )
        )
        return created
    finally:
        db.close()


def run_loop(
    *,
    session_factory: sessionmaker = SessionLocal,
    limit: int = DEFAULT_WORKER_BATCH_SIZE,
    sleep_seconds: int = DEFAULT_WORKER_INTERVAL_SECONDS,
) -> None:
    trending_cycle = 0
    while True:
        db = session_factory()
        try:
            result = dispatch_pending_events(db, limit=limit)
            _log_cycle(result, once=False, limit=limit)
        finally:
            db.close()

        # Run trending check every ~15 cycles (every ~15 minutes)
        trending_cycle += 1
        if trending_cycle % 15 == 0:
            run_trending()

        time.sleep(max(1, sleep_seconds))


def main() -> int:
    configure_logging()
    args = _parse_args()
    if not DEFAULT_WORKER_ENABLED:
        logger.warning(
            json.dumps(
                {
                    "event": "notification_worker_disabled",
                    "message": "NOTIFICATION_WORKER_ENABLED=false",
                },
                ensure_ascii=False,
            )
        )

    if args.trending:
        created = run_trending()
        return 0 if created >= 0 else 1

    if args.once:
        run_once(limit=args.limit)
        return 0
    run_loop(limit=args.limit, sleep_seconds=args.sleep_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
