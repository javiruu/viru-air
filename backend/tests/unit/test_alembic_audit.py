from pathlib import Path
import builtins
import os
import sqlite3
import subprocess
import sys
import tempfile

from app.infrastructure.db.alembic_audit import build_audit_payload, inspect_database_revision


def test_current_alembic_chain_has_no_missing_down_revisions() -> None:
    backend_root = Path(__file__).resolve().parents[2]

    payload, exit_code = build_audit_payload(
        backend_root,
        db_url="sqlite:///:memory:",
    )

    assert exit_code == 0
    assert payload["chain_ok"] is True
    assert payload["missing_down_revisions"] == []
    assert payload["duplicate_revisions"] == {}
    assert payload["files_missing_identifiers"] == []
    assert payload["heads"] == ["0037_reconcile_live_snapshot_uniqueness"]


def test_inspect_database_revision_flags_orphan_alembic_version(tmp_path: Path) -> None:
    db_path = tmp_path / "orphan-alembic.db"
    payload, exit_code = build_audit_payload(
        Path(__file__).resolve().parents[2],
        db_url=f"sqlite:///{db_path}",
    )
    known_revisions = payload["known_revisions"]

    import sqlite3

    connection = sqlite3.connect(db_path)
    try:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        connection.execute(
            "INSERT INTO alembic_version(version_num) VALUES (?)",
            ("0025_alert_rule_compare_against",),
        )
        connection.commit()
    finally:
        connection.close()

    db_state = inspect_database_revision(f"sqlite:///{db_path}", known_revisions)

    assert db_state["status"] == "invalid_revision"
    assert db_state["invalid_revisions"] == ["0025_alert_rule_compare_against"]


def test_inspect_database_revision_reports_broken_sqlalchemy_import(monkeypatch) -> None:
    real_import = builtins.__import__

    def fail_sqlalchemy_import(name, *args, **kwargs):
        if name == "sqlalchemy" or name.startswith("sqlalchemy."):
            raise ImportError("broken SQLAlchemy install")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_sqlalchemy_import)

    db_state = inspect_database_revision("sqlite:///:memory:", [])

    assert db_state["status"] == "db_error"
    assert db_state["error"] == "sqlalchemy_unavailable: broken SQLAlchemy install"


