from pathlib import Path
import logging
import sqlite3

from alembic import command
from alembic.config import Config
import pytest


def build_config(db_path: Path) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def test_canonical_stay_offer_schema_expands_and_rolls_back_without_v1_removal(tmp_path: Path) -> None:
    db_path = tmp_path / "hotel-canonical-stay-offer.db"
    config = build_config(db_path)

    command.upgrade(config, "head")
    with sqlite3.connect(db_path) as connection:
        tables = table_names(connection)
        snapshot_columns = {row[1] for row in connection.execute("PRAGMA table_info(hotel_rate_snapshot)")}
        stay_offer_columns = {row[1] for row in connection.execute("PRAGMA table_info(hotel_stay_offer)")}
        stay_watch_columns = {row[1] for row in connection.execute("PRAGMA table_info(hotel_user_stay_watch)")}
        snapshot_indexes = {row[1] for row in connection.execute("PRAGMA index_list(hotel_rate_snapshot)")}
        tracked_offer_indexes = {row[1] for row in connection.execute("PRAGMA index_list(hotel_tracked_offer)")}
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]

    assert {"hotel_stay_offer", "hotel_user_stay_watch", "hotel_tracked_offer"}.issubset(tables)
    assert {
        "stay_offer_id",
        "observed_at",
        "stay_query_fingerprint",
        "offer_fingerprint",
        "snapshot_outcome",
        "price_semantics",
        "amount_base",
        "amount_total",
        "fees_json",
        "conditions_completeness",
    }.issubset(snapshot_columns)
    assert {
        "canonical_hotel_id",
        "provider_hotel_id",
        "stay_query_fingerprint",
        "offer_fingerprint",
        "canonical_query_json",
    }.issubset(stay_offer_columns)
    assert {"user_id", "stay_offer_id", "legacy_tracked_offer_id", "status"}.issubset(stay_watch_columns)
    assert "ix_hotel_rate_snapshot_stay_offer_id" in snapshot_indexes
    assert "uq_hotel_tracked_offer_legacy_identity" in tracked_offer_indexes
    assert revision == "0060_revalidation_job_active_target"

    command.downgrade(config, "0056_hotel_saved_searches")
    with sqlite3.connect(db_path) as connection:
        tables_after_downgrade = table_names(connection)
        snapshot_columns_after_downgrade = {
            row[1] for row in connection.execute("PRAGMA table_info(hotel_rate_snapshot)")
        }
        revision_after_downgrade = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]

    assert {"hotel_stay_offer", "hotel_user_stay_watch"}.isdisjoint(tables_after_downgrade)
    assert "hotel_tracked_offer" in tables_after_downgrade
    assert "stay_offer_id" not in snapshot_columns_after_downgrade
    assert revision_after_downgrade == "0056_hotel_saved_searches"


def test_semantic_offer_downgrade_aborts_before_losing_distinct_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "hotel-semantic-offer-downgrade.db"
    config = build_config(db_path)
    command.upgrade(config, "head")

    statement = (
        "INSERT INTO hotel_tracked_offer ("
        "id, user_id, hotel_id, check_in, check_out, guests, provider, "
        "offer_fingerprint, currency, is_active, created_at, updated_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            statement,
            [
                ("offer-a", "user-a", "hotel-a", "2026-09-10", "2026-09-13", 2, "mock", "a" * 64, "EUR", 1, "2026-08-11 12:00:00", "2026-08-11 12:00:00"),
                ("offer-b", "user-a", "hotel-a", "2026-09-10", "2026-09-13", 2, "mock", "b" * 64, "EUR", 1, "2026-08-11 12:00:00", "2026-08-11 12:00:00"),
            ],
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="requires_semantic_offer_merge"):
        command.downgrade(config, "0057_hotel_canonical_stay_offer")

    with sqlite3.connect(db_path) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        rows = connection.execute("SELECT COUNT(*) FROM hotel_tracked_offer").fetchone()[0]
    assert revision == "0058_hotel_tracked_offer_offer_identity"
    assert rows == 2


def test_canonical_stay_offer_upgrade_keeps_application_loggers_enabled(tmp_path: Path) -> None:
    db_path = tmp_path / "hotel-canonical-stay-offer-logging.db"
    config = build_config(db_path)
    app_logger = logging.getLogger("app.hotels.makcorps")
    original_disabled = app_logger.disabled
    app_logger.disabled = False

    try:
        command.upgrade(config, "head")
        assert app_logger.disabled is False
    finally:
        app_logger.disabled = original_disabled
