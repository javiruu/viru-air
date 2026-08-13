"""add private hotel saved searches

Revision ID: 0056_hotel_saved_searches
Revises: 0055_hotel_alert_baseline_metadata
Create Date: 2026-08-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0056_hotel_saved_searches"
down_revision: Union[str, None] = "0055_hotel_alert_baseline_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hotel_saved_search",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False, server_default="hotel-search-v1"),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("canonical_query_json", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "fingerprint", name="uq_hotel_saved_search_user_fingerprint"),
        sa.CheckConstraint("status IN ('active', 'paused')", name="ck_hotel_saved_search_status"),
    )
    op.create_index("ix_hotel_saved_search_user_id", "hotel_saved_search", ["user_id"])
    op.create_index(
        "ix_hotel_saved_search_user_status_updated",
        "hotel_saved_search",
        ["user_id", "status", "updated_at"],
    )
    op.create_index("ix_hotel_saved_search_status", "hotel_saved_search", ["status"])


def downgrade() -> None:
    op.drop_index("ix_hotel_saved_search_status", table_name="hotel_saved_search")
    op.drop_index("ix_hotel_saved_search_user_status_updated", table_name="hotel_saved_search")
    op.drop_index("ix_hotel_saved_search_user_id", table_name="hotel_saved_search")
    op.drop_table("hotel_saved_search")
