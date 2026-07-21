"""reconcile live snapshot uniqueness after legacy ORM bootstrap

Revision ID: 0037_reconcile_live_snapshot_uniqueness
Revises: 0036_add_live_provider_quota
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0037_reconcile_live_snapshot_uniqueness"
down_revision: str | None = "0036_add_live_provider_quota"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    expected = {"flight_instance_fingerprint", "provider", "observed_at"}
    existing = inspector.get_unique_constraints("flight_operational_snapshot")
    if any(set(constraint["column_names"]) == expected for constraint in existing):
        return
    with op.batch_alter_table("flight_operational_snapshot") as batch_op:
        batch_op.create_unique_constraint(
            "uq_flight_operational_snapshot_observation",
            ["flight_instance_fingerprint", "provider", "observed_at"],
        )


def downgrade() -> None:
    pass
