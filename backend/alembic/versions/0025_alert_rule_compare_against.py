"""add compare_against field to hotel_alert_rule

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hotel_alert_rule") as batch_op:
        batch_op.add_column(
            sa.Column("compare_against", sa.String(20), nullable=False, server_default="snapshot_previous")
        )


def downgrade() -> None:
    with op.batch_alter_table("hotel_alert_rule") as batch_op:
        batch_op.drop_column("compare_against")
