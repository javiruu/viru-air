"""add revalidation job table

Revision ID: 8c1b0d7e2a43
Revises: 7b8f4c6a9d12
Create Date: 2026-06-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c1b0d7e2a43"
down_revision: Union[str, None] = "7b8f4c6a9d12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "revalidation_job" in _table_names(inspector):
        return

    op.create_table(
        "revalidation_job",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("lock_token", sa.String(length=64), nullable=True),
        sa.Column("lock_acquired_at", sa.DateTime(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_revalidation_job_due", "revalidation_job", ["status", "scheduled_at", "priority"], unique=False)
    op.create_index(
        "ix_revalidation_job_target",
        "revalidation_job",
        ["target_type", "target_fingerprint", "provider", "status"],
        unique=False,
    )
    op.create_index("ix_revalidation_job_lock_token", "revalidation_job", ["lock_token"], unique=False)
    op.create_index(op.f("ix_revalidation_job_job_type"), "revalidation_job", ["job_type"], unique=False)
    op.create_index(op.f("ix_revalidation_job_target_type"), "revalidation_job", ["target_type"], unique=False)
    op.create_index(
        op.f("ix_revalidation_job_target_fingerprint"),
        "revalidation_job",
        ["target_fingerprint"],
        unique=False,
    )
    op.create_index(op.f("ix_revalidation_job_status"), "revalidation_job", ["status"], unique=False)
    op.create_index(op.f("ix_revalidation_job_scheduled_at"), "revalidation_job", ["scheduled_at"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "revalidation_job" not in _table_names(inspector):
        return

    indexes = _index_names(inspector, "revalidation_job")
    for index_name in (
        "ix_revalidation_job_due",
        "ix_revalidation_job_target",
        "ix_revalidation_job_lock_token",
        op.f("ix_revalidation_job_job_type"),
        op.f("ix_revalidation_job_target_type"),
        op.f("ix_revalidation_job_target_fingerprint"),
        op.f("ix_revalidation_job_status"),
        op.f("ix_revalidation_job_scheduled_at"),
    ):
        if index_name in indexes:
            op.drop_index(index_name, table_name="revalidation_job")

    op.drop_table("revalidation_job")
