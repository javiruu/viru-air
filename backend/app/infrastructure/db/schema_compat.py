from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.infrastructure.db.session import Base


SEARCH_PREFERENCE_COLUMN_PATCHES = (
    ("include_nearby_origins_default", "ALTER TABLE user_preference ADD COLUMN include_nearby_origins_default BOOLEAN NOT NULL DEFAULT 0"),
    ("include_nearby_destinations_default", "ALTER TABLE user_preference ADD COLUMN include_nearby_destinations_default BOOLEAN NOT NULL DEFAULT 0"),
    ("country_price_hint_mode_default", "ALTER TABLE user_preference ADD COLUMN country_price_hint_mode_default VARCHAR(16) NOT NULL DEFAULT 'min'"),
    (
        "calendar_hint_bucket_mode_default",
        "ALTER TABLE user_preference ADD COLUMN calendar_hint_bucket_mode_default VARCHAR(24) NOT NULL DEFAULT 'monthly_terciles'",
    ),
    (
        "calendar_hint_guideline_low_max_default",
        "ALTER TABLE user_preference ADD COLUMN calendar_hint_guideline_low_max_default NUMERIC(10,2) NOT NULL DEFAULT 90",
    ),
    (
        "calendar_hint_guideline_mid_max_default",
        "ALTER TABLE user_preference ADD COLUMN calendar_hint_guideline_mid_max_default NUMERIC(10,2) NOT NULL DEFAULT 150",
    ),
    ("depart_before_default", "ALTER TABLE user_preference ADD COLUMN depart_before_default VARCHAR(5)"),
    ("strict_filters_default", "ALTER TABLE user_preference ADD COLUMN strict_filters_default BOOLEAN NOT NULL DEFAULT 1"),
)


def ensure_search_preference_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "user_preference" not in tables:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("user_preference")}
    missing_patches = [
        ddl for column_name, ddl in SEARCH_PREFERENCE_COLUMN_PATCHES if column_name not in existing_columns
    ]
    if not missing_patches:
        return

    with engine.begin() as connection:
        for ddl in missing_patches:
            connection.execute(text(ddl))


def ensure_door_to_door_tables(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    table_names = {
        "door_to_door_saved_location",
        "door_to_door_search_history",
        "door_to_door_chosen_option",
    }
    missing = [Base.metadata.tables[name] for name in table_names if name not in existing_tables]
    if missing:
        Base.metadata.create_all(bind=engine, tables=missing)
