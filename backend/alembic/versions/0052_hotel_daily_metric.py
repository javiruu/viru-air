"""add aggregated hotel daily metrics

Revision ID: 0052_hotel_daily_metric
Revises: 0051_hotel_notification_delivery_error_class
Create Date: 2026-08-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0052_hotel_daily_metric"
down_revision: Union[str, None] = "0051_hotel_notification_delivery_error_class"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hotel_daily_metric",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("metric_name", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "metric_date",
            "metric_name",
            "provider",
            "outcome",
            name="uq_hotel_daily_metric_key",
        ),
    )
    op.create_index("ix_hotel_daily_metric_date", "hotel_daily_metric", ["metric_date"], unique=False)
    op.create_index(
        "ix_hotel_daily_metric_name_date",
        "hotel_daily_metric",
        ["metric_name", "metric_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hotel_daily_metric_name_date", table_name="hotel_daily_metric")
    op.drop_index("ix_hotel_daily_metric_date", table_name="hotel_daily_metric")
    op.drop_table("hotel_daily_metric")
