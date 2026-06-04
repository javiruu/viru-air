"""add unique constraint on hotel_tracked_offer identity fields

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_hotel_tracked_offer_identity",
        "hotel_tracked_offer",
        ["user_id", "hotel_id", "check_in", "check_out", "guests", "provider"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_hotel_tracked_offer_identity", "hotel_tracked_offer", type_="unique")
