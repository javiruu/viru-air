"""add quiet hours preferences and digest fields

Revision ID: 0015_alerts_quiet_hours_digest
Revises: 0014_notification_pipeline_fields
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_alerts_quiet_hours_digest"
down_revision = "0014_notification_pipeline_fields"
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

    if "notification_event" in tables:
        event_columns = _column_names(conn, "notification_event")
        if "group_key" not in event_columns:
            op.add_column("notification_event", sa.Column("group_key", sa.String(length=180), nullable=True))
            op.create_index("ix_notification_event_group_key", "notification_event", ["group_key"])
        if "group_reason" not in event_columns:
            op.add_column("notification_event", sa.Column("group_reason", sa.String(length=64), nullable=True))
        if "is_digest" not in event_columns:
            op.add_column(
                "notification_event",
                sa.Column("is_digest", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            )
        if "grouped_count" not in event_columns:
            op.add_column(
                "notification_event",
                sa.Column("grouped_count", sa.Integer(), nullable=False, server_default="1"),
            )

    if "user_preference" in tables:
        pref_columns = _column_names(conn, "user_preference")
        if "quiet_hours_enabled" not in pref_columns:
            op.add_column(
                "user_preference",
                sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            )
        if "quiet_hours_start" not in pref_columns:
            op.add_column("user_preference", sa.Column("quiet_hours_start", sa.String(length=5), nullable=True))
        if "quiet_hours_end" not in pref_columns:
            op.add_column("user_preference", sa.Column("quiet_hours_end", sa.String(length=5), nullable=True))
        if "quiet_hours_timezone" not in pref_columns:
            op.add_column("user_preference", sa.Column("quiet_hours_timezone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)

    if "user_preference" in tables:
        pref_columns = _column_names(conn, "user_preference")
        if "quiet_hours_timezone" in pref_columns:
            op.drop_column("user_preference", "quiet_hours_timezone")
        if "quiet_hours_end" in pref_columns:
            op.drop_column("user_preference", "quiet_hours_end")
        if "quiet_hours_start" in pref_columns:
            op.drop_column("user_preference", "quiet_hours_start")
        if "quiet_hours_enabled" in pref_columns:
            op.drop_column("user_preference", "quiet_hours_enabled")

    if "notification_event" in tables:
        event_columns = _column_names(conn, "notification_event")
        if "grouped_count" in event_columns:
            op.drop_column("notification_event", "grouped_count")
        if "is_digest" in event_columns:
            op.drop_column("notification_event", "is_digest")
        if "group_reason" in event_columns:
            op.drop_column("notification_event", "group_reason")
        if "group_key" in event_columns:
            op.drop_index("ix_notification_event_group_key", table_name="notification_event")
            op.drop_column("notification_event", "group_key")
