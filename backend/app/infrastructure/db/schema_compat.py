from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


SEARCH_PREFERENCE_COLUMN_PATCHES = (
    ("include_nearby_origins_default", "ALTER TABLE user_preference ADD COLUMN include_nearby_origins_default BOOLEAN NOT NULL DEFAULT 0"),
    ("include_nearby_destinations_default", "ALTER TABLE user_preference ADD COLUMN include_nearby_destinations_default BOOLEAN NOT NULL DEFAULT 0"),
    ("country_price_hint_mode_default", "ALTER TABLE user_preference ADD COLUMN country_price_hint_mode_default VARCHAR(16) NOT NULL DEFAULT 'min'"),
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
