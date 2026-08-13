"""add hotel alert baseline metadata

Revision ID: 0055_hotel_alert_baseline_metadata
Revises: 0054_hotel_alert_deterministic_evaluation
Create Date: 2026-08-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0055_hotel_alert_baseline_metadata"
down_revision: Union[str, None] = "0054_hotel_alert_deterministic_evaluation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hotel_alert_event") as batch_op:
        batch_op.add_column(sa.Column("baseline_source", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("baseline_amount", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("baseline_currency", sa.String(length=3), nullable=True))
        batch_op.add_column(sa.Column("evaluation_state", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("hotel_alert_event") as batch_op:
        batch_op.drop_column("evaluation_state")
        batch_op.drop_column("baseline_currency")
        batch_op.drop_column("baseline_amount")
        batch_op.drop_column("baseline_source")
