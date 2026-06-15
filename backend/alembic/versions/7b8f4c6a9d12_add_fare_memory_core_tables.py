"""add fare memory core tables

Revision ID: 7b8f4c6a9d12
Revises: 5f465bd665fa
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b8f4c6a9d12"
down_revision: Union[str, None] = "5f465bd665fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = _table_names(inspector)

    if "quick_search_cache_entry" in table_names:
        existing_columns = _column_names(inspector, "quick_search_cache_entry")
        with op.batch_alter_table("quick_search_cache_entry") as batch_op:
            if "search_fingerprint" not in existing_columns:
                batch_op.add_column(sa.Column("search_fingerprint", sa.String(length=64), nullable=True))
            if "canonical_request_json" not in existing_columns:
                batch_op.add_column(sa.Column("canonical_request_json", sa.Text(), nullable=True))
            if "provider_set_json" not in existing_columns:
                batch_op.add_column(sa.Column("provider_set_json", sa.Text(), nullable=True))
            if "freshness_status" not in existing_columns:
                batch_op.add_column(
                    sa.Column(
                        "freshness_status",
                        sa.String(length=32),
                        nullable=False,
                        server_default=sa.text("'fresh'"),
                    )
                )
            if "result_count" not in existing_columns:
                batch_op.add_column(
                    sa.Column("result_count", sa.Integer(), nullable=False, server_default=sa.text("0"))
                )
            if "confidence_score" not in existing_columns:
                batch_op.add_column(sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True))

        inspector = sa.inspect(op.get_bind())
        existing_indexes = _index_names(inspector, "quick_search_cache_entry")
        if "ix_quick_search_cache_entry_search_fingerprint" not in existing_indexes:
            op.create_index(
                op.f("ix_quick_search_cache_entry_search_fingerprint"),
                "quick_search_cache_entry",
                ["search_fingerprint"],
                unique=False,
            )
        if "ix_quick_search_cache_entry_freshness_status" not in existing_indexes:
            op.create_index(
                op.f("ix_quick_search_cache_entry_freshness_status"),
                "quick_search_cache_entry",
                ["freshness_status"],
                unique=False,
            )

    inspector = sa.inspect(op.get_bind())
    table_names = _table_names(inspector)

    if "flight_offer_cache_entry" not in table_names:
        op.create_table(
            "flight_offer_cache_entry",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("offer_fingerprint", sa.String(length=64), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("carrier", sa.String(length=16), nullable=True),
            sa.Column("flight_number", sa.String(length=32), nullable=True),
            sa.Column("origin_airport", sa.String(length=3), nullable=False),
            sa.Column("destination_airport", sa.String(length=3), nullable=False),
            sa.Column("departure_at", sa.DateTime(), nullable=False),
            sa.Column("arrival_at", sa.DateTime(), nullable=True),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("stops_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("booking_url_hash", sa.String(length=128), nullable=True),
            sa.Column("deeplink_signature", sa.String(length=128), nullable=True),
            sa.Column("source_kind", sa.String(length=24), nullable=False, server_default=sa.text("'provider'")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("offer_fingerprint", name="uq_flight_offer_cache_fingerprint"),
        )
        op.create_index(
            "ix_flight_offer_cache_route",
            "flight_offer_cache_entry",
            ["origin_airport", "destination_airport", "departure_at"],
            unique=False,
        )
        op.create_index(
            "ix_flight_offer_cache_provider",
            "flight_offer_cache_entry",
            ["provider", "departure_at"],
            unique=False,
        )
        op.create_index(
            op.f("ix_flight_offer_cache_entry_provider"),
            "flight_offer_cache_entry",
            ["provider"],
            unique=False,
        )
        op.create_index(
            op.f("ix_flight_offer_cache_entry_departure_at"),
            "flight_offer_cache_entry",
            ["departure_at"],
            unique=False,
        )

    if "flight_price_observation" not in table_names:
        op.create_table(
            "flight_price_observation",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("offer_id", sa.String(length=36), nullable=False),
            sa.Column("search_cache_entry_id", sa.String(length=36), nullable=True),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("price_amount", sa.Numeric(10, 2), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'EUR'")),
            sa.Column("fare_family", sa.String(length=64), nullable=True),
            sa.Column("baggage_included", sa.Boolean(), nullable=True),
            sa.Column("seats_left", sa.Integer(), nullable=True),
            sa.Column("observed_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column(
                "freshness_status",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'fresh'"),
            ),
            sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
            sa.Column(
                "validation_status",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'observed'"),
            ),
            sa.Column(
                "price_changed_since_last_seen",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("delta_abs", sa.Numeric(10, 2), nullable=True),
            sa.Column("delta_pct", sa.Numeric(8, 4), nullable=True),
            sa.ForeignKeyConstraint(["offer_id"], ["flight_offer_cache_entry.id"]),
            sa.ForeignKeyConstraint(["search_cache_entry_id"], ["quick_search_cache_entry.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_flight_price_observation_offer_observed",
            "flight_price_observation",
            ["offer_id", "observed_at"],
            unique=False,
        )
        op.create_index(
            "ix_flight_price_observation_expires",
            "flight_price_observation",
            ["expires_at"],
            unique=False,
        )
        op.create_index(
            "ix_flight_price_observation_freshness",
            "flight_price_observation",
            ["freshness_status"],
            unique=False,
        )
        op.create_index(
            op.f("ix_flight_price_observation_offer_id"),
            "flight_price_observation",
            ["offer_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_flight_price_observation_search_cache_entry_id"),
            "flight_price_observation",
            ["search_cache_entry_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_flight_price_observation_provider"),
            "flight_price_observation",
            ["provider"],
            unique=False,
        )
        op.create_index(
            op.f("ix_flight_price_observation_observed_at"),
            "flight_price_observation",
            ["observed_at"],
            unique=False,
        )

    if "quick_search_negative_cache_entry" not in table_names:
        op.create_table(
            "quick_search_negative_cache_entry",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("negative_fingerprint", sa.String(length=64), nullable=False),
            sa.Column("scope", sa.String(length=32), nullable=False),
            sa.Column("reason", sa.String(length=64), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=True),
            sa.Column("canonical_request_json", sa.Text(), nullable=False),
            sa.Column("observed_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column(
                "freshness_status",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'negative_fresh'"),
            ),
            sa.Column("retry_after_at", sa.DateTime(), nullable=True),
            sa.Column("hit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("negative_fingerprint", name="uq_qs_negative_cache_fingerprint"),
        )
        op.create_index(
            "ix_qs_negative_cache_expires",
            "quick_search_negative_cache_entry",
            ["expires_at"],
            unique=False,
        )
        op.create_index(
            "ix_qs_negative_cache_provider",
            "quick_search_negative_cache_entry",
            ["provider", "expires_at"],
            unique=False,
        )
        op.create_index(
            "ix_qs_negative_cache_freshness",
            "quick_search_negative_cache_entry",
            ["freshness_status"],
            unique=False,
        )
        op.create_index(
            op.f("ix_quick_search_negative_cache_entry_observed_at"),
            "quick_search_negative_cache_entry",
            ["observed_at"],
            unique=False,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = _table_names(inspector)

    if "quick_search_negative_cache_entry" in table_names:
        indexes = _index_names(inspector, "quick_search_negative_cache_entry")
        for index_name in (
            "ix_qs_negative_cache_expires",
            "ix_qs_negative_cache_provider",
            "ix_qs_negative_cache_freshness",
            op.f("ix_quick_search_negative_cache_entry_observed_at"),
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="quick_search_negative_cache_entry")
        op.drop_table("quick_search_negative_cache_entry")

    if "flight_price_observation" in table_names:
        indexes = _index_names(inspector, "flight_price_observation")
        for index_name in (
            "ix_flight_price_observation_offer_observed",
            "ix_flight_price_observation_expires",
            "ix_flight_price_observation_freshness",
            op.f("ix_flight_price_observation_offer_id"),
            op.f("ix_flight_price_observation_search_cache_entry_id"),
            op.f("ix_flight_price_observation_provider"),
            op.f("ix_flight_price_observation_observed_at"),
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="flight_price_observation")
        op.drop_table("flight_price_observation")

    if "flight_offer_cache_entry" in table_names:
        indexes = _index_names(inspector, "flight_offer_cache_entry")
        for index_name in (
            "ix_flight_offer_cache_route",
            "ix_flight_offer_cache_provider",
            op.f("ix_flight_offer_cache_entry_provider"),
            op.f("ix_flight_offer_cache_entry_departure_at"),
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="flight_offer_cache_entry")
        op.drop_table("flight_offer_cache_entry")

    if "quick_search_cache_entry" in table_names:
        indexes = _index_names(inspector, "quick_search_cache_entry")
        for index_name in (
            op.f("ix_quick_search_cache_entry_search_fingerprint"),
            op.f("ix_quick_search_cache_entry_freshness_status"),
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="quick_search_cache_entry")

        existing_columns = _column_names(sa.inspect(op.get_bind()), "quick_search_cache_entry")
        removable_columns = [
            column_name
            for column_name in (
                "search_fingerprint",
                "canonical_request_json",
                "provider_set_json",
                "freshness_status",
                "result_count",
                "confidence_score",
            )
            if column_name in existing_columns
        ]
        if removable_columns:
            with op.batch_alter_table("quick_search_cache_entry") as batch_op:
                for column_name in removable_columns:
                    batch_op.drop_column(column_name)
