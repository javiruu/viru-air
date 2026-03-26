"""add user notes

Revision ID: 0003_add_user_notes
Revises: 0002_add_is_admin
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_user_notes"
down_revision = "0002_add_is_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_note",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_user_note_user_id", "user_note", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_note_user_id", table_name="user_note")
    op.drop_table("user_note")
