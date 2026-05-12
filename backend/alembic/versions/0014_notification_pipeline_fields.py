"""add notification pipeline fields

Revision ID: 0014_notification_pipeline_fields
Revises: 0013_auth_tokens
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_notification_pipeline_fields"
down_revision = "0013_auth_tokens"
branch_labels = None
depends_on = None


def _column_names(conn, table_name: str) -> set[str]:
    inspector = sa.inspect(conn)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _table_names(conn) -> set[str]:
    inspector = sa.inspect(conn)
    return set(inspector.get_table_names())


def upgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)
    if "notification_event" not in tables:
        return
    columns = _column_names(conn, "notification_event")

    if "attempts" not in columns:
        op.add_column(
            "notification_event",
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        )
    if "next_attempt_at" not in columns:
        op.add_column(
            "notification_event",
            sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_notification_event_next_attempt_at", "notification_event", ["next_attempt_at"])
    if "last_error" not in columns:
        op.add_column(
            "notification_event",
            sa.Column("last_error", sa.String(length=500), nullable=True),
        )
    if "delivered_at" not in columns:
        op.add_column(
            "notification_event",
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_notification_event_delivered_at", "notification_event", ["delivered_at"])
    if "dedupe_key" not in columns:
        op.add_column(
            "notification_event",
            sa.Column("dedupe_key", sa.String(length=120), nullable=True),
        )
        op.create_index("ix_notification_event_dedupe_key", "notification_event", ["dedupe_key"])


def downgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)
    if "notification_event" not in tables:
        return
    columns = _column_names(conn, "notification_event")

    if "dedupe_key" in columns:
        op.drop_index("ix_notification_event_dedupe_key", table_name="notification_event")
        op.drop_column("notification_event", "dedupe_key")
    if "delivered_at" in columns:
        op.drop_index("ix_notification_event_delivered_at", table_name="notification_event")
        op.drop_column("notification_event", "delivered_at")
    if "last_error" in columns:
        op.drop_column("notification_event", "last_error")
    if "next_attempt_at" in columns:
        op.drop_index("ix_notification_event_next_attempt_at", table_name="notification_event")
        op.drop_column("notification_event", "next_attempt_at")
    if "attempts" in columns:
        op.drop_column("notification_event", "attempts")
