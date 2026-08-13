"""add explicit ownership to hotel alert events

Revision ID: 0042
Revises: 0041_add_community_trending_snapshots
Create Date: 2026-08-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0042_hotel_alert_event_ownership"
down_revision: Union[str, None] = "0041_add_community_trending_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hotel_alert_event") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
    op.execute(
        sa.text(
            "UPDATE hotel_alert_event "
            "SET user_id = (SELECT user_id FROM hotel_alert_rule "
            "WHERE hotel_alert_rule.id = hotel_alert_event.rule_id) "
            "WHERE user_id IS NULL AND rule_id IS NOT NULL"
        )
    )
    with op.batch_alter_table("hotel_alert_event") as batch_op:
        batch_op.create_foreign_key(
            "fk_hotel_alert_event_user",
            "users",
            ["user_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_hotel_alert_event_user_id",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("hotel_alert_event") as batch_op:
        batch_op.drop_index("ix_hotel_alert_event_user_id")
        batch_op.drop_constraint("fk_hotel_alert_event_user", type_="foreignkey")
        batch_op.drop_column("user_id")
