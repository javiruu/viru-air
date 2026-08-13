import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile


def _run_alembic(backend_root: Path, db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DB_URL"] = f"sqlite:///./{db_path.name}"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=backend_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_tracking_lifecycle_migration_upgrades_and_refuses_a_lossy_downgrade() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    fd, raw_path = tempfile.mkstemp(suffix="-tracking-lifecycle.db", dir=backend_root)
    os.close(fd)
    db_path = Path(raw_path)
    try:
        assert _run_alembic(backend_root, db_path, "upgrade", "0058_hotel_tracked_offer_offer_identity").returncode == 0
        assert _run_alembic(backend_root, db_path, "upgrade", "0059_hotel_tracking_lifecycle").returncode == 0

        with sqlite3.connect(db_path) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(hotel_tracked_offer)")}
            assert {"lifecycle_state", "lifecycle_version", "lifecycle_changed_at"} <= columns
            connection.execute(
                "INSERT INTO hotel_tracked_offer_lifecycle_event "
                "(id, tracked_offer_id, user_id, from_state, to_state, action, source, state_version, created_at) "
                "VALUES ('event-1', 'offer-1', 'user-1', 'active', 'paused', 'pause', 'test', 2, '2026-08-12 00:00:00')"
            )
            connection.commit()

        downgrade = _run_alembic(backend_root, db_path, "downgrade", "0058_hotel_tracked_offer_offer_identity")
        assert downgrade.returncode != 0
        assert "hotel_tracking_0059_downgrade_requires_lifecycle_event_retention" in downgrade.stderr
        with sqlite3.connect(db_path) as connection:
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        assert revision == ("0059_hotel_tracking_lifecycle",)
    finally:
        try:
            os.remove(db_path)
        except OSError:
            pass
