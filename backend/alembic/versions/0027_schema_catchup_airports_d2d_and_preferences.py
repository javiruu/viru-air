"""schema catchup for airports, door-to-door tables, and preference defaults

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _create_airport_table(inspector: sa.Inspector) -> None:
    if "airport" not in _table_names(inspector):
        op.create_table(
            "airport",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("iata", sa.String(length=3), nullable=False),
            sa.Column("icao", sa.String(length=4), nullable=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("city", sa.String(length=100), nullable=False),
            sa.Column("country", sa.String(length=100), nullable=False),
            sa.Column("region", sa.String(length=50), nullable=True),
            sa.Column("latitude", sa.Numeric(10, 6), nullable=False),
            sa.Column("longitude", sa.Numeric(10, 6), nullable=False),
            sa.Column("timezone", sa.String(length=64), nullable=True),
            sa.Column("airport_type", sa.String(length=50), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False),
            sa.Column("source", sa.String(length=50), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(op.get_bind())

    indexes = _index_names(inspector, "airport")
    if "ix_airport_iata" not in indexes:
        op.create_index("ix_airport_iata", "airport", ["iata"], unique=True)
    if "ix_airport_icao" not in indexes:
        op.create_index("ix_airport_icao", "airport", ["icao"], unique=False)


def _create_door_to_door_saved_location(inspector: sa.Inspector) -> None:
    if "door_to_door_saved_location" not in _table_names(inspector):
        op.create_table(
            "door_to_door_saved_location",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("location_type", sa.String(length=32), nullable=False),
            sa.Column("label", sa.String(length=180), nullable=False),
            sa.Column("lat", sa.Numeric(10, 6), nullable=True),
            sa.Column("lng", sa.Numeric(10, 6), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(op.get_bind())

    indexes = _index_names(inspector, "door_to_door_saved_location")
    if "ix_door_to_door_saved_location_user_id" not in indexes:
        op.create_index(
            "ix_door_to_door_saved_location_user_id",
            "door_to_door_saved_location",
            ["user_id"],
            unique=True,
        )


def _create_door_to_door_search_history(inspector: sa.Inspector) -> None:
    if "door_to_door_search_history" not in _table_names(inspector):
        op.create_table(
            "door_to_door_search_history",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("watch_id", sa.String(length=36), nullable=False),
            sa.Column("origin_json", sa.Text(), nullable=False),
            sa.Column("final_destination_json", sa.Text(), nullable=False),
            sa.Column("preferences_json", sa.Text(), nullable=False),
            sa.Column("summary_json", sa.Text(), nullable=False),
            sa.Column("warnings_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["watch_id"], ["flight_watch.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(op.get_bind())

    indexes = _index_names(inspector, "door_to_door_search_history")
    if "ix_door_to_door_search_history_created_at" not in indexes:
        op.create_index("ix_door_to_door_search_history_created_at", "door_to_door_search_history", ["created_at"])
    if "ix_door_to_door_search_history_user_id" not in indexes:
        op.create_index("ix_door_to_door_search_history_user_id", "door_to_door_search_history", ["user_id"])
    if "ix_door_to_door_search_history_watch_id" not in indexes:
        op.create_index("ix_door_to_door_search_history_watch_id", "door_to_door_search_history", ["watch_id"])


def _create_door_to_door_chosen_option(inspector: sa.Inspector) -> None:
    if "door_to_door_chosen_option" not in _table_names(inspector):
        op.create_table(
            "door_to_door_chosen_option",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("watch_id", sa.String(length=36), nullable=False),
            sa.Column("history_id", sa.String(length=36), nullable=True),
            sa.Column("option_id", sa.String(length=80), nullable=False),
            sa.Column("option_label", sa.String(length=120), nullable=False),
            sa.Column("option_summary_json", sa.Text(), nullable=False),
            sa.Column("chosen_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["history_id"], ["door_to_door_search_history.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["watch_id"], ["flight_watch.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(op.get_bind())

    indexes = _index_names(inspector, "door_to_door_chosen_option")
    if "ix_door_to_door_chosen_option_chosen_at" not in indexes:
        op.create_index("ix_door_to_door_chosen_option_chosen_at", "door_to_door_chosen_option", ["chosen_at"])
    if "ix_door_to_door_chosen_option_user_id" not in indexes:
        op.create_index("ix_door_to_door_chosen_option_user_id", "door_to_door_chosen_option", ["user_id"])
    if "ix_door_to_door_chosen_option_watch_id" not in indexes:
        op.create_index("ix_door_to_door_chosen_option_watch_id", "door_to_door_chosen_option", ["watch_id"])


def _add_missing_user_preference_columns(inspector: sa.Inspector) -> None:
    if "user_preference" not in _table_names(inspector):
        return

    column_names = _column_names(inspector, "user_preference")
    with op.batch_alter_table("user_preference") as batch_op:
        if "country_price_hint_mode_default" not in column_names:
            batch_op.add_column(
                sa.Column("country_price_hint_mode_default", sa.String(length=16), nullable=False, server_default="min")
            )
        if "calendar_hint_bucket_mode_default" not in column_names:
            batch_op.add_column(
                sa.Column(
                    "calendar_hint_bucket_mode_default",
                    sa.String(length=24),
                    nullable=False,
                    server_default="monthly_terciles",
                )
            )
        if "calendar_hint_guideline_low_max_default" not in column_names:
            batch_op.add_column(
                sa.Column(
                    "calendar_hint_guideline_low_max_default",
                    sa.Numeric(10, 2),
                    nullable=False,
                    server_default="90.0",
                )
            )
        if "calendar_hint_guideline_mid_max_default" not in column_names:
            batch_op.add_column(
                sa.Column(
                    "calendar_hint_guideline_mid_max_default",
                    sa.Numeric(10, 2),
                    nullable=False,
                    server_default="150.0",
                )
            )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    _create_airport_table(inspector)
    inspector = sa.inspect(op.get_bind())
    _create_door_to_door_saved_location(inspector)
    inspector = sa.inspect(op.get_bind())
    _create_door_to_door_search_history(inspector)
    inspector = sa.inspect(op.get_bind())
    _create_door_to_door_chosen_option(inspector)
    inspector = sa.inspect(op.get_bind())
    _add_missing_user_preference_columns(inspector)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "user_preference" in _table_names(inspector):
        column_names = _column_names(inspector, "user_preference")
        with op.batch_alter_table("user_preference") as batch_op:
            if "calendar_hint_guideline_mid_max_default" in column_names:
                batch_op.drop_column("calendar_hint_guideline_mid_max_default")
            if "calendar_hint_guideline_low_max_default" in column_names:
                batch_op.drop_column("calendar_hint_guideline_low_max_default")
            if "calendar_hint_bucket_mode_default" in column_names:
                batch_op.drop_column("calendar_hint_bucket_mode_default")
            if "country_price_hint_mode_default" in column_names:
                batch_op.drop_column("country_price_hint_mode_default")

    inspector = sa.inspect(op.get_bind())
    table_names = _table_names(inspector)
    if "door_to_door_chosen_option" in table_names:
        for index_name in (
            "ix_door_to_door_chosen_option_watch_id",
            "ix_door_to_door_chosen_option_user_id",
            "ix_door_to_door_chosen_option_chosen_at",
        ):
            if index_name in _index_names(inspector, "door_to_door_chosen_option"):
                op.drop_index(index_name, table_name="door_to_door_chosen_option")
        op.drop_table("door_to_door_chosen_option")

    inspector = sa.inspect(op.get_bind())
    table_names = _table_names(inspector)
    if "door_to_door_search_history" in table_names:
        for index_name in (
            "ix_door_to_door_search_history_watch_id",
            "ix_door_to_door_search_history_user_id",
            "ix_door_to_door_search_history_created_at",
        ):
            if index_name in _index_names(inspector, "door_to_door_search_history"):
                op.drop_index(index_name, table_name="door_to_door_search_history")
        op.drop_table("door_to_door_search_history")

    inspector = sa.inspect(op.get_bind())
    table_names = _table_names(inspector)
    if "door_to_door_saved_location" in table_names:
        if "ix_door_to_door_saved_location_user_id" in _index_names(inspector, "door_to_door_saved_location"):
            op.drop_index("ix_door_to_door_saved_location_user_id", table_name="door_to_door_saved_location")
        op.drop_table("door_to_door_saved_location")

    inspector = sa.inspect(op.get_bind())
    table_names = _table_names(inspector)
    if "airport" in table_names:
        for index_name in ("ix_airport_icao", "ix_airport_iata"):
            if index_name in _index_names(inspector, "airport"):
                op.drop_index(index_name, table_name="airport")
        op.drop_table("airport")
