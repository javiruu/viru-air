from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0040_add_qs_popularity_daily"
down_revision: str | None = "0039_add_community_pricing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quick_search_popularity_daily",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("search_date", sa.Date(), nullable=False),
        sa.Column("origin_iata", sa.String(length=3), nullable=False),
        sa.Column("destination_iata", sa.String(length=3), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("search_count", sa.Integer(), nullable=False),
        sa.Column("first_searched_at", sa.DateTime(), nullable=False),
        sa.Column("last_searched_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "search_date",
            "origin_iata",
            "destination_iata",
            "currency",
            name="uq_qs_popularity_daily_route_currency",
        ),
    )
    op.create_index(
        "ix_qs_popularity_daily_date_count",
        "quick_search_popularity_daily",
        ["search_date", "search_count"],
        unique=False,
    )
    op.create_index(
        "ix_qs_popularity_daily_route",
        "quick_search_popularity_daily",
        ["origin_iata", "destination_iata", "search_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_qs_popularity_daily_route",
        table_name="quick_search_popularity_daily",
    )
    op.drop_index(
        "ix_qs_popularity_daily_date_count",
        table_name="quick_search_popularity_daily",
    )
    op.drop_table("quick_search_popularity_daily")
