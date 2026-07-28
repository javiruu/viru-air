"""add anonymous community price reports

Revision ID: 0039_add_community_pricing
Revises: 0038_add_fare_comparison_profile
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0039_add_community_pricing"
down_revision: str | None = "0038_add_fare_comparison_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_price_report",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("watch_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("trigger_reason", sa.String(length=20), nullable=False),
        sa.Column("flew", sa.Boolean(), nullable=False),
        sa.Column("price_per_traveler", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(flew = false AND price_per_traveler IS NULL) "
            "OR (flew = true AND price_per_traveler > 0)",
            name="ck_community_price_report_flew_price",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["watch_id"], ["flight_watch.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("watch_id", name="uq_community_price_report_watch"),
    )
    op.create_index(
        "ix_community_price_report_user",
        "community_price_report",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_community_price_report_user", table_name="community_price_report")
    op.drop_table("community_price_report")
