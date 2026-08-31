from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
BASE_REVISION = "0052_hotel_daily_metric"
HEAD_REVISION = "0062_prune_legacy_expiry_indexes"


def _env(db_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["DB_URL"] = f"sqlite:///{db_path.as_posix()}"
    environment["RUN_DB_INIT"] = "false"
    environment["RUN_SEED_USERS"] = "false"
    environment["WATCHLIST_STARTUP_REFRESH_ENABLED"] = "false"
    environment["FARE_MEMORY_BOOT_WARMUP_ENABLED"] = "false"
    environment["FARE_MEMORY_REVALIDATION_WORKER_ENABLED"] = "false"
    return environment


def _run(db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_ROOT,
        env=_env(db_path),
        capture_output=True,
        text=True,
        check=False,
    )


def test_latency_migration_roundtrip_and_constraints(tmp_path: Path) -> None:
    db_path = tmp_path / "hotel-provider-latency-roundtrip.db"
    upgraded = _run(db_path, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(hotel_provider_latency_aggregate)")}
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(hotel_provider_latency_aggregate)")}
        foreign_keys = connection.execute("PRAGMA foreign_key_list(hotel_provider_latency_aggregate)").fetchall()
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert {
        "id", "provider_run_id", "provider", "operation", "outcome", "error_code",
        "sample_count", "total_duration_ms", "min_duration_ms", "max_duration_ms",
        "created_at", "updated_at",
    } == columns
    assert {
        "ix_hotel_provider_latency_aggregate_run",
        "ix_hotel_provider_latency_aggregate_provider_operation_created",
    }.issubset(indexes)
    assert foreign_keys[0][2] == "hotel_provider_run"
    assert foreign_keys[0][6] == "CASCADE"
    assert revision == HEAD_REVISION

    downgraded = _run(db_path, "downgrade", BASE_REVISION)
    assert downgraded.returncode == 0, downgraded.stderr
    with sqlite3.connect(db_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "hotel_provider_latency_aggregate" not in tables
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == BASE_REVISION

    reupgraded = _run(db_path, "upgrade", "head")
    assert reupgraded.returncode == 0, reupgraded.stderr
