"""add hotel_provider_run and hotel_alert_event

Revision ID: 0018_hotels_provider_run_and_alert_event
Revises: 0017_hotels_domain_skeleton
Create Date: 2026-06-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018_hotels_provider_run_and_alert_event"
down_revision: Union[str, None] = "0017_hotels_domain_skeleton"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, table_name: str) -> bool:
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def _index_names(conn, table_name: str) -> set[str]:
    inspector = sa.inspect(conn)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "hotel_provider_run"):
        op.create_table(
            "hotel_provider_run",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
            sa.Column("items_processed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.String(length=500), nullable=True),
        )

    indexes = _index_names(conn, "hotel_provider_run")
    if "ix_hotel_provider_run_provider" not in indexes:
        op.create_index("ix_hotel_provider_run_provider", "hotel_provider_run", ["provider"])

    if not _has_table(conn, "hotel_alert_event"):
        op.create_table(
            "hotel_alert_event",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "rule_id",
                sa.String(length=36),
                sa.ForeignKey("hotel_alert_rule.id"),
                nullable=False,
            ),
            sa.Column(
                "hotel_id",
                sa.String(length=36),
                sa.ForeignKey("hotel_property.id"),
                nullable=False,
            ),
            sa.Column(
                "provider_run_id",
                sa.String(length=36),
                sa.ForeignKey("hotel_provider_run.id"),
                nullable=True,
            ),
            sa.Column("event_type", sa.String(length=30), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("trigger_value", sa.Numeric(10, 2), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    indexes = _index_names(conn, "hotel_alert_event")
    if "ix_hotel_alert_event_rule_id" not in indexes:
        op.create_index("ix_hotel_alert_event_rule_id", "hotel_alert_event", ["rule_id"])
    if "ix_hotel_alert_event_hotel_id" not in indexes:
        op.create_index("ix_hotel_alert_event_hotel_id", "hotel_alert_event", ["hotel_id"])
    if "ix_hotel_alert_event_provider_run_id" not in indexes:
        op.create_index("ix_hotel_alert_event_provider_run_id", "hotel_alert_event", ["provider_run_id"])
    if "ix_hotel_alert_event_created_at" not in indexes:
        op.create_index("ix_hotel_alert_event_created_at", "hotel_alert_event", ["created_at"])


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "hotel_alert_event"):
        indexes = _index_names(conn, "hotel_alert_event")
        if "ix_hotel_alert_event_created_at" in indexes:
            op.drop_index("ix_hotel_alert_event_created_at", table_name="hotel_alert_event")
        if "ix_hotel_alert_event_provider_run_id" in indexes:
            op.drop_index("ix_hotel_alert_event_provider_run_id", table_name="hotel_alert_event")
        if "ix_hotel_alert_event_hotel_id" in indexes:
            op.drop_index("ix_hotel_alert_event_hotel_id", table_name="hotel_alert_event")
        if "ix_hotel_alert_event_rule_id" in indexes:
            op.drop_index("ix_hotel_alert_event_rule_id", table_name="hotel_alert_event")
        op.drop_table("hotel_alert_event")

    if _has_table(conn, "hotel_provider_run"):
        indexes = _index_names(conn, "hotel_provider_run")
        if "ix_hotel_provider_run_provider" in indexes:
            op.drop_index("ix_hotel_provider_run_provider", table_name="hotel_provider_run")
        op.drop_table("hotel_provider_run")
