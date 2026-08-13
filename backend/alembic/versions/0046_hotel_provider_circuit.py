"""add persistent hotel provider circuit breaker

Revision ID: 0046_hotel_provider_circuit
Revises: 0045_hotel_sweep_lease
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0046_hotel_provider_circuit"
down_revision: Union[str, None] = "0045_hotel_sweep_lease"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hotel_provider_circuit",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="closed"),
        sa.Column("failure_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("next_probe_at", sa.DateTime(), nullable=True),
        sa.Column("probe_token", sa.String(length=64), nullable=True),
        sa.Column("probe_expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "provider",
            "operation",
            name="uq_hotel_provider_circuit_provider_operation",
        ),
    )
    op.create_index(
        "ix_hotel_provider_circuit_provider",
        "hotel_provider_circuit",
        ["provider"],
    )
    op.create_index(
        "ix_hotel_provider_circuit_status_probe",
        "hotel_provider_circuit",
        ["status", "next_probe_at"],
    )
    op.create_index(
        "ix_hotel_provider_circuit_next_probe_at",
        "hotel_provider_circuit",
        ["next_probe_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_hotel_provider_circuit_next_probe_at", table_name="hotel_provider_circuit")
    op.drop_index("ix_hotel_provider_circuit_status_probe", table_name="hotel_provider_circuit")
    op.drop_index("ix_hotel_provider_circuit_provider", table_name="hotel_provider_circuit")
    op.drop_table("hotel_provider_circuit")
