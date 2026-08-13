"""add client event context to hotel provider runs

Revision ID: 0049_hotel_provider_run_client_event
Revises: 0048_hotel_provider_run_context
Create Date: 2026-08-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0049_hotel_provider_run_client_event"
down_revision: Union[str, None] = "0048_hotel_provider_run_context"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hotel_provider_run",
        sa.Column("client_event_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_hotel_provider_run_client_event_id",
        "hotel_provider_run",
        ["client_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hotel_provider_run_client_event_id", table_name="hotel_provider_run")
    op.drop_column("hotel_provider_run", "client_event_id")
