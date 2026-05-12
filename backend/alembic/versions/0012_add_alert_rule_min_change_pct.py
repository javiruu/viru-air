"""add min_change_pct to alert_rule

Revision ID: 0012_add_alert_rule_min_change_pct
Revises: 0011_search_pref_defaults
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_add_alert_rule_min_change_pct"
down_revision = "0011_search_pref_defaults"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    if not _has_column("alert_rule", "min_change_pct"):
        op.add_column("alert_rule", sa.Column("min_change_pct", sa.Numeric(5, 2), nullable=True))


def downgrade() -> None:
    if _has_column("alert_rule", "min_change_pct"):
        op.drop_column("alert_rule", "min_change_pct")
