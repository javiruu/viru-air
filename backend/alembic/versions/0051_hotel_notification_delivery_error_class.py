"""add hotel delivery error classification

Revision ID: 0051_hotel_notification_delivery_error_class
Revises: 0050_hotel_notification_delivery
Create Date: 2026-08-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0051_hotel_notification_delivery_error_class"
down_revision: Union[str, None] = "0050_hotel_notification_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hotel_notification_delivery",
        sa.Column("error_class", sa.String(length=24), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hotel_notification_delivery", "error_class")
