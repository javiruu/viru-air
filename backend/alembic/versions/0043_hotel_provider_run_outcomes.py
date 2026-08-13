"""persist tracked-offer provider outcomes on hotel runs

Revision ID: 0043_hotel_provider_run_outcomes
Revises: 0042_hotel_alert_event_ownership
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0043_hotel_provider_run_outcomes"
down_revision: Union[str, None] = "0042_hotel_alert_event_ownership"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hotel_provider_run") as batch_op:
        batch_op.add_column(sa.Column("tracked_outcomes", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("hotel_provider_run") as batch_op:
        batch_op.drop_column("tracked_outcomes")
