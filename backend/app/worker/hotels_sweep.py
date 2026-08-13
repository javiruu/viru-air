from __future__ import annotations

import argparse
import json
import logging
import os
import time
from uuid import uuid4

from app.core.request_context import (
    get_correlation_id,
    normalize_correlation_id,
    reset_client_event_id,
    reset_correlation_id,
    set_client_event_id,
    set_correlation_id,
)

from sqlalchemy.orm import sessionmaker

from app.core.logging import configure_logging
from app.hotels.activation import is_hotel_sweep_enabled
from app.infrastructure.db.session import SessionLocal
from app.services.hotels_service import expire_due_tracked_offers, run_hotel_sweep


def _default_sweep_interval_seconds() -> int:
    return int(os.getenv("HOTEL_SWEEP_INTERVAL_SECONDS", "3600"))


def _default_sweep_provider() -> str:
    return os.getenv("HOTEL_PROVIDER", "mock").strip() or "mock"

logger = logging.getLogger("app.worker.hotels_sweep")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hotel sweep worker")
    parser.add_argument("--provider", default=_default_sweep_provider())
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Run one hotel sweep and exit.")
    mode.add_argument("--loop", action="store_true", help="Run continuously with sleep intervals.")
    parser.add_argument("--sleep-seconds", type=int, default=_default_sweep_interval_seconds())
    args = parser.parse_args()
    if not args.once and not args.loop:
        args.once = True
    return args


def _log_cycle(provider_run, *, once: bool, provider: str, expired_tracked_offers: int) -> None:
    logger.info(
        json.dumps(
            {
                "event": "hotel_sweep_cycle",
                "mode": "once" if once else "loop",
                "provider": provider,
                "provider_run_id": provider_run.id,
                "correlation_id": provider_run.correlation_id,
                "execution_id": provider_run.execution_id,
                "status": provider_run.status,
                "items_processed": provider_run.items_processed,
                "expired_tracked_offers": expired_tracked_offers,
                "error_message": provider_run.error_message,
            },
            ensure_ascii=False,
        ),
        extra={
            "correlation_id": provider_run.correlation_id,
            "hotel_correlation_id": provider_run.correlation_id,
            "hotel_execution_id": provider_run.execution_id,
            "hotel_provider_run_id": provider_run.id,
        },
    )


def run_once(
    *,
    session_factory: sessionmaker = SessionLocal,
    provider: str | None = None,
):
    effective_provider = provider or _default_sweep_provider()
    correlation_id = normalize_correlation_id(get_correlation_id() or None)
    execution_id = str(uuid4())
    correlation_token = set_correlation_id(correlation_id)
    client_event_token = set_client_event_id(None)
    db = None
    try:
        db = session_factory()
        expired_tracked_offers = expire_due_tracked_offers(db)
        db.commit()
        provider_run = run_hotel_sweep(
            db,
            provider=effective_provider,
            correlation_id=correlation_id,
            execution_id=execution_id,
        )
        _log_cycle(
            provider_run,
            once=True,
            provider=effective_provider,
            expired_tracked_offers=expired_tracked_offers,
        )
        return provider_run
    finally:
        if db is not None:
            db.close()
        reset_client_event_id(client_event_token)
        reset_correlation_id(correlation_token)


def run_loop(
    *,
    session_factory: sessionmaker = SessionLocal,
    provider: str | None = None,
    sleep_seconds: int | None = None,
) -> None:
    effective_provider = provider or _default_sweep_provider()
    effective_sleep_seconds = sleep_seconds if sleep_seconds is not None else _default_sweep_interval_seconds()
    while True:
        correlation_id = normalize_correlation_id(get_correlation_id() or None)
        execution_id = str(uuid4())
        correlation_token = set_correlation_id(correlation_id)
        client_event_token = set_client_event_id(None)
        db = None
        try:
            db = session_factory()
            expired_tracked_offers = expire_due_tracked_offers(db)
            db.commit()
            provider_run = run_hotel_sweep(
                db,
                provider=effective_provider,
                correlation_id=correlation_id,
                execution_id=execution_id,
            )
            _log_cycle(
                provider_run,
                once=False,
                provider=effective_provider,
                expired_tracked_offers=expired_tracked_offers,
            )
        finally:
            if db is not None:
                db.close()
            reset_client_event_id(client_event_token)
            reset_correlation_id(correlation_token)
        time.sleep(max(1, effective_sleep_seconds))


def main() -> int:
    configure_logging()
    args = _parse_args()
    if not is_hotel_sweep_enabled(provider=args.provider):
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
