"""add refresh and password reset token tables

Revision ID: 0013_auth_tokens
Revises: 0012_add_alert_rule_min_change_pct
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_auth_tokens"
down_revision = "0012_add_alert_rule_min_change_pct"
branch_labels = None
depends_on = None


def _table_names(conn) -> set[str]:
    return set(sa.inspect(conn).get_table_names())


def upgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)

    if "refresh_token" not in tables:
        op.create_table(
            "refresh_token",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("replaced_by_token_id", sa.String(length=36), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("ip_hash", sa.String(length=64), nullable=True),
            sa.ForeignKeyConstraint(["replaced_by_token_id"], ["refresh_token.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_refresh_token_user_id", "refresh_token", ["user_id"])
        op.create_index("ix_refresh_token_token_hash", "refresh_token", ["token_hash"])
        op.create_index("ix_refresh_token_expires_at", "refresh_token", ["expires_at"])
        op.create_index("ix_refresh_token_revoked_at", "refresh_token", ["revoked_at"])

    if "password_reset_token" not in tables:
        op.create_table(
            "password_reset_token",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_password_reset_token_user_id", "password_reset_token", ["user_id"])
        op.create_index("ix_password_reset_token_token_hash", "password_reset_token", ["token_hash"])
        op.create_index("ix_password_reset_token_expires_at", "password_reset_token", ["expires_at"])
        op.create_index("ix_password_reset_token_used_at", "password_reset_token", ["used_at"])


def downgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)

    if "password_reset_token" in tables:
        op.drop_index("ix_password_reset_token_used_at", table_name="password_reset_token")
        op.drop_index("ix_password_reset_token_expires_at", table_name="password_reset_token")
        op.drop_index("ix_password_reset_token_token_hash", table_name="password_reset_token")
        op.drop_index("ix_password_reset_token_user_id", table_name="password_reset_token")
        op.drop_table("password_reset_token")

    if "refresh_token" in tables:
        op.drop_index("ix_refresh_token_revoked_at", table_name="refresh_token")
        op.drop_index("ix_refresh_token_expires_at", table_name="refresh_token")
        op.drop_index("ix_refresh_token_token_hash", table_name="refresh_token")
        op.drop_index("ix_refresh_token_user_id", table_name="refresh_token")
        op.drop_table("refresh_token")
