"""add per-run hotel provider latency aggregates

Revision ID: 0053_hotel_provider_latency_aggregate
Revises: 0052_hotel_daily_metric
Create Date: 2026-08-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0053_hotel_provider_latency_aggregate"
down_revision: Union[str, None] = "0052_hotel_daily_metric"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hotel_provider_latency_aggregate",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_run_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("error_code", sa.String(length=32), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("total_duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("min_duration_ms", sa.Integer(), nullable=False),
        sa.Column("max_duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "sample_count >= 0",
            name="ck_hotel_provider_latency_sample_count_nonnegative",
        ),
        sa.CheckConstraint(
            "total_duration_ms >= 0",
            name="ck_hotel_provider_latency_total_duration_nonnegative",
        ),
        sa.CheckConstraint(
            "min_duration_ms >= 0",
            name="ck_hotel_provider_latency_min_duration_nonnegative",
        ),
        sa.CheckConstraint(
            "max_duration_ms >= 0",
            name="ck_hotel_provider_latency_max_duration_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["provider_run_id"],
            ["hotel_provider_run.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_run_id",
            "provider",
            "operation",
            "outcome",
            "error_code",
            name="uq_hotel_provider_latency_aggregate_key",
        ),
    )
    op.create_index(
        "ix_hotel_provider_latency_aggregate_run",
        "hotel_provider_latency_aggregate",
        ["provider_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_hotel_provider_latency_aggregate_provider_operation_created",
        "hotel_provider_latency_aggregate",
        ["provider", "operation", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hotel_provider_latency_aggregate_provider_operation_created",
        table_name="hotel_provider_latency_aggregate",
    )
    op.drop_index(
        "ix_hotel_provider_latency_aggregate_run",
        table_name="hotel_provider_latency_aggregate",
    )
    op.drop_table("hotel_provider_latency_aggregate")
