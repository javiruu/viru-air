"""add unique constraint on hotel_tracked_offer identity fields

Revision ID: 0022
Revises: 0021_snapshot_tracking_fields
Create Date: 2026-06-04
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0022"
down_revision: Union[str, None] = "0021_snapshot_tracking_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hotel_tracked_offer") as batch_op:
        batch_op.create_unique_constraint(
            "uq_hotel_tracked_offer_identity",
            ["user_id", "hotel_id", "check_in", "check_out", "guests", "provider"],
        )


def downgrade() -> None:
    with op.batch_alter_table("hotel_tracked_offer") as batch_op:
        batch_op.drop_constraint("uq_hotel_tracked_offer_identity", type_="unique")
