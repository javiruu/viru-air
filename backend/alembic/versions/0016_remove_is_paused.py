"""remove is_paused column from flight_watch

Revision ID: 0016_remove_is_paused
Revises: 0015_alerts_quiet_hours_digest
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_remove_is_paused"
down_revision = "0015_alerts_quiet_hours_digest"
branch_labels = None
depends_on = None


def _column_names(conn, table_name: str) -> set[str]:
    inspector = sa.inspect(conn)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(conn, table_name: str) -> set[str]:
    insp = sa.inspect(conn)
    return {idx["name"] for idx in insp.get_indexes(table_name)}


def upgrade() -> None:
    conn = op.get_bind()
    columns = _column_names(conn, "flight_watch")
    indexes = _index_names(conn, "flight_watch")

    # Drop the composite index that references is_paused before dropping the column
    if "ix_flight_watch_user_status_paused_created" in indexes:
        op.drop_index("ix_flight_watch_user_status_paused_created", table_name="flight_watch")

    if "is_paused" in columns:
        op.drop_column("flight_watch", "is_paused")


def downgrade() -> None:
    conn = op.get_bind()
    columns = _column_names(conn, "flight_watch")
    indexes = _index_names(conn, "flight_watch")

    if "is_paused" not in columns:
        op.add_column(
            "flight_watch",
            sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    # Restore the composite index
    if "ix_flight_watch_user_status_paused_created" not in indexes:
        op.create_index(
            "ix_flight_watch_user_status_paused_created",
            "flight_watch",
            ["user_id", "status", "is_paused", "created_at"],
        )
