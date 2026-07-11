"""add quick search popularity counter table

Revision ID: 0034_add_quick_search_popularity_counter
Revises: 0033_add_quick_search_provider_lock
Create Date: 2026-07-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0034_add_quick_search_popularity_counter"
down_revision: str | None = "0033_add_quick_search_provider_lock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {str(index["name"]) for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "quick_search_popularity_counter" in _table_names(inspector):
        return

    op.create_table(
        "quick_search_popularity_counter",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("origin_iata", sa.String(length=3), nullable=False),
        sa.Column("destination_iata", sa.String(length=3), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'EUR'")),
        sa.Column("search_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("first_searched_at", sa.DateTime(), nullable=False),
        sa.Column("last_searched_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "origin_iata",
            "destination_iata",
            "travel_date",
            "currency",
            name="uq_qs_popularity_route_day_currency",
        ),
    )
    op.create_index("ix_qs_popularity_count", "quick_search_popularity_counter", ["search_count"], unique=False)
    op.create_index(
        "ix_qs_popularity_route",
        "quick_search_popularity_counter",
        ["origin_iata", "destination_iata", "travel_date"],
        unique=False,
    )
    op.create_index(
        "ix_qs_popularity_last_seen",
        "quick_search_popularity_counter",
        ["last_searched_at"],
        unique=False,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "quick_search_popularity_counter" not in _table_names(inspector):
        return

    indexes = _index_names(inspector, "quick_search_popularity_counter")
    for index_name in (
        "ix_qs_popularity_count",
        "ix_qs_popularity_route",
        "ix_qs_popularity_last_seen",
    ):
        if index_name in indexes:
            op.drop_index(index_name, table_name="quick_search_popularity_counter")
    op.drop_table("quick_search_popularity_counter")
