from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0058_hotel_tracked_offer_offer_identity"
down_revision: Union[str, None] = "0057_hotel_canonical_stay_offer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_IDENTITY_COLUMNS = [
    "user_id",
    "hotel_id",
    "check_in",
    "check_out",
    "guests",
    "provider",
    "room_label",
    "meal_plan",
    "cancellation_policy",
    "currency",
    "offer_fingerprint",
]
_LEGACY_IDENTITY_COLUMNS = ["user_id", "hotel_id", "check_in", "check_out", "guests", "provider"]
_LEGACY_IDENTITY_WHERE = "offer_fingerprint IS NULL AND check_in IS NOT NULL AND check_out IS NOT NULL"


def _assert_downgrade_preserves_legacy_identity() -> None:
    tracked_offer = sa.table(
        "hotel_tracked_offer",
        *(sa.column(name) for name in _LEGACY_IDENTITY_COLUMNS),
    )
    duplicate = op.get_bind().execute(
        sa.select(*[tracked_offer.c[name] for name in _LEGACY_IDENTITY_COLUMNS])
        .where(
            tracked_offer.c.check_in.is_not(None),
            tracked_offer.c.check_out.is_not(None),
        )
        .group_by(*[tracked_offer.c[name] for name in _LEGACY_IDENTITY_COLUMNS])
        .having(sa.func.count() > 1)
        .limit(1)
    ).first()
    if duplicate is not None:
        raise RuntimeError("hotel_tracking_0058_downgrade_requires_semantic_offer_merge")


def upgrade() -> None:
    with op.batch_alter_table("hotel_tracked_offer") as batch_op:
        batch_op.add_column(sa.Column("offer_fingerprint", sa.String(length=64), nullable=True))
        batch_op.drop_constraint("uq_hotel_tracked_offer_identity", type_="unique")
        batch_op.create_unique_constraint("uq_hotel_tracked_offer_identity", _IDENTITY_COLUMNS)
        batch_op.create_index("ix_hotel_tracked_offer_offer_fingerprint", ["offer_fingerprint"])
    op.create_index(
        "uq_hotel_tracked_offer_legacy_identity",
        "hotel_tracked_offer",
        _LEGACY_IDENTITY_COLUMNS,
        unique=True,
        sqlite_where=sa.text(_LEGACY_IDENTITY_WHERE),
        postgresql_where=sa.text(_LEGACY_IDENTITY_WHERE),
    )


def downgrade() -> None:
    _assert_downgrade_preserves_legacy_identity()
    op.drop_index("uq_hotel_tracked_offer_legacy_identity", table_name="hotel_tracked_offer")
    with op.batch_alter_table("hotel_tracked_offer") as batch_op:
        batch_op.drop_index("ix_hotel_tracked_offer_offer_fingerprint")
        batch_op.drop_constraint("uq_hotel_tracked_offer_identity", type_="unique")
        batch_op.drop_column("offer_fingerprint")
        batch_op.create_unique_constraint(
            "uq_hotel_tracked_offer_identity",
            _LEGACY_IDENTITY_COLUMNS,
        )
