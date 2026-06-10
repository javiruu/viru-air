"""add quick_search_cache_entry for shared persistent cross-user cache (V2.1)

Revision ID: 0030
Revises: 0029
Create Date: 2026-06-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "quick_search_cache_entry" in _table_names(inspector):
        return

    op.create_table(
        "quick_search_cache_entry",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("origin_iata", sa.String(3), nullable=False),
        sa.Column("destination_iata", sa.String(3), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'ready'")),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default=sa.text("86400")),
        sa.Column("expires_at_utc", sa.DateTime(), nullable=False),
        sa.Column("captured_at_utc", sa.DateTime(), nullable=False),
        sa.Column("last_accessed_at_utc", sa.DateTime(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("provider_latency_ms", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "origin_iata",
            "destination_iata",
            "travel_date",
            "provider",
            "source_hash",
            name="uq_quick_search_cache_unit",
        ),
    )

    op.create_index(
        "ix_qs_cache_lookup",
        "quick_search_cache_entry",
        ["origin_iata", "destination_iata", "travel_date", "provider"],
    )
    op.create_index(
        "ix_qs_cache_expires",
        "quick_search_cache_entry",
        ["expires_at_utc"],
    )
    op.create_index(
        "ix_qs_cache_status",
        "quick_search_cache_entry",
        ["status"],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "quick_search_cache_entry" not in _table_names(inspector):
        return

    indexes = _index_names(inspector, "quick_search_cache_entry")
    for index_name in ("ix_qs_cache_lookup", "ix_qs_cache_expires", "ix_qs_cache_status"):
        if index_name in indexes:
            op.drop_index(index_name, table_name="quick_search_cache_entry")

    op.drop_table("quick_search_cache_entry")
