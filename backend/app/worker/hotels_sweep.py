from __future__ import annotations

import argparse
import json
import logging
import os
import time

from sqlalchemy.orm import sessionmaker

from app.core.logging import configure_logging
from app.infrastructure.db.session import SessionLocal
from app.services.hotels_service import run_hotel_sweep

DEFAULT_SWEEP_ENABLED = os.getenv("HOTEL_SWEEP_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
}
DEFAULT_SWEEP_INTERVAL_SECONDS = int(os.getenv("HOTEL_SWEEP_INTERVAL_SECONDS", "3600"))
DEFAULT_SWEEP_PROVIDER = os.getenv("HOTEL_PROVIDER", "mock").strip() or "mock"

logger = logging.getLogger("app.worker.hotels_sweep")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hotel sweep worker")
    parser.add_argument("--provider", default=DEFAULT_SWEEP_PROVIDER)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Run one hotel sweep and exit.")
    mode.add_argument("--loop", action="store_true", help="Run continuously with sleep intervals.")
    parser.add_argument("--sleep-seconds", type=int, default=DEFAULT_SWEEP_INTERVAL_SECONDS)
    args = parser.parse_args()
    if not args.once and not args.loop:
        args.once = True
    return args


def _log_cycle(provider_run, *, once: bool, provider: str) -> None:
    logger.info(
        json.dumps(
            {
                "event": "hotel_sweep_cycle",
                "mode": "once" if once else "loop",
                "provider": provider,
                "provider_run_id": provider_run.id,
                "status": provider_run.status,
                "items_processed": provider_run.items_processed,
                "error_message": provider_run.error_message,
            },
            ensure_ascii=False,
        )
    )


def run_once(
    *,
    session_factory: sessionmaker = SessionLocal,
    provider: str = DEFAULT_SWEEP_PROVIDER,
):
    db = session_factory()
    try:
        provider_run = run_hotel_sweep(db, provider=provider)
        _log_cycle(provider_run, once=True, provider=provider)
        return provider_run
    finally:
        db.close()


def run_loop(
    *,
    session_factory: sessionmaker = SessionLocal,
    provider: str = DEFAULT_SWEEP_PROVIDER,
    sleep_seconds: int = DEFAULT_SWEEP_INTERVAL_SECONDS,
) -> None:
    while True:
        db = session_factory()
        try:
            provider_run = run_hotel_sweep(db, provider=provider)
            _log_cycle(provider_run, once=False, provider=provider)
        finally:
            db.close()
        time.sleep(max(1, sleep_seconds))


def main() -> int:
    configure_logging()
    args = _parse_args()
    if not DEFAULT_SWEEP_ENABLED:
        logger.warning(
            json.dumps(
                {
                    "event": "hotel_sweep_disabled",
                    "message": "HOTEL_SWEEP_ENABLED=false",
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.once:
        run_once(provider=args.provider)
        return 0
    run_loop(provider=args.provider, sleep_seconds=args.sleep_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
