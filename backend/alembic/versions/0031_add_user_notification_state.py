"""add user notification state

Revision ID: 0031_add_user_notification_state
Revises: 8c1b0d7e2a43
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0031_add_user_notification_state"
down_revision = "8c1b0d7e2a43"
branch_labels = None
depends_on = None


def _table_names(conn) -> set[str]:
    inspector = sa.inspect(conn)
    return set(inspector.get_table_names())


def upgrade() -> None:
    conn = op.get_bind()
    if "user_notification_state" in _table_names(conn):
        return

    op.create_table(
        "user_notification_state",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "source_type",
            "source_id",
            name="uq_user_notification_state_source",
        ),
    )
    op.create_index("ix_user_notification_state_user_id", "user_notification_state", ["user_id"])
    op.create_index("ix_user_notification_state_source_id", "user_notification_state", ["source_id"])
    op.create_index(
        "ix_user_notification_state_user_read",
        "user_notification_state",
        ["user_id", "read_at"],
    )


def downgrade() -> None:
    conn = op.get_bind()
    if "user_notification_state" not in _table_names(conn):
        return

    op.drop_index("ix_user_notification_state_user_read", table_name="user_notification_state")
    op.drop_index("ix_user_notification_state_source_id", table_name="user_notification_state")
    op.drop_index("ix_user_notification_state_user_id", table_name="user_notification_state")
    op.drop_table("user_notification_state")
