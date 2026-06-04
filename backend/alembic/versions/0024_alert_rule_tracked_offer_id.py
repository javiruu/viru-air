"""add tracked_offer_id to hotel_alert_rule

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hotel_alert_rule") as batch_op:
        batch_op.add_column(
            sa.Column("tracked_offer_id", sa.String(36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_hotel_alert_rule_tracked_offer",
            "hotel_tracked_offer",
            ["tracked_offer_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_hotel_alert_rule_tracked_offer_id",
            ["tracked_offer_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("hotel_alert_rule") as batch_op:
        batch_op.drop_index("ix_hotel_alert_rule_tracked_offer_id")
        batch_op.drop_constraint("fk_hotel_alert_rule_tracked_offer", type_="foreignkey")
        batch_op.drop_column("tracked_offer_id")
