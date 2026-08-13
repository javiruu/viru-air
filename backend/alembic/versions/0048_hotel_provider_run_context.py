"""add correlation and execution context to hotel provider runs

Revision ID: 0048_hotel_provider_run_context
Revises: 0047_hotel_provider_circuit_state_version
Create Date: 2026-08-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0048_hotel_provider_run_context"
down_revision: Union[str, None] = "0047_hotel_provider_circuit_state_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hotel_provider_run",
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "hotel_provider_run",
        sa.Column("execution_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_hotel_provider_run_correlation_id",
        "hotel_provider_run",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "ix_hotel_provider_run_execution_id",
        "hotel_provider_run",
        ["execution_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hotel_provider_run_execution_id", table_name="hotel_provider_run")
    op.drop_index("ix_hotel_provider_run_correlation_id", table_name="hotel_provider_run")
    op.drop_column("hotel_provider_run", "execution_id")
    op.drop_column("hotel_provider_run", "correlation_id")
