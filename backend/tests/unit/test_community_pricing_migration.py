import os
from pathlib import Path
import runpy
import sqlite3
import subprocess
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
HEAD_REVISION = "0059_hotel_tracking_lifecycle"
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "0039_add_community_pricing.py"
)


def _database_environment(db_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["DB_URL"] = f"sqlite:///{db_path.as_posix()}"
    env["RUN_DB_INIT"] = "false"
    env["RUN_SEED_USERS"] = "false"
    env["WATCHLIST_STARTUP_REFRESH_ENABLED"] = "false"
    env["FARE_MEMORY_BOOT_WARMUP_ENABLED"] = "false"
    env["FARE_MEMORY_REVALIDATION_WORKER_ENABLED"] = "false"
    return env


def _run_alembic(db_path: Path, target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=BACKEND_ROOT,
        env=_database_environment(db_path),
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


def _precreate_community_price_table(db_path: Path) -> None:
    precreate = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.infrastructure.db.models import CommunityPriceReport;"
                "from app.infrastructure.db.session import engine;"
                "CommunityPriceReport.__table__.create(bind=engine)"
            ),
        ],
        cwd=BACKEND_ROOT,
        env=_database_environment(db_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert precreate.returncode == 0, precreate.stderr


def test_importing_app_does_not_create_tables_owned_by_future_migrations(
    tmp_path: Path,
) -> None:
    # Given
    db_path = tmp_path / "app-import.db"
    baseline = _run_alembic(db_path, "0038_add_fare_comparison_profile")
    assert baseline.returncode == 0, baseline.stderr
    tables_before_import = _table_names(db_path)

    # When
    imported = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=BACKEND_ROOT,
        env=_database_environment(db_path),
        capture_output=True,
        text=True,
        check=False,
    )

    # Then
    assert imported.returncode == 0, imported.stderr
    assert _table_names(db_path) == tables_before_import
    assert "community_price_report" not in tables_before_import


def test_upgrade_adopts_matching_table_created_before_revision_stamp(
    tmp_path: Path,
) -> None:
    # Given
    db_path = tmp_path / "precreated-community-price.db"
    baseline = _run_alembic(db_path, "0038_add_fare_comparison_profile")
    assert baseline.returncode == 0, baseline.stderr
    _precreate_community_price_table(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP INDEX ix_community_price_report_user")

    # When
    upgrade = _run_alembic(db_path, "head")

    # Then
    assert upgrade.returncode == 0, upgrade.stderr
    with sqlite3.connect(db_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        indexes = {
            row[1]
            for row in connection.execute(
                "PRAGMA index_list('community_price_report')"
            )
        }
    assert revision == (HEAD_REVISION,)
    assert "ix_community_price_report_user" in indexes


def test_upgrade_rejects_table_without_required_constraints(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "invalid-community-price.db"
    baseline = _run_alembic(db_path, "0038_add_fare_comparison_profile")
    assert baseline.returncode == 0, baseline.stderr
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE community_price_report (
                id VARCHAR(36) NOT NULL,
                watch_id VARCHAR(36) NOT NULL UNIQUE,
                user_id VARCHAR(36) NOT NULL,
                trigger_reason VARCHAR(20) NOT NULL,
                flew BOOLEAN NOT NULL,
                price_per_traveler NUMERIC(10, 2),
                currency VARCHAR(3) NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )

    # When
    upgrade = _run_alembic(db_path, "head")

    # Then
    assert upgrade.returncode != 0
    assert "IncompatibleCommunityPriceTableError" in upgrade.stderr
    with sqlite3.connect(db_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
    assert revision == ("0038_add_fare_comparison_profile",)


def test_upgrade_rejects_unexpected_unique_user_index(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "unexpected-user-index.db"
    baseline = _run_alembic(db_path, "0038_add_fare_comparison_profile")
    assert baseline.returncode == 0, baseline.stderr
    _precreate_community_price_table(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP INDEX ix_community_price_report_user")
        connection.execute(
            "CREATE UNIQUE INDEX unexpected_unique_user "
            "ON community_price_report (user_id)"
        )

    # When
    upgrade = _run_alembic(db_path, "head")

    # Then
    assert upgrade.returncode != 0
    assert "IncompatibleCommunityPriceTableError" in upgrade.stderr
    with sqlite3.connect(db_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
    assert revision == ("0038_add_fare_comparison_profile",)


def test_check_validation_accepts_postgresql_reflection_format() -> None:
    # Given
    normalize_check_sql = runpy.run_path(MIGRATION_PATH)["_normalize_check_sql"]
    reflected_sql = (
        "(((flew = false) AND (price_per_traveler IS NULL)) "
        "OR ((flew = true) AND (price_per_traveler > (0)::numeric)))"
    )

    # When
    normalized = normalize_check_sql(reflected_sql)

    # Then
    assert normalized == (
        "(flew=falseandprice_per_travelerisnull)"
        "or(flew=trueandprice_per_traveler>0)"
    )


def test_upgrade_rejects_check_constraint_weakened_with_or_true(
    tmp_path: Path,
) -> None:
    # Given
    db_path = tmp_path / "weakened-check-community-price.db"
    baseline = _run_alembic(db_path, "0038_add_fare_comparison_profile")
    assert baseline.returncode == 0, baseline.stderr
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE community_price_report (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                watch_id VARCHAR(36) NOT NULL,
                user_id VARCHAR(36) NOT NULL,
                trigger_reason VARCHAR(20) NOT NULL,
                flew BOOLEAN NOT NULL,
                price_per_traveler NUMERIC(10, 2),
                currency VARCHAR(3) NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT uq_community_price_report_watch UNIQUE (watch_id),
                CONSTRAINT ck_community_price_report_flew_price CHECK (
                    (flew = false AND price_per_traveler IS NULL)
                    OR (flew = true AND price_per_traveler > 0)
                    OR true
                ),
                FOREIGN KEY(watch_id) REFERENCES flight_watch(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

    # When
    upgrade = _run_alembic(db_path, "head")

    # Then
    assert upgrade.returncode != 0
    assert "IncompatibleCommunityPriceTableError" in upgrade.stderr
    with sqlite3.connect(db_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
    assert revision == ("0038_add_fare_comparison_profile",)
