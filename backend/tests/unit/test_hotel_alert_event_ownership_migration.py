from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_hotel_alert_event_ownership_migration_backfills_rule_owner(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    db_path = tmp_path / "hotel-event-ownership.db"
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.upgrade(config, "0041_add_community_trending_snapshots")
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as connection:
            user_id = "migration-user"
            hotel_id = "migration-hotel"
            rule_id = "migration-rule"
            event_id = "migration-event"
            connection.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, is_verified, locale, timezone, created_at) "
                    "VALUES (:id, :email, :password_hash, 0, 'es', 'Europe/Madrid', CURRENT_TIMESTAMP)"
                ),
                {"id": user_id, "email": "migration-owner@viru.dev", "password_hash": "hash"},
            )
            connection.execute(
                text(
                    "INSERT INTO hotel_property "
                    "(id, canonical_name, normalized_name, normalized_city, city, country_code, created_at, updated_at) "
                    "VALUES (:id, 'Migration Hotel', 'migration hotel', 'madrid', 'Madrid', 'ES', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": hotel_id},
            )
            connection.execute(
                text(
                    "INSERT INTO hotel_alert_rule "
                    "(id, user_id, hotel_id, rule_type, threshold_amount, is_active, compare_against) "
                    "VALUES (:id, :user_id, :hotel_id, 'price_below', 100, 1, 'snapshot_previous')"
                ),
                {"id": rule_id, "user_id": user_id, "hotel_id": hotel_id},
            )
            connection.execute(
                text(
                    "INSERT INTO hotel_alert_event "
                    "(id, rule_id, hotel_id, event_type, message, created_at) "
                    "VALUES (:id, :rule_id, :hotel_id, 'price_below', 'legacy', CURRENT_TIMESTAMP)"
                ),
                {"id": event_id, "rule_id": rule_id, "hotel_id": hotel_id},
            )

        command.upgrade(config, "0042_hotel_alert_event_ownership")
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT user_id FROM hotel_alert_event WHERE id = :id"),
                {"id": event_id},
            ).one()
            assert row.user_id == user_id
    finally:
        engine.dispose()


def test_hotel_alert_event_ownership_migration_recovers_after_sqlite_partial_add_column(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    db_path = tmp_path / "hotel-event-ownership-partial.db"
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.upgrade(config, "0041_add_community_trending_snapshots")
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE hotel_alert_event ADD COLUMN user_id VARCHAR(36)"))

        command.upgrade(config, "0042_hotel_alert_event_ownership")

        with engine.connect() as connection:
            indexes = {index["name"] for index in connection.dialect.get_indexes(connection, "hotel_alert_event")}
            assert "ix_hotel_alert_event_user_id" in indexes
    finally:
        engine.dispose()
