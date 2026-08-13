"""add normalized_city to hotel_property

Revision ID: 0019_hotels_normalized_city
Revises: 0018_hotels_provider_run_and_alert_event
Create Date: 2026-06-03
"""

import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = "0019_hotels_normalized_city"
down_revision: Union[str, None] = "0018_hotels_provider_run_and_alert_event"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(conn)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_names(conn, table_name: str) -> set[str]:
    inspector = sa.inspect(conn)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def _normalize_city(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.strip().lower()
    no_accents = unicodedata.normalize("NFKD", lowered).encode("ascii", errors="ignore").decode("ascii")
    no_punctuation = re.sub(r"[^\w\s]", " ", no_accents)
    return re.sub(r"\s+", " ", no_punctuation).strip()


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, "hotel_property", "normalized_city"):
        op.add_column(
            "hotel_property",
            sa.Column("normalized_city", sa.String(length=100), nullable=True),
        )

    hotel_property = sa.table(
        "hotel_property",
        sa.column("id", sa.String(length=36)),
        sa.column("city", sa.String(length=100)),
        sa.column("normalized_city", sa.String(length=100)),
    )

    rows = conn.execute(sa.select(hotel_property.c.id, hotel_property.c.city)).mappings().all()
    for row in rows:
        normalized_city = _normalize_city(row["city"])
        conn.execute(
            hotel_property.update()
            .where(hotel_property.c.id == row["id"])
            .values(normalized_city=normalized_city)
        )

    op.execute(
        sa.text(
            "UPDATE hotel_property SET normalized_city = '' WHERE normalized_city IS NULL"
        )
    )
    with op.batch_alter_table("hotel_property") as batch_op:
        batch_op.alter_column(
            "normalized_city",
            existing_type=sa.String(length=100),
            nullable=False,
        )

    indexes = _index_names(conn, "hotel_property")
    if "ix_hotel_property_normalized_city" not in indexes:
        op.create_index("ix_hotel_property_normalized_city", "hotel_property", ["normalized_city"])


def downgrade() -> None:
    conn = op.get_bind()
    indexes = _index_names(conn, "hotel_property")
    if "ix_hotel_property_normalized_city" in indexes:
        op.drop_index("ix_hotel_property_normalized_city", table_name="hotel_property")
    if _has_column(conn, "hotel_property", "normalized_city"):
        op.drop_column("hotel_property", "normalized_city")
