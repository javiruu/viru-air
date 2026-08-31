import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
BASE_REVISION = "0040_add_qs_popularity_daily"
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


def _table_names(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }


def test_upgrade_creates_snapshot_tables_and_constraints(tmp_path: Path) -> None:
    db_path = tmp_path / "community-trending-upgrade.db"

    upgraded = _run(db_path, "upgrade", "head")

    assert upgraded.returncode == 0, upgraded.stderr
    with sqlite3.connect(db_path) as connection:
        tables = _table_names(db_path)
        assert "community_trending_snapshot" in tables
        assert "community_trending_snapshot_route" in tables
        snapshot_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(community_trending_snapshot)"
            )
        }
        route_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(community_trending_snapshot_route)"
            )
        }
        route_indexes = {
            row[1]
            for row in connection.execute(
                "PRAGMA index_list(community_trending_snapshot_route)"
            )
        }
        route_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(community_trending_snapshot_route)"
        ).fetchall()
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]

    assert snapshot_columns == {
        "id",
        "reporting_date",
        "window_start_date",
        "window_end_date",
        "calculated_at_utc",
        "published_at_utc",
        "expires_at_utc",
        "status",
        "route_count",
        "created_at",
    }
    assert route_columns == {
        "id",
        "snapshot_id",
        "origin_iata",
        "destination_iata",
        "rank",
        "search_count",
        "created_at",
    }
    assert {
        "ix_community_trending_snapshot_route_snapshot_rank",
        "ix_community_trending_snapshot_route_snapshot_route",
        "sqlite_autoindex_community_trending_snapshot_route_1",
    }.issubset(route_indexes)
    assert len(route_foreign_keys) == 1
    assert route_foreign_keys[0][2] == "community_trending_snapshot"
    assert route_foreign_keys[0][6] == "CASCADE"
    assert revision == HEAD_REVISION


def test_snapshot_route_constraints_and_cascade_work_on_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "community-trending-integrity.db"
    upgraded = _run(db_path, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO community_trending_snapshot (
                id, reporting_date, window_start_date, window_end_date,
                calculated_at_utc, published_at_utc, expires_at_utc,
                status, route_count, created_at
            ) VALUES (
                'snapshot-1', '2026-08-04', '2026-07-29', '2026-08-04',
                '2026-08-04 10:00:00', '2026-08-04 10:00:01',
                '2026-08-04 11:00:00', 'published', 1, '2026-08-04 10:00:00'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO community_trending_snapshot_route (
                id, snapshot_id, origin_iata, destination_iata, rank, search_count, created_at
            ) VALUES (
                'route-1', 'snapshot-1', 'MAD', 'BCN', 1, 12, '2026-08-04 10:00:00'
            )
            """
        )
        with_error = connection.execute
        try:
            with_error(
                """
                INSERT INTO community_trending_snapshot_route (
                    id, snapshot_id, origin_iata, destination_iata, rank, search_count, created_at
                ) VALUES ('route-invalid', 'snapshot-1', 'MAD', 'LIS', 0, 4, '2026-08-04 10:00:00')
                """
            )
            raise AssertionError("rank constraint accepted zero")
        except sqlite3.IntegrityError:
            pass
        try:
            with_error(
                """
                INSERT INTO community_trending_snapshot_route (
                    id, snapshot_id, origin_iata, destination_iata, rank, search_count, created_at
                ) VALUES ('route-invalid-2', 'snapshot-1', 'MAD', 'LIS', 2, -1, '2026-08-04 10:00:00')
                """
            )
            raise AssertionError("search_count constraint accepted a negative value")
        except sqlite3.IntegrityError:
            pass
        connection.execute(
            "DELETE FROM community_trending_snapshot WHERE id = 'snapshot-1'"
        )
        remaining_routes = connection.execute(
            "SELECT COUNT(*) FROM community_trending_snapshot_route"
        ).fetchone()[0]

    assert remaining_routes == 0


def test_downgrade_removes_snapshot_tables_and_upgrade_recreates_them(tmp_path: Path) -> None:
    db_path = tmp_path / "community-trending-roundtrip.db"

    upgraded = _run(db_path, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr
    downgraded = _run(db_path, "downgrade", BASE_REVISION)
    assert downgraded.returncode == 0, downgraded.stderr
    assert "community_trending_snapshot" not in _table_names(db_path)
    assert "community_trending_snapshot_route" not in _table_names(db_path)

    reupgraded = _run(db_path, "upgrade", "head")
    assert reupgraded.returncode == 0, reupgraded.stderr
    assert "community_trending_snapshot" in _table_names(db_path)
    assert "community_trending_snapshot_route" in _table_names(db_path)


def test_importing_app_does_not_create_future_snapshot_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "community-trending-import.db"
    baseline = _run(db_path, "upgrade", BASE_REVISION)
    assert baseline.returncode == 0, baseline.stderr
    before = _table_names(db_path)

    imported = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=BACKEND_ROOT,
        env=_env(db_path),
        capture_output=True,
        text=True,
        check=False,
    )

    assert imported.returncode == 0, imported.stderr
    assert _table_names(db_path) == before
    assert "community_trending_snapshot" not in before
