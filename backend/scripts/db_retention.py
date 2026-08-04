from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request

from sqlalchemy.exc import SQLAlchemyError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.time import utc_now_naive  # noqa: E402
from app.infrastructure.db.models import (  # noqa: E402
    IdempotencyRecord,
    NotificationEvent,
    PriceSnapshot,
    SecurityActivity,
)
from app.infrastructure.db.session import SessionLocal  # noqa: E402
from app.services.db_retention_tables import TableRetentionPlan, prune_table, validate_retention_windows  # noqa: E402
from app.services.community_trending_retention import (  # noqa: E402
    CommunityTrendingRetentionOptions,
    run_community_trending_retention,
    validate_community_trending_retention_days,
)
from app.services.fare_memory_retention import (  # noqa: E402
    FareMemoryRetentionOptions,
    retention_result_to_payload,
    run_fare_memory_retention,
)


def log_event(event: str, payload: dict[str, Any], log_file: str | None = None) -> None:
    line = {
        "ts": utc_now_naive().isoformat() + "Z",
        "event": event,
        **payload,
    }
    serialized = json.dumps(line, ensure_ascii=False, sort_keys=True)
    print(serialized)
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")


def log_table_completed(table_result: dict[str, Any], log_file: str | None) -> None:
    log_event(
        "db_retention.table_completed",
        {
            "table": table_result["table"],
            "retention_days": table_result["retention_days"],
            "candidates": table_result["candidates"],
            "deleted": table_result["deleted"],
            "batches": table_result["batches"],
            "duration_ms": table_result["duration_ms"],
            "dry_run": table_result["dry_run"],
        },
        log_file,
    )


