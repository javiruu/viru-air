"""add comparable fare profile to flight watch

Revision ID: 0038_add_fare_comparison_profile
Revises: 0037_reconcile_live_snapshot_uniqueness
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0038_add_fare_comparison_profile"
down_revision: str | None = "0037_reconcile_live_snapshot_uniqueness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("flight_watch") as batch_op:
        batch_op.add_column(sa.Column("fare_profile", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("flight_watch") as batch_op:
        batch_op.drop_column("fare_profile")
