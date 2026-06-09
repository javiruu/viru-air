"""add door_to_door_saved_place table for Fase 8

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _create_door_to_door_saved_place(inspector: sa.Inspector) -> None:
    if "door_to_door_saved_place" not in _table_names(inspector):
        op.create_table(
            "door_to_door_saved_place",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("label", sa.String(length=180), nullable=False),
            sa.Column("note", sa.String(length=280), nullable=False),
            sa.Column("watch_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["watch_id"], ["flight_watch.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(op.get_bind())

    indexes = _index_names(inspector, "door_to_door_saved_place")
    if "ix_door_to_door_saved_place_user_id" not in indexes:
        op.create_index("ix_door_to_door_saved_place_user_id", "door_to_door_saved_place", ["user_id"])


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    _create_door_to_door_saved_place(inspector)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "door_to_door_saved_place" in _table_names(inspector):
        if "ix_door_to_door_saved_place_user_id" in _index_names(inspector, "door_to_door_saved_place"):
            op.drop_index("ix_door_to_door_saved_place_user_id", table_name="door_to_door_saved_place")
        op.drop_table("door_to_door_saved_place")