def emit_failure_alert(payload: dict[str, Any], alert_file: str, webhook_url: str | None) -> None:
    path = Path(alert_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    if not webhook_url:
        return

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(webhook_url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "viru-db-retention/1.0")
    with request.urlopen(req, timeout=10):  # nosec B310 - controlled operational webhook
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prune growth tables by retention windows")
    parser.add_argument("--fare-memory", action="store_true", help="Prune Fare Memory cache tables")
    parser.add_argument("--price-snapshot-days", type=int, default=180)
    parser.add_argument("--notification-event-days", type=int, default=90)
    parser.add_argument("--security-activity-days", type=int, default=180)
    parser.add_argument("--idempotency-days", type=int, default=7)
    parser.add_argument("--community-trending-days", type=int, default=90)
    parser.add_argument("--community-trending-building-hours", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true", help="Only report deletion candidates")
    parser.add_argument("--apply", action="store_true", help="Explicitly delete candidates")
    parser.add_argument(
        "--log-file",
        default=os.getenv("DB_RETENTION_LOG_FILE", "./logs/db-retention.log"),
        help="JSONL execution log file",
    )
    parser.add_argument(
        "--alert-file",
        default=os.getenv("DB_RETENTION_ALERT_FILE", "./logs/alerts/db-retention-failure.json"),
        help="Path written on failure",
    )
    parser.add_argument(
        "--alert-webhook",
        default=os.getenv("DB_RETENTION_ALERT_WEBHOOK"),
        help="Optional webhook URL receiving failure payload",
    )
    return parser.parse_args()


def _validate_execution_mode(args: argparse.Namespace) -> None:
    if args.dry_run and args.apply:
        raise ValueError("--dry-run and --apply are mutually exclusive")
    if args.fare_memory and not args.dry_run and not args.apply:
        raise ValueError("--fare-memory requires either --dry-run or --apply")
    if args.batch_size < 1:
        raise ValueError("--batch-size must be >= 1")
    if args.community_trending_building_hours <= 0:
        raise ValueError("--community-trending-building-hours must be > 0")
    validate_community_trending_retention_days(args.community_trending_days)


def main() -> int:
    args = parse_args()
    started_at = time.monotonic()
    run_started_utc = utc_now_naive().isoformat() + "Z"

    retention_windows = {
        "price_snapshot_days": args.price_snapshot_days,
        "notification_event_days": args.notification_event_days,
        "security_activity_days": args.security_activity_days,
        "idempotency_days": args.idempotency_days,
        "community_trending_days": args.community_trending_days,
    }
    run_context = {
        "dry_run": args.dry_run,
        "batch_size": args.batch_size,
        "db_url": os.getenv("DB_URL", "sqlite:///./viru.db"),
        "retention": retention_windows,
    }

    try:
        _validate_execution_mode(args)
        if args.fare_memory:
            log_event("db_retention.fare_memory_started", run_context, args.log_file)
            with SessionLocal() as session:
                result = run_fare_memory_retention(
                    session,
                    FareMemoryRetentionOptions(
                        dry_run=args.dry_run,
                        batch_size=args.batch_size,
                        today=utc_now_naive().date(),
                        now_utc=utc_now_naive(),
                    ),
                )
            summary = {
                "status": "ok",
                "started_at": run_started_utc,
                "finished_at": utc_now_naive().isoformat() + "Z",
                "duration_ms": round((time.monotonic() - started_at) * 1000, 2),
                **retention_result_to_payload(result),
            }
            log_event("db_retention.fare_memory_completed", summary, args.log_file)
            return 0

        validate_retention_windows(retention_windows)

        plans = [
            TableRetentionPlan("price_snapshot", PriceSnapshot, PriceSnapshot.captured_at_utc, args.price_snapshot_days),
            TableRetentionPlan(
                "notification_event", NotificationEvent, NotificationEvent.created_at, args.notification_event_days
            ),
            TableRetentionPlan(
                "security_activity", SecurityActivity, SecurityActivity.created_at, args.security_activity_days
            ),
            TableRetentionPlan("idempotency_record", IdempotencyRecord, IdempotencyRecord.created_at, args.idempotency_days),
        ]

        log_event("db_retention.run_started", run_context, args.log_file)

        with SessionLocal() as session:
            per_table = [
                prune_table(
                    session=session,
                    plan=plan,
                    batch_size=args.batch_size,
                    dry_run=args.dry_run,
                )
                for plan in plans
            ]
            for table_result in per_table:
                log_table_completed(table_result, args.log_file)

            community_result = run_community_trending_retention(
                session,
                CommunityTrendingRetentionOptions(
                    dry_run=args.dry_run,
                    batch_size=args.batch_size,
                    snapshot_days=args.community_trending_days,
                    building_hours=args.community_trending_building_hours,
                    now_utc=utc_now_naive(),
                ),
            )
            log_event(
                "db_retention.community_trending_completed",
                community_result.to_payload(),
                args.log_file,
            )

        deleted_total = sum(item["deleted"] for item in per_table) + community_result.deleted_total
        candidates_total = sum(item["candidates"] for item in per_table) + community_result.candidates_total
        duration_ms = round((time.monotonic() - started_at) * 1000, 2)

        summary = {
            "status": "ok",
            "started_at": run_started_utc,
            "finished_at": utc_now_naive().isoformat() + "Z",
            "duration_ms": duration_ms,
            "dry_run": args.dry_run,
            "batch_size": args.batch_size,
            "tables": per_table,
            "community_trending": community_result.to_payload(),
            "totals": {
                "candidates": candidates_total,
                "deleted": deleted_total,
            },
        }
        log_event("db_retention.run_completed", summary, args.log_file)
        return 0

    except (ValueError, SQLAlchemyError, OSError) as exc:
        duration_ms = round((time.monotonic() - started_at) * 1000, 2)
        failure_payload = {
            "status": "failed",
            "started_at": run_started_utc,
            "failed_at": utc_now_naive().isoformat() + "Z",
            "duration_ms": duration_ms,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "context": run_context,
        }
        try:
            emit_failure_alert(failure_payload, args.alert_file, args.alert_webhook)
        finally:
            log_event("db_retention.run_failed", failure_payload, args.log_file)
        return 1


if __name__ == "__main__":
    sys.exit(main())
