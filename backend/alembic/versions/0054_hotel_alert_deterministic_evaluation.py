"""add deterministic hotel alert evaluation metadata

Revision ID: 0054_hotel_alert_deterministic_evaluation
Revises: 0053_hotel_provider_latency_aggregate
Create Date: 2026-08-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0054_hotel_alert_deterministic_evaluation"
down_revision: Union[str, None] = "0053_hotel_provider_latency_aggregate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hotel_alert_rule") as batch_op:
        batch_op.add_column(sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="60"))
        batch_op.add_column(sa.Column("evaluation_state", sa.String(length=16), nullable=False, server_default="clear"))
        batch_op.add_column(sa.Column("last_fired_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_event_fingerprint", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_hotel_alert_rule_last_event_fingerprint", ["last_event_fingerprint"], unique=False)

    with op.batch_alter_table("hotel_alert_event") as batch_op:
        batch_op.add_column(sa.Column("event_fingerprint", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("snapshot_before_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("snapshot_after_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("baseline_snapshot_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("comparability_key", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("reason_code", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("eligibility_status", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("rule_version", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("cooldown_until", sa.DateTime(), nullable=True))
        batch_op.create_index("uq_hotel_alert_event_fingerprint", ["event_fingerprint"], unique=True)
        batch_op.create_index("ix_hotel_alert_event_rule_created", ["rule_id", "created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("hotel_alert_event") as batch_op:
        batch_op.drop_index("ix_hotel_alert_event_rule_created")
        batch_op.drop_index("uq_hotel_alert_event_fingerprint")
        batch_op.drop_column("cooldown_until")
        batch_op.drop_column("rule_version")
        batch_op.drop_column("eligibility_status")
        batch_op.drop_column("reason_code")
        batch_op.drop_column("comparability_key")
        batch_op.drop_column("baseline_snapshot_id")
        batch_op.drop_column("snapshot_after_id")
        batch_op.drop_column("snapshot_before_id")
        batch_op.drop_column("event_fingerprint")

    with op.batch_alter_table("hotel_alert_rule") as batch_op:
        batch_op.drop_index("ix_hotel_alert_rule_last_event_fingerprint")
        batch_op.drop_column("last_event_fingerprint")
        batch_op.drop_column("last_fired_at")
        batch_op.drop_column("evaluation_state")
        batch_op.drop_column("cooldown_minutes")
