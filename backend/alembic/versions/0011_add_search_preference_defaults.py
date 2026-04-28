"""add search preference defaults

Revision ID: 0011_search_pref_defaults
Revises: 0010_client_error_event
Create Date: 2026-04-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_search_pref_defaults"
down_revision = "0010_client_error_event"
branch_labels = None
depends_on = None


def _column_names(conn, table_name: str) -> set[str]:
    insp = sa.inspect(conn)
    return {column["name"] for column in insp.get_columns(table_name)}


def upgrade() -> None:
    conn = op.get_bind()
    tables = set(sa.inspect(conn).get_table_names())
    if "user_preference" not in tables:
        return

    columns = _column_names(conn, "user_preference")

    if "include_nearby_origins_default" not in columns:
        op.add_column(
            "user_preference",
            sa.Column("include_nearby_origins_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "include_nearby_destinations_default" not in columns:
        op.add_column(
            "user_preference",
            sa.Column("include_nearby_destinations_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "depart_before_default" not in columns:
        op.add_column(
            "user_preference",
            sa.Column("depart_before_default", sa.String(length=5), nullable=True),
        )
    if "strict_filters_default" not in columns:
        op.add_column(
            "user_preference",
            sa.Column("strict_filters_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    conn = op.get_bind()
    tables = set(sa.inspect(conn).get_table_names())
    if "user_preference" not in tables:
        return

    columns = _column_names(conn, "user_preference")

    if "strict_filters_default" in columns:
        op.drop_column("user_preference", "strict_filters_default")
    if "depart_before_default" in columns:
        op.drop_column("user_preference", "depart_before_default")
    if "include_nearby_destinations_default" in columns:
        op.drop_column("user_preference", "include_nearby_destinations_default")
    if "include_nearby_origins_default" in columns:
        op.drop_column("user_preference", "include_nearby_origins_default")
