"""add anonymous community price reports

Revision ID: 0039_add_community_pricing
Revises: 0038_add_fare_comparison_profile
Create Date: 2026-07-28
"""

from collections.abc import Sequence
from typing import Final

import sqlalchemy as sa
from alembic import op


revision: str = "0039_add_community_pricing"
down_revision: str | None = "0038_add_fare_comparison_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME: Final = "community_price_report"
EXPECTED_COLUMNS: Final = {
    "id",
    "watch_id",
    "user_id",
    "trigger_reason",
    "flew",
    "price_per_traveler",
    "currency",
    "created_at",
    "updated_at",
}
EXPECTED_NULLABILITY: Final = {
    "id": False,
    "watch_id": False,
    "user_id": False,
    "trigger_reason": False,
    "flew": False,
    "price_per_traveler": True,
    "currency": False,
    "created_at": False,
    "updated_at": False,
}
USER_INDEX_NAME: Final = "ix_community_price_report_user"
CHECK_NAME: Final = "ck_community_price_report_flew_price"
EXPECTED_CHECK_SQL: Final = (
    "(flew=falseandprice_per_travelerisnull)"
    "or(flew=trueandprice_per_traveler>0)"
)


class IncompatibleCommunityPriceTableError(RuntimeError):
    pass


def _matches_expected_type(name: str, column_type: sa.types.TypeEngine) -> bool:
    if name in {"id", "watch_id", "user_id"}:
        return isinstance(column_type, sa.String) and column_type.length == 36
    if name == "trigger_reason":
        return isinstance(column_type, sa.String) and column_type.length == 20
    if name == "currency":
        return isinstance(column_type, sa.String) and column_type.length == 3
    if name == "flew":
        return isinstance(column_type, sa.Boolean)
    if name == "price_per_traveler":
        return (
            isinstance(column_type, sa.Numeric)
            and column_type.precision == 10
            and column_type.scale == 2
        )
    return isinstance(column_type, sa.DateTime)


def _normalize_check_sql(sqltext: object) -> str:
    normalized = "".join(str(sqltext).lower().split())
    normalized = normalized.replace("::numeric", "").replace("(0)", "0")
    for atom in (
        "flew=false",
        "price_per_travelerisnull",
        "flew=true",
        "price_per_traveler>0",
    ):
        normalized = normalized.replace(f"({atom})", atom)
    while normalized.startswith("(") and normalized.endswith(")"):
        depth = 0
        closes_at_end = True
        for position, character in enumerate(normalized):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and position != len(normalized) - 1:
                    closes_at_end = False
                    break
        if not closes_at_end:
            break
        normalized = normalized[1:-1]
    return normalized


def _validate_existing_table(inspector: sa.Inspector) -> None:
    columns = {
        column["name"]: column for column in inspector.get_columns(TABLE_NAME)
    }
    unique_columns = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
    }
    primary_key = tuple(
        inspector.get_pk_constraint(TABLE_NAME).get("constrained_columns") or ()
    )
    foreign_keys = {
        (
            tuple(constraint["constrained_columns"]),
            constraint["referred_table"],
            tuple(constraint["referred_columns"]),
            str(constraint.get("options", {}).get("ondelete", "")).upper(),
        )
        for constraint in inspector.get_foreign_keys(TABLE_NAME)
    }
    checks = {
        constraint["name"]: _normalize_check_sql(constraint["sqltext"])
        for constraint in inspector.get_check_constraints(TABLE_NAME)
    }
    check_sql = checks.get(CHECK_NAME, "")
    valid_columns = (
        set(columns) == EXPECTED_COLUMNS
        and all(
            bool(columns[name]["nullable"]) is nullable
            and columns[name].get("default") is None
            and _matches_expected_type(name, columns[name]["type"])
            for name, nullable in EXPECTED_NULLABILITY.items()
        )
    )
    valid_foreign_keys = foreign_keys == {
        (("watch_id",), "flight_watch", ("id",), "CASCADE"),
        (("user_id",), "users", ("id",), "CASCADE"),
    }
    valid_check = check_sql == EXPECTED_CHECK_SQL
    if not (
        valid_columns
        and primary_key == ("id",)
        and unique_columns == {("watch_id",)}
        and valid_foreign_keys
        and valid_check
    ):
        raise IncompatibleCommunityPriceTableError(
            "community_price_report exists but does not match revision 0039"
        )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABLE_NAME not in inspector.get_table_names():
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("watch_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("trigger_reason", sa.String(length=20), nullable=False),
            sa.Column("flew", sa.Boolean(), nullable=False),
            sa.Column("price_per_traveler", sa.Numeric(10, 2), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "(flew = false AND price_per_traveler IS NULL) "
                "OR (flew = true AND price_per_traveler > 0)",
                name="ck_community_price_report_flew_price",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["watch_id"], ["flight_watch.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("watch_id", name="uq_community_price_report_watch"),
        )
        inspector = sa.inspect(op.get_bind())
    else:
        _validate_existing_table(inspector)

    reflected_indexes = inspector.get_indexes(TABLE_NAME)
    unexpected_indexes = [
        index
        for index in reflected_indexes
        if index["name"] != USER_INDEX_NAME
        and index.get("duplicates_constraint")
        != "uq_community_price_report_watch"
    ]
    if unexpected_indexes:
        raise IncompatibleCommunityPriceTableError(
            "community_price_report has unexpected indexes"
        )
    indexes = {index["name"]: index for index in reflected_indexes}
    existing_user_index = indexes.get(USER_INDEX_NAME)
    if existing_user_index is not None and (
        tuple(existing_user_index["column_names"]) != ("user_id",)
        or bool(existing_user_index["unique"])
    ):
        raise IncompatibleCommunityPriceTableError(
            "community_price_report has an incompatible user index"
        )
    if existing_user_index is None:
        op.create_index(USER_INDEX_NAME, TABLE_NAME, ["user_id"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABLE_NAME not in inspector.get_table_names():
        return
    index_names = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
    if USER_INDEX_NAME in index_names:
        op.drop_index(USER_INDEX_NAME, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