def test_clean_upgrade_keeps_alembic_check_green() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    fd, db_path = tempfile.mkstemp(suffix="-alembic-clean.db", dir=backend_root)
    os.close(fd)

    env = os.environ.copy()
    env["DB_URL"] = f"sqlite:///./{Path(db_path).name}"

    try:
        upgrade = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert upgrade.returncode == 0, upgrade.stderr

        check = subprocess.run(
            [sys.executable, "-m", "alembic", "check"],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert check.returncode == 0, check.stderr or check.stdout
    finally:
        try:
            sqlite3.connect(db_path).close()
        except sqlite3.Error:
            pass
        try:
            os.remove(db_path)
        except OSError:
            pass


def test_upgrade_repairs_orphan_live_tracking_tables_created_by_orm() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    fd, db_path = tempfile.mkstemp(suffix="-alembic-orphan-live.db", dir=backend_root)
    os.close(fd)
    env = os.environ.copy()
    env["DB_URL"] = f"sqlite:///./{Path(db_path).name}"

    try:
        baseline = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "upgrade",
                "0034_add_quick_search_popularity_counter",
            ],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert baseline.returncode == 0, baseline.stderr
        connection = sqlite3.connect(db_path)
        try:
            connection.executescript(
                """
                CREATE TABLE watch_tracked_flight_leg (
                    id VARCHAR(36) PRIMARY KEY, watch_id VARCHAR(36) NOT NULL,
                    sequence INTEGER NOT NULL, flight_instance_fingerprint VARCHAR(64) NOT NULL,
                    carrier_code VARCHAR(16), flight_number VARCHAR(32), origin_iata VARCHAR(3) NOT NULL,
                    destination_iata VARCHAR(3) NOT NULL, scheduled_departure_at DATETIME,
                    scheduled_arrival_at DATETIME, identity_source VARCHAR(24) NOT NULL,
                    created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                    CONSTRAINT uq_watch_tracked_flight_leg_sequence UNIQUE (watch_id, sequence)
                );
                CREATE INDEX ix_watch_tracked_flight_leg_watch_id ON watch_tracked_flight_leg (watch_id);
                CREATE INDEX ix_watch_tracked_flight_leg_instance ON watch_tracked_flight_leg (flight_instance_fingerprint);
                CREATE TABLE flight_operational_snapshot (
                    id VARCHAR(36) PRIMARY KEY, flight_instance_fingerprint VARCHAR(64) NOT NULL,
                    provider VARCHAR(40) NOT NULL, provider_flight_id VARCHAR(80), flight_number VARCHAR(32),
                    callsign VARCHAR(32), icao24 VARCHAR(16), status VARCHAR(24) NOT NULL,
                    status_raw VARCHAR(64), observed_at DATETIME NOT NULL, expires_at DATETIME NOT NULL,
                    scheduled_departure_at DATETIME, estimated_departure_at DATETIME, actual_departure_at DATETIME,
                    scheduled_arrival_at DATETIME, estimated_arrival_at DATETIME, actual_arrival_at DATETIME,
                    departure_terminal VARCHAR(32), departure_gate VARCHAR(32), arrival_terminal VARCHAR(32),
                    arrival_gate VARCHAR(32), departure_delay_minutes INTEGER, arrival_delay_minutes INTEGER,
                    latitude NUMERIC(9,6), longitude NUMERIC(9,6), altitude_m NUMERIC(10,2),
                    speed_mps NUMERIC(10,2), heading_deg NUMERIC(6,2), on_ground BOOLEAN,
                    registration VARCHAR(32), aircraft_iata VARCHAR(16), aircraft_icao VARCHAR(16),
                    data_quality VARCHAR(24) NOT NULL, created_at DATETIME NOT NULL
                );
                CREATE INDEX ix_flight_operational_snapshot_instance_observed
                    ON flight_operational_snapshot (flight_instance_fingerprint, observed_at);
                CREATE INDEX ix_flight_operational_snapshot_expires ON flight_operational_snapshot (expires_at);
                CREATE INDEX ix_flight_operational_snapshot_provider_flight
                    ON flight_operational_snapshot (provider, provider_flight_id);
                CREATE INDEX ix_flight_operational_snapshot_observed_at ON flight_operational_snapshot (observed_at);
                CREATE TABLE flight_operational_refresh_lock (
                    flight_instance_fingerprint VARCHAR(64) PRIMARY KEY, lock_token VARCHAR(64) NOT NULL,
                    acquired_at DATETIME NOT NULL, expires_at DATETIME NOT NULL
                );
                CREATE UNIQUE INDEX ix_flight_operational_refresh_lock_lock_token
                    ON flight_operational_refresh_lock (lock_token);
                CREATE INDEX ix_flight_operational_refresh_lock_expires_at
                    ON flight_operational_refresh_lock (expires_at);
                CREATE TABLE flight_provider_quota (
                    provider VARCHAR(40) PRIMARY KEY, window_key VARCHAR(10) NOT NULL,
                    units_used INTEGER NOT NULL, blocked_until DATETIME,
                    block_reason VARCHAR(32), updated_at DATETIME NOT NULL
                );
                CREATE INDEX ix_flight_provider_quota_blocked_until
                    ON flight_provider_quota (blocked_until);
                """
            )
            connection.commit()
        finally:
            connection.close()

        upgrade = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert upgrade.returncode == 0, upgrade.stderr

        connection = sqlite3.connect(db_path)
        try:
            leg_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(watch_tracked_flight_leg)")
            }
            lock_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(flight_operational_refresh_lock)")
            }
            lock_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(flight_operational_refresh_lock)")
            }
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            snapshot_unique = [
                {column[2] for column in connection.execute(f"PRAGMA index_info('{index[1]}')")}
                for index in connection.execute("PRAGMA index_list(flight_operational_snapshot)")
                if index[2] == 1
            ]
        finally:
            connection.close()
        assert "departure_date_local" in leg_columns
        assert "outcome" in lock_columns
        assert "ix_flight_operational_refresh_lock_token" in lock_indexes
        assert "ix_flight_operational_refresh_lock_expires" in lock_indexes
        assert {"flight_instance_fingerprint", "provider", "observed_at"} in snapshot_unique
        assert revision == "0037_reconcile_live_snapshot_uniqueness"
    finally:
        try:
            os.remove(db_path)
        except OSError:
            pass
