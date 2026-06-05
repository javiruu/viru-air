"""add group_id to flight_watch

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("flight_watch", sa.Column("group_id", sa.String(36), nullable=True))
    op.create_index(op.f("ix_flight_watch_group_id"), "flight_watch", ["group_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_flight_watch_group_id"), table_name="flight_watch")
    op.drop_column("flight_watch", "group_id")
