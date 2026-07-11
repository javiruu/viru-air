from app.infrastructure.db.models import (
    FlightOfferCacheEntry,
    FlightPriceObservation,
    QuickSearchCacheEntry,
    QuickSearchNegativeCacheEntry,
    QuickSearchPopularityCounter,
)


GLOBAL_FARE_MEMORY_MODELS = (
    QuickSearchCacheEntry,
    QuickSearchNegativeCacheEntry,
    FlightOfferCacheEntry,
    FlightPriceObservation,
    QuickSearchPopularityCounter,
)


def test_global_fare_memory_tables_do_not_store_user_id():
    for model in GLOBAL_FARE_MEMORY_MODELS:
        column_names = {column.name for column in model.__table__.columns}

        assert "user_id" not in column_names, f"{model.__name__} must stay cross-user and anonymous"


def test_global_fare_memory_tables_do_not_reference_users():
    for model in GLOBAL_FARE_MEMORY_MODELS:
        foreign_key_targets = {
            f"{foreign_key.column.table.name}.{foreign_key.column.name}"
            for foreign_key in model.__table__.foreign_keys
        }

        assert not any(target.startswith("users.") for target in foreign_key_targets), (
            f"{model.__name__} must not reference users: {sorted(foreign_key_targets)}"
        )
