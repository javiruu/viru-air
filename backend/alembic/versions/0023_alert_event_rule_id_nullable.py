"""make hotel_alert_event.rule_id nullable for sweep-generated events

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hotel_alert_event") as batch_op:
        batch_op.alter_column("rule_id", existing_type=sa.String(36), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("hotel_alert_event") as batch_op:
        batch_op.alter_column("rule_id", existing_type=sa.String(36), nullable=False)
