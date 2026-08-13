from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
BASE_REVISION = "0043_hotel_provider_run_outcomes"
HEAD_REVISION = "0060_revalidation_job_active_target"


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


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def test_hotel_provider_infrastructure_migrations_create_expected_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "hotel-provider-infrastructure-schema.db"

    upgraded = _run(db_path, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr

    with sqlite3.connect(db_path) as connection:
        tables = _table_names(connection)
        budget_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(hotel_provider_budget)")
        }
        reservation_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(hotel_provider_budget_reservation)"
            )
        }
        lease_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(hotel_sweep_lease)")
        }
        circuit_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(hotel_provider_circuit)")
        }
        provider_run_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(hotel_provider_run)")
        }

        budget_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(hotel_provider_budget)")
        }
        lease_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(hotel_sweep_lease)")
        }
        circuit_indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(hotel_provider_circuit)")
        }
        provider_run_indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(hotel_provider_run)")
        }
        reservation_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(hotel_provider_budget_reservation)"
        ).fetchall()
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]

    assert {"hotel_provider_budget", "hotel_provider_budget_reservation"}.issubset(tables)
    assert "hotel_sweep_lease" in tables
    assert "hotel_provider_circuit" in tables
    assert {
        "provider",
        "operation",
        "window_key",
        "hard_limit",
        "units_reserved",
        "units_used",
        "units_released",
        "window_expires_at",
        "source",
        "updated_at",
    }.issubset(budget_columns)
    assert {"budget_id", "units", "status", "created_at", "updated_at"}.issubset(
        reservation_columns
    )
    assert {
        "fingerprint",
        "status",
        "lock_token",
        "lease_expires_at",
        "attempt_count",
        "last_provider_run_id",
    }.issubset(lease_columns)
    assert {
        "provider",
        "operation",
        "status",
        "consecutive_failures",
        "probe_token",
        "state_version",
    }.issubset(circuit_columns)
    assert "ix_hotel_provider_budget_provider_operation" in budget_indexes
    assert "ix_hotel_sweep_lease_status_expires" in lease_indexes
    assert "ix_hotel_sweep_lease_token" in lease_indexes
    assert "ix_hotel_provider_circuit_status_probe" in circuit_indexes
    assert {"correlation_id", "client_event_id", "execution_id"}.issubset(provider_run_columns)
    assert "ix_hotel_provider_run_correlation_id" in provider_run_indexes
    assert "ix_hotel_provider_run_client_event_id" in provider_run_indexes
    assert "ix_hotel_provider_run_execution_id" in provider_run_indexes
    assert len(reservation_foreign_keys) == 1
    assert reservation_foreign_keys[0][2] == "hotel_provider_budget"
    assert reservation_foreign_keys[0][6] == "CASCADE"
    assert revision == HEAD_REVISION


def test_hotel_provider_infrastructure_migrations_roundtrip_and_constraints(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "hotel-provider-infrastructure-roundtrip.db"

    upgraded = _run(db_path, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO hotel_provider_budget (
                id, provider, operation, window_key, hard_limit,
                units_reserved, units_used, units_released,
                window_expires_at, source, updated_at
            ) VALUES (
                'budget-1', 'mock', 'area_search', '2026-08-08T12',
                10, 1, 0, 0, '2026-08-08 13:00:00', 'test', '2026-08-08 12:00:00'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO hotel_provider_budget_reservation (
                id, budget_id, units, status, created_at, updated_at
            ) VALUES (
                'reservation-1', 'budget-1', 1, 'reserved',
                '2026-08-08 12:00:00', '2026-08-08 12:00:00'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO hotel_sweep_lease (
                fingerprint, status, lock_token, attempt_count, updated_at
            ) VALUES ('fingerprint-1', 'queued', 'token-1', 0, '2026-08-08 12:00:00')
            """
        )
        connection.execute(
            """
            INSERT INTO hotel_provider_circuit (
                id, provider, operation, updated_at
            ) VALUES ('circuit-1', 'mock', 'area_search', '2026-08-08 12:00:00')
            """
        )
        connection.commit()

        state_version = connection.execute(
            "SELECT state_version FROM hotel_provider_circuit WHERE id = 'circuit-1'"
        ).fetchone()[0]
        assert state_version == 0

        connection.execute("DELETE FROM hotel_provider_budget WHERE id = 'budget-1'")
        remaining_reservations = connection.execute(
            "SELECT COUNT(*) FROM hotel_provider_budget_reservation"
        ).fetchone()[0]
        assert remaining_reservations == 0

        try:
            connection.execute(
                """
                INSERT INTO hotel_provider_circuit (
                    id, provider, operation, updated_at
                ) VALUES ('circuit-2', 'mock', 'area_search', '2026-08-08 12:00:00')
                """
            )
        except sqlite3.IntegrityError:
            connection.rollback()
        else:
            raise AssertionError("provider/operation uniqueness constraint accepted duplicate")

    downgraded = _run(db_path, "downgrade", BASE_REVISION)
    assert downgraded.returncode == 0, downgraded.stderr
    with sqlite3.connect(db_path) as connection:
        tables_after_downgrade = _table_names(connection)
        revision_after_downgrade = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
    assert {
        "hotel_provider_budget",
        "hotel_provider_budget_reservation",
        "hotel_sweep_lease",
        "hotel_provider_circuit",
    }.isdisjoint(tables_after_downgrade)
    assert revision_after_downgrade == BASE_REVISION

    reupgraded = _run(db_path, "upgrade", "head")
    assert reupgraded.returncode == 0, reupgraded.stderr
    with sqlite3.connect(db_path) as connection:
        assert {
            "hotel_provider_budget",
            "hotel_provider_budget_reservation",
            "hotel_sweep_lease",
            "hotel_provider_circuit",
        }.issubset(_table_names(connection))
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0] == HEAD_REVISION
