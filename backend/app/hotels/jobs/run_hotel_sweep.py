"""Hotel sweep job — ingests mock data and evaluates alert rules.

Usage:
    python -m app.hotels.jobs.run_hotel_sweep
    python -m app.hotels.jobs.run_hotel_sweep --provider mock
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from app.core.logging import configure_logging
from app.hotels.activation import is_hotel_sweep_enabled
from app.infrastructure.db.session import SessionLocal
from app.services import hotels_service

logger = logging.getLogger("app.hotels.jobs.sweep")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a hotel provider sweep")
    parser.add_argument(
        "--provider",
        type=str,
        default=os.getenv("HOTEL_PROVIDER", "mock"),
        help="Provider id (default: mock)",
    )
    return parser.parse_args()


def run(provider: str = "mock") -> int:
    if not is_hotel_sweep_enabled(provider=provider):
        logger.warning(
            json.dumps(
                {"event": "hotel_sweep_disabled", "message": "HOTEL_SWEEP_ENABLED=false"},
                ensure_ascii=False,
            )
        )
        return 0

    db = SessionLocal()
    try:
        logger.info(
            json.dumps(
                {"event": "hotel_sweep_start", "provider": provider},
                ensure_ascii=False,
            )
        )

        provider_run = hotels_service.run_hotel_sweep(db, provider=provider)

        logger.info(
            json.dumps(
                {
                    "event": "hotel_sweep_finished",
                    "run_id": provider_run.id,
                    "provider": provider_run.provider,
                    "status": provider_run.status,
                    "items_processed": provider_run.items_processed,
                },
                ensure_ascii=False,
            )
        )

        if provider_run.status == "failed":
            logger.error(
                json.dumps(
                    {
                        "event": "hotel_sweep_failed",
                        "run_id": provider_run.id,
                        "error": provider_run.error_message,
                    },
                    ensure_ascii=False,
                )
            )
            return 1

        return 0
    except Exception as exc:
        logger.exception(
            json.dumps(
                {"event": "hotel_sweep_unhandled_error", "error": str(exc)},
                ensure_ascii=False,
            )
        )
        return 1
    finally:
        db.close()


def main() -> int:
    configure_logging()
    args = _parse_args()
    return run(provider=args.provider)


if __name__ == "__main__":
    sys.exit(main())
