"""add quick search provider lock table

Revision ID: 0033_add_quick_search_provider_lock
Revises: 0032_add_flight_instance_fingerprint
Create Date: 2026-07-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0033_add_quick_search_provider_lock"
down_revision: str | None = "0032_add_flight_instance_fingerprint"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {str(index["name"]) for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "quick_search_provider_lock" in _table_names(inspector):
        return

    op.create_table(
        "quick_search_provider_lock",
        sa.Column("lock_key", sa.String(length=64), nullable=False),
        sa.Column("origin_iata", sa.String(length=3), nullable=False),
        sa.Column("destination_iata", sa.String(length=3), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'EUR'")),
        sa.Column("lock_token", sa.String(length=64), nullable=False),
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("lock_key"),
    )
    op.create_index("ix_qs_provider_lock_expires", "quick_search_provider_lock", ["expires_at"], unique=False)
    op.create_index(
        "ix_qs_provider_lock_route",
        "quick_search_provider_lock",
        ["origin_iata", "destination_iata", "travel_date", "provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quick_search_provider_lock_lock_token"),
        "quick_search_provider_lock",
        ["lock_token"],
        unique=False,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "quick_search_provider_lock" not in _table_names(inspector):
        return

    indexes = _index_names(inspector, "quick_search_provider_lock")
    for index_name in (
        "ix_qs_provider_lock_expires",
        "ix_qs_provider_lock_route",
        op.f("ix_quick_search_provider_lock_lock_token"),
    ):
        if index_name in indexes:
            op.drop_index(index_name, table_name="quick_search_provider_lock")
    op.drop_table("quick_search_provider_lock")
