from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_hotel_provider_run_outcomes_migration_adds_json_column(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    db_path = tmp_path / "hotel-provider-run-outcomes.db"
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.upgrade(config, "0042_hotel_alert_event_ownership")
    engine = create_engine(f"sqlite:///{db_path}")
    outcomes = '{"offers_scanned": 2, "snapshots_created": 1, "provider_fetch_failed": 1}'
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO hotel_provider_run "
                    "(id, provider, started_at, status, items_processed) "
                    "VALUES ('run-before-0043', 'mock', CURRENT_TIMESTAMP, 'completed', 0)"
                )
            )

        command.upgrade(config, "0043_hotel_provider_run_outcomes")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE hotel_provider_run SET tracked_outcomes = :outcomes "
                    "WHERE id = 'run-before-0043'"
                ),
                {"outcomes": outcomes},
            )
            row = connection.execute(
                text("SELECT tracked_outcomes FROM hotel_provider_run WHERE id = 'run-before-0043'")
            ).one()
            assert row.tracked_outcomes == outcomes
    finally:
        engine.dispose()
