"""add hotel sweep stay-query leases

Revision ID: 0045_hotel_sweep_lease
Revises: 0044_hotel_provider_budget
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0045_hotel_sweep_lease"
down_revision: Union[str, None] = "0044_hotel_provider_budget"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hotel_sweep_lease",
        sa.Column("fingerprint", sa.String(length=64), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("lock_token", sa.String(length=64), nullable=True),
        sa.Column("lock_acquired_at", sa.DateTime(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_provider_run_id", sa.String(length=36), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_hotel_sweep_lease_status_expires",
        "hotel_sweep_lease",
        ["status", "lease_expires_at"],
    )
    op.create_index("ix_hotel_sweep_lease_token", "hotel_sweep_lease", ["lock_token"], unique=True)
    op.create_index("ix_hotel_sweep_lease_last_provider_run_id", "hotel_sweep_lease", ["last_provider_run_id"])


def downgrade() -> None:
    op.drop_index("ix_hotel_sweep_lease_last_provider_run_id", table_name="hotel_sweep_lease")
    op.drop_index("ix_hotel_sweep_lease_token", table_name="hotel_sweep_lease")
    op.drop_index("ix_hotel_sweep_lease_status_expires", table_name="hotel_sweep_lease")
    op.drop_table("hotel_sweep_lease")
