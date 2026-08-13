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


def _column_names() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("hotel_alert_event")}


def _index_names() -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("hotel_alert_event")}


def _has_user_foreign_key() -> bool:
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys("hotel_alert_event")
    return any(
        foreign_key["constrained_columns"] == ["user_id"] and foreign_key["referred_table"] == "users"
        for foreign_key in foreign_keys
    )


def upgrade() -> None:
    if "user_id" not in _column_names():
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

    has_user_foreign_key = _has_user_foreign_key()
    has_user_index = "ix_hotel_alert_event_user_id" in _index_names()
    if not has_user_foreign_key or not has_user_index:
        with op.batch_alter_table("hotel_alert_event") as batch_op:
            if not has_user_foreign_key:
                batch_op.create_foreign_key(
                    "fk_hotel_alert_event_user",
                    "users",
                    ["user_id"],
                    ["id"],
                )
            if not has_user_index:
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
