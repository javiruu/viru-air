"""add is_saved and label to door_to_door_search_history for Fase 8 saved plans

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "door_to_door_search_history" not in _table_names(inspector):
        return

    column_names = _column_names(inspector, "door_to_door_search_history")
    with op.batch_alter_table("door_to_door_search_history") as batch_op:
        if "is_saved" not in column_names:
            batch_op.add_column(
                sa.Column("is_saved", sa.Boolean(), nullable=False, server_default=sa.text("0"))
            )
        if "label" not in column_names:
            batch_op.add_column(
                sa.Column("label", sa.String(length=120), nullable=True)
            )

    inspector = sa.inspect(op.get_bind())
    indexes = _index_names(inspector, "door_to_door_search_history")
    if "ix_door_to_door_search_history_is_saved" not in indexes:
        op.create_index(
            "ix_door_to_door_search_history_is_saved",
            "door_to_door_search_history",
            ["is_saved"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "door_to_door_search_history" not in _table_names(inspector):
        return

    indexes = _index_names(inspector, "door_to_door_search_history")
    if "ix_door_to_door_search_history_is_saved" in indexes:
        op.drop_index("ix_door_to_door_search_history_is_saved", table_name="door_to_door_search_history")

    column_names = _column_names(inspector, "door_to_door_search_history")
    with op.batch_alter_table("door_to_door_search_history") as batch_op:
        if "label" in column_names:
            batch_op.drop_column("label")
        if "is_saved" in column_names:
            batch_op.drop_column("is_saved")
