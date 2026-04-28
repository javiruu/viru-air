from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.infrastructure.db.schema_compat import ensure_search_preference_columns


def test_ensure_search_preference_columns_upgrades_legacy_user_preference_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-pref.db"
    engine = create_engine(f"sqlite:///{db_path}")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE user_preference (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    default_radius_km INTEGER NOT NULL DEFAULT 150,
                    include_stops_default BOOLEAN NOT NULL DEFAULT 0,
                    avoid_departure_before VARCHAR(5),
                    preferred_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
                    language VARCHAR(8) NOT NULL DEFAULT 'es'
                )
                """
            )
        )

    ensure_search_preference_columns(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("user_preference")}
    assert "include_nearby_origins_default" in columns
    assert "include_nearby_destinations_default" in columns
    assert "depart_before_default" in columns
    assert "strict_filters_default" in columns
