from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import tempfile


def test_flight_instance_migration_upgrades_and_downgrades_sqlite_columns() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    fd, db_path = tempfile.mkstemp(suffix="-flight-instance.db", dir=backend_root)
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
        upgraded_columns = _column_names(db_path)
        assert "flight_instance_fingerprint" in upgraded_columns
        assert "carrier_code" in upgraded_columns
        assert "departure_time_local" in upgraded_columns
        assert "arrival_time_local" in upgraded_columns

        downgrade = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "0031_add_user_notification_state"],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert downgrade.returncode == 0, downgrade.stderr
        downgraded_columns = _column_names(db_path)
        assert "flight_instance_fingerprint" not in downgraded_columns
        assert "carrier_code" not in downgraded_columns
        assert "departure_time_local" not in downgraded_columns
        assert "arrival_time_local" not in downgraded_columns
    finally:
        try:
            sqlite3.connect(db_path).close()
        except sqlite3.Error:
            pass
        try:
            os.remove(db_path)
        except OSError:
            pass


def _column_names(db_path: str) -> set[str]:
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("PRAGMA table_info(flight_offer_cache_entry)").fetchall()
    finally:
        connection.close()
    return {str(row[1]) for row in rows}
