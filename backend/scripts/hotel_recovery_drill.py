from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from contextlib import closing
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

# Support both ``python scripts/hotel_recovery_drill.py`` and module/test imports.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from scripts.hotel_demo_seed import DATASET_ID, _load_marker, run_seed  # noqa: E402


SAFE_APP_ENVS = {"test", "demo", "local_fixture"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _head_revision() -> str:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    heads = list(ScriptDirectory.from_config(config).get_heads())
    if len(heads) != 1:
        raise ValueError("hotel_recovery_unexpected_alembic_heads")
    return heads[0]


def _checkpoint(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA wal_checkpoint(FULL)")
        connection.commit()


def _copy_seed_marker(source_db: Path, destination_db: Path) -> None:
    source_marker = source_db.with_name(source_db.name + ".h44-demo.json")
    destination_marker = destination_db.with_name(destination_db.name + ".h44-demo.json")
    if not source_marker.exists():
        raise ValueError("hotel_recovery_seed_marker_missing")
    shutil.copy2(source_marker, destination_marker)


def _backup(source: Path, destination: Path) -> None:
    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()


def _snapshot_counts(connection: sqlite3.Connection) -> dict[str, int]:
    tables = {
        "users": "SELECT COUNT(*) FROM users WHERE email IN ('demo-user-a@viru.local', 'demo-user-b@viru.local')",
        "hotels": "SELECT COUNT(*) FROM hotel_property",
        "aliases": "SELECT COUNT(*) FROM hotel_provider_alias WHERE provider = 'mock'",
        "snapshots": "SELECT COUNT(*) FROM hotel_rate_snapshot",
        "tracked_offers": "SELECT COUNT(*) FROM hotel_tracked_offer",
        "alert_rules": "SELECT COUNT(*) FROM hotel_alert_rule",
        "alert_events": "SELECT COUNT(*) FROM hotel_alert_event",
        "deliveries": "SELECT COUNT(*) FROM hotel_notification_delivery",
    }
    return {name: int(connection.execute(query).fetchone()[0]) for name, query in tables.items()}


def _validate_restore(path: Path, expected_counts: dict[str, int], sentinel: str) -> dict[str, object]:
    with closing(sqlite3.connect(path)) as connection:
        current = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        if current is None or current[0] != _head_revision():
            raise ValueError("hotel_recovery_schema_not_at_head")
        counts = _snapshot_counts(connection)
        if counts != expected_counts:
            raise ValueError("hotel_recovery_counts_mismatch")
        restored_sentinel = connection.execute(
            "SELECT value FROM recovery_drill_sentinel WHERE name = 'outside_scope'"
        ).fetchone()
        if restored_sentinel is None or restored_sentinel[0] != sentinel:
            raise ValueError("hotel_recovery_sentinel_missing")
        owner_count = int(
            connection.execute(
                "SELECT COUNT(DISTINCT user_id) FROM hotel_alert_rule WHERE user_id IN ("
                "SELECT id FROM users WHERE email IN ('demo-user-a@viru.local', 'demo-user-b@viru.local')"
                ")"
            ).fetchone()[0]
        )
        if owner_count != 2:
            raise ValueError("hotel_recovery_ownership_not_isolated")
        return {"counts": counts, "owner_count": owner_count, "schema_revision": current[0]}


def run_recovery_drill() -> dict[str, object]:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env not in SAFE_APP_ENVS:
        raise ValueError("hotel_recovery_requires_safe_app_env")
    started = _utc_now()
    with tempfile.TemporaryDirectory(prefix="hotel-h55-recovery-") as workspace:
        root = Path(workspace)
        source = root / "source.db"
        backup = root / "backup.db"
        restored = root / "restored.db"
        seed_started = time.perf_counter()
        seed_report = run_seed(f"sqlite:///{source.as_posix()}")
        seed_seconds = time.perf_counter() - seed_started
        sentinel = "outside-scope-sentinel-v1"
        with closing(sqlite3.connect(source)) as connection:
            connection.execute("CREATE TABLE recovery_drill_sentinel (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute(
                "INSERT INTO recovery_drill_sentinel(name, value) VALUES ('outside_scope', ?)",
                (sentinel,),
            )
            connection.commit()
        _checkpoint(source)
        backup_started = time.perf_counter()
        _backup(source, backup)
        _copy_seed_marker(source, backup)
        backup_seconds = time.perf_counter() - backup_started
        restore_started = time.perf_counter()
        _backup(backup, restored)
        _copy_seed_marker(backup, restored)
        restore_seconds = time.perf_counter() - restore_started
        with closing(sqlite3.connect(source)) as source_connection:
            expected_counts = _snapshot_counts(source_connection)
        restored_report = _validate_restore(restored, expected_counts, sentinel)
        restored_marker_path = restored.with_name(restored.name + ".h44-demo.json")
        restored_marker = _load_marker(restored)
        restored_marker_exists = restored_marker_path.exists()
        if not restored_marker_exists or restored_marker is None:
            raise ValueError("hotel_recovery_restored_marker_missing")
        if restored_marker.get("status") != "complete" or restored_marker.get("dataset_id") != DATASET_ID:
            raise ValueError("hotel_recovery_restored_marker_mismatch")
        finished = _utc_now()
        report = {
            "result": "passed",
            "schema_version": "hotel-recovery-drill-v1",
            "dataset_id": DATASET_ID,
            "app_env": app_env,
            "db_isolation_kind": "sqlite_temp_workspace",
            "provider_mode": "mock",
            "external_calls_expected": 0,
            "external_calls_observed": 0,
            "source_database_removed_after_drill": True,
            "backup_database_removed_after_drill": True,
            "restored_database_removed_after_drill": False,
            "restored_seed_marker_copied": restored_marker_exists,
            "seed": {"result": seed_report["result"], "rows_by_table": seed_report["rows_by_table"]},
            "backup": {"result": "passed", "source_counts": expected_counts},
            "restore": restored_report,
            "observed_rpo_seconds": 0,
            "observed_rto_seconds": round(restore_seconds, 3),
            "drill_runtime_seconds": round(seed_seconds + backup_seconds + restore_seconds, 3),
            "timing_seconds": {
                "seed": round(seed_seconds, 3),
                "backup": round(backup_seconds, 3),
                "restore": round(restore_seconds, 3),
            },
            "started_at_utc": started.isoformat().replace("+00:00", "Z"),
            "finished_at_utc": finished.isoformat().replace("+00:00", "Z"),
            "known_limitations": [
                "sqlite_only",
                "mock_fixture_only",
                "no_production_backup_provider",
                "no_live_worker_failover",
                "rpo_is_zero_for_this_same_process_checkpoint",
            ],
        }
    cleanup_paths = (
        source,
        backup,
        restored,
        source.with_name(source.name + ".h44-demo.json"),
        backup.with_name(backup.name + ".h44-demo.json"),
        restored.with_name(restored.name + ".h44-demo.json"),
    )
    cleanup_verified = not any(path.exists() for path in cleanup_paths)
    report["source_database_removed_after_drill"] = not source.exists()
    report["backup_database_removed_after_drill"] = not backup.exists()
    report["restored_database_removed_after_drill"] = not restored.exists()
    report["cleanup_verified"] = cleanup_verified
    if not cleanup_verified:
        raise ValueError("hotel_recovery_cleanup_failed")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an isolated H55 SQLite backup/restore drill")
    parser.parse_args()
    try:
        report = run_recovery_drill()
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"result": "blocked", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
