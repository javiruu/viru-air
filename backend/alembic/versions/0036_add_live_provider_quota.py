"""add persistent live provider quota ledger

Revision ID: 0036_add_live_provider_quota
Revises: 0035_add_live_flight_tracking
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0036_add_live_provider_quota"
down_revision: str | None = "0035_add_live_flight_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    inspector = _inspector()
    if "flight_provider_quota" not in inspector.get_table_names():
        op.create_table(
            "flight_provider_quota",
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("window_key", sa.String(length=10), nullable=False),
            sa.Column("units_used", sa.Integer(), nullable=False),
            sa.Column("blocked_until", sa.DateTime(), nullable=True),
            sa.Column("block_reason", sa.String(length=32), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("provider"),
        )
    else:
        existing = {column["name"] for column in inspector.get_columns("flight_provider_quota")}
        required = {
            "provider",
            "window_key",
            "units_used",
            "blocked_until",
            "block_reason",
            "updated_at",
        }
        missing = required - existing
        if missing:
            formatted = ", ".join(sorted(missing))
            raise RuntimeError(
                f"Cannot reconcile flight_provider_quota; missing columns: {formatted}"
            )
    index_names = {index["name"] for index in _inspector().get_indexes("flight_provider_quota")}
    if "ix_flight_provider_quota_blocked_until" not in index_names:
        op.create_index(
            "ix_flight_provider_quota_blocked_until",
            "flight_provider_quota",
            ["blocked_until"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        "ix_flight_provider_quota_blocked_until",
        table_name="flight_provider_quota",
    )
    op.drop_table("flight_provider_quota")
