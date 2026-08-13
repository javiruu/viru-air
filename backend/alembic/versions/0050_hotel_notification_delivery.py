"""add hotel notification delivery ledger

Revision ID: 0050_hotel_notification_delivery
Revises: 0049_hotel_provider_run_client_event
Create Date: 2026-08-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0050_hotel_notification_delivery"
down_revision: Union[str, None] = "0049_hotel_provider_run_client_event"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hotel_notification_delivery",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_event_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("template_version", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_event_id"], ["hotel_alert_event.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_hotel_notification_delivery_idempotency"),
    )
    op.create_index("ix_hotel_notification_delivery_queue", "hotel_notification_delivery", ["status", "next_attempt_at", "created_at"], unique=False)
    op.create_index("ix_hotel_notification_delivery_recipient", "hotel_notification_delivery", ["recipient_user_id", "created_at"], unique=False)
    op.create_index("ix_hotel_notification_delivery_source", "hotel_notification_delivery", ["source_event_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_hotel_notification_delivery_source", table_name="hotel_notification_delivery")
    op.drop_index("ix_hotel_notification_delivery_recipient", table_name="hotel_notification_delivery")
    op.drop_index("ix_hotel_notification_delivery_queue", table_name="hotel_notification_delivery")
    op.drop_table("hotel_notification_delivery")
