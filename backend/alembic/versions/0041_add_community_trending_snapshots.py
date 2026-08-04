"""add persistent community trending snapshots

Revision ID: 0041_add_community_trending_snapshots
Revises: 0040_add_qs_popularity_daily
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0041_add_community_trending_snapshots"
down_revision: str | None = "0040_add_qs_popularity_daily"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_trending_snapshot",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reporting_date", sa.Date(), nullable=False),
        sa.Column("window_start_date", sa.Date(), nullable=False),
        sa.Column("window_end_date", sa.Date(), nullable=False),
        sa.Column("calculated_at_utc", sa.DateTime(), nullable=False),
        sa.Column("published_at_utc", sa.DateTime(), nullable=True),
        sa.Column("expires_at_utc", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("route_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('building', 'published')",
            name="ck_community_trending_snapshot_status",
        ),
        sa.CheckConstraint(
            "route_count >= 0",
            name="ck_community_trending_snapshot_route_count",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_community_trending_snapshot_status_calculated",
        "community_trending_snapshot",
        ["status", "calculated_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_community_trending_snapshot_status_expires",
        "community_trending_snapshot",
        ["status", "expires_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_community_trending_snapshot_reporting_date",
        "community_trending_snapshot",
        ["reporting_date"],
        unique=False,
    )

    op.create_table(
        "community_trending_snapshot_route",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("origin_iata", sa.String(length=3), nullable=False),
        sa.Column("destination_iata", sa.String(length=3), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("search_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "rank >= 1",
            name="ck_community_trending_snapshot_route_rank",
        ),
        sa.CheckConstraint(
            "search_count >= 0",
            name="ck_community_trending_snapshot_route_search_count",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["community_trending_snapshot.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "origin_iata",
            "destination_iata",
            name="uq_community_trending_snapshot_route",
        ),
    )
    op.create_index(
        "ix_community_trending_snapshot_route_snapshot_rank",
        "community_trending_snapshot_route",
        ["snapshot_id", "rank"],
        unique=False,
    )
    op.create_index(
        "ix_community_trending_snapshot_route_snapshot_route",
        "community_trending_snapshot_route",
        ["snapshot_id", "origin_iata", "destination_iata"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_community_trending_snapshot_route_snapshot_route",
        table_name="community_trending_snapshot_route",
    )
    op.drop_index(
        "ix_community_trending_snapshot_route_snapshot_rank",
        table_name="community_trending_snapshot_route",
    )
    op.drop_table("community_trending_snapshot_route")

    op.drop_index(
        "ix_community_trending_snapshot_reporting_date",
        table_name="community_trending_snapshot",
    )
    op.drop_index(
        "ix_community_trending_snapshot_status_expires",
        table_name="community_trending_snapshot",
    )
    op.drop_index(
        "ix_community_trending_snapshot_status_calculated",
        table_name="community_trending_snapshot",
    )
    op.drop_table("community_trending_snapshot")
