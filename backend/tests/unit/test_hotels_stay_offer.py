from datetime import date
from decimal import Decimal

import pytest

from app.hotels.stay_offer import (
    CancellationPolicy,
    FeeBreakdown,
    FeeLine,
    Occupancy,
    OccupancyRoom,
    OfferIdentity,
    RoomSignature,
    SnapshotOutcome,
    StayQuery,
    stay_query_from_legacy,
)


def build_stay(*, children_ages: tuple[int, ...] = (7, 3), rooms: int = 1) -> StayQuery:
    return StayQuery(
        canonical_hotel_id="hotel-viru",
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 13),
        occupancy=Occupancy.from_rooms(
            tuple(OccupancyRoom(adults=2, children_ages=children_ages) for _ in range(rooms))
        ),
        currency="EUR",
    )


def test_stay_fingerprint_is_canonical_but_keeps_price_dimensions() -> None:
    canonical = build_stay(children_ages=(3, 7))
    reordered = build_stay(children_ages=(7, 3))

    assert canonical.fingerprint == reordered.fingerprint
    assert canonical.fingerprint != build_stay(children_ages=(3, 8)).fingerprint
    assert canonical.fingerprint != build_stay(rooms=2).fingerprint
    assert canonical.nights == 3


def test_legacy_bridge_marks_inferred_occupancy_without_changing_v1_guest_meaning() -> None:
    stay = stay_query_from_legacy(
        canonical_hotel_id="hotel-viru",
        area_key=None,
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 13),
        guests=2,
    )

    assert stay.occupancy.source == "legacy_inferred"
    assert stay.occupancy.total_adults == 2
    assert stay.occupancy.total_children == 0
    assert len(stay.occupancy.rooms) == 1


@pytest.mark.parametrize(
    ("factory", "error_code"),
    [
        (
            lambda: build_stay().__class__(
                canonical_hotel_id="hotel-viru",
                area_key=None,
                check_in=date(2026, 9, 13),
                check_out=date(2026, 9, 10),
                occupancy=Occupancy.from_rooms((OccupancyRoom(adults=2),)),
                currency="EUR",
            ),
            "hotel_stay_dates_invalid",
        ),
        (lambda: OccupancyRoom(adults=0), "hotel_occupancy_room_requires_adult"),
        (lambda: OccupancyRoom(adults=2, children_ages=(18,)), "hotel_occupancy_child_age_invalid"),
        (lambda: build_stay().__class__(
            canonical_hotel_id="hotel-viru",
            area_key=None,
            check_in=date(2026, 9, 10),
            check_out=date(2026, 9, 13),
            occupancy=Occupancy.from_rooms((OccupancyRoom(adults=2),)),
            currency="eur",
        ), "hotel_currency_invalid"),
    ],
)
def test_stay_invariants_reject_ambiguous_or_invalid_inputs(factory, error_code: str) -> None:
    with pytest.raises(ValueError, match=error_code):
        factory()


def test_offer_identity_separates_provider_and_conditions() -> None:
    stay = build_stay()
    fees = FeeBreakdown(
        currency="EUR",
        semantics="total",
        amount_base=Decimal("100.00"),
        amount_total=Decimal("120.00"),
        fees=(FeeLine(fee_code="tax", amount=Decimal("20.00"), currency="EUR", status="included"),),
        conditions_completeness="complete",
    )
    booking = OfferIdentity(
        provider_id="booking_demand",
        provider_hotel_id="provider-hotel-1",
        provider_offer_id="room-1",
        stay_query=stay,
        room=RoomSignature(provider_room_id="room-1", room_type_normalized="standard"),
        meal_plan_normalized="BB",
        cancellation=CancellationPolicy(cancellation_type="refundable", conditions_completeness="complete"),
        fees=fees,
    )
    lite = OfferIdentity(
        provider_id="liteapi",
        provider_hotel_id="provider-hotel-1",
        provider_offer_id="room-1",
        stay_query=stay,
        room=RoomSignature(provider_room_id="room-1", room_type_normalized="standard"),
        meal_plan_normalized="BB",
        cancellation=CancellationPolicy(cancellation_type="refundable", conditions_completeness="complete"),
        fees=fees,
    )

    assert booking.fingerprint != lite.fingerprint
    assert fees.is_total_comparable is True


def test_fee_and_snapshot_invariants_do_not_turn_unknowns_or_errors_into_prices() -> None:
    with pytest.raises(ValueError, match="hotel_total_amount_semantics_invalid"):
        FeeBreakdown(currency="EUR", semantics="unknown", amount_total=Decimal("100"))
    with pytest.raises(ValueError, match="hotel_fee_currency_mismatch"):
        FeeBreakdown(
            currency="EUR",
            semantics="base",
            amount_base=Decimal("100"),
            fees=(FeeLine(fee_code="tax", amount=Decimal("5"), currency="USD"),),
        )

    assert SnapshotOutcome(status="success", availability_status="available").is_price_eligible is True
    assert SnapshotOutcome(status="timeout", availability_status="provider_error").is_price_eligible is False
    assert SnapshotOutcome(status="partial", availability_status="limited", replay=True).is_price_eligible is False
