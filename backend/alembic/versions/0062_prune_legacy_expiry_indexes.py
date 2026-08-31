"""remove redundant expiry indexes left by the legacy ORM bootstrap

Revision ID: 0062_prune_legacy_expiry_indexes
Revises: 0061_calendar_price_observations
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0062_prune_legacy_expiry_indexes"
down_revision: str | None = "0061_calendar_price_observations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGACY_INDEXES = (
    ("flight_price_observation", "ix_flight_price_observation_expires_at"),
    ("quick_search_negative_cache_entry", "ix_quick_search_negative_cache_entry_expires_at"),
    ("quick_search_provider_lock", "ix_quick_search_provider_lock_expires_at"),
)


def upgrade() -> None:
    """Prune duplicate indexes while preserving the migration-managed equivalents."""
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    for table_name, index_name in LEGACY_INDEXES:
        if table_name not in tables:
            continue
        indexes = {str(index["name"]) for index in inspector.get_indexes(table_name)}
        if index_name in indexes:
            op.drop_index(index_name, table_name=table_name)


def downgrade() -> None:
    """The removed indexes were redundant bootstrap artifacts, not schema contract."""
