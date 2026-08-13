"""add hotel provider budget ledger

Revision ID: 0044_hotel_provider_budget
Revises: 0043_hotel_provider_run_outcomes
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0044_hotel_provider_budget"
down_revision: Union[str, None] = "0043_hotel_provider_run_outcomes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hotel_provider_budget",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("window_key", sa.String(length=20), nullable=False),
        sa.Column("hard_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("units_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("units_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("units_released", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_expires_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False, server_default="local_config"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "provider",
            "operation",
            "window_key",
            name="uq_hotel_provider_budget_window",
        ),
    )
    op.create_index(
        "ix_hotel_provider_budget_provider",
        "hotel_provider_budget",
        ["provider"],
    )
    op.create_index(
        "ix_hotel_provider_budget_operation",
        "hotel_provider_budget",
        ["operation"],
    )
    op.create_index(
        "ix_hotel_provider_budget_provider_operation",
        "hotel_provider_budget",
        ["provider", "operation"],
    )
    op.create_index(
        "ix_hotel_provider_budget_window_expires_at",
        "hotel_provider_budget",
        ["window_expires_at"],
    )
    op.create_table(
        "hotel_provider_budget_reservation",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("budget_id", sa.String(length=36), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="reserved"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["budget_id"], ["hotel_provider_budget.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_hotel_provider_budget_reservation_budget",
        "hotel_provider_budget_reservation",
        ["budget_id"],
    )
    op.create_index(
        "ix_hotel_provider_budget_reservation_status",
        "hotel_provider_budget_reservation",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_hotel_provider_budget_reservation_status", table_name="hotel_provider_budget_reservation")
    op.drop_index("ix_hotel_provider_budget_reservation_budget", table_name="hotel_provider_budget_reservation")
    op.drop_table("hotel_provider_budget_reservation")
    op.drop_index("ix_hotel_provider_budget_window_expires_at", table_name="hotel_provider_budget")
    op.drop_index("ix_hotel_provider_budget_provider_operation", table_name="hotel_provider_budget")
    op.drop_index("ix_hotel_provider_budget_operation", table_name="hotel_provider_budget")
    op.drop_index("ix_hotel_provider_budget_provider", table_name="hotel_provider_budget")
    op.drop_table("hotel_provider_budget")
