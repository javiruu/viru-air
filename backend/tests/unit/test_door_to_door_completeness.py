"""Unit tests for itinerary builder completeness classification (Fase 6)."""

from datetime import datetime, timezone

from app.door_to_door.schemas import (
    DoorToDoorLegOut,
    DoorToDoorOptionOut,
    DoorToDoorSourceOut,
)
from app.door_to_door.services.itinerary_builder import assign_completeness


_NOW = datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)


def _make_leg(*, leg_type="ground", source_type="deeplink", duration=None, departure=None, arrival=None, actions=None, booking_url=None) -> DoorToDoorLegOut:
    return DoorToDoorLegOut(
        type=leg_type,  # type: ignore[arg-type]
        mode="car",
        from_location="Origin",
        to_location="Destination",
        duration_minutes=duration,
        departure_at=departure,
        arrival_at=arrival,
        source_type=source_type,  # type: ignore[arg-type]
        actions=actions or [],
        booking_url=booking_url,
    )


def _make_option(option_id: str, status="real_deeplink", legs=None, sources=None, confidence="deeplink") -> DoorToDoorOptionOut:
    return DoorToDoorOptionOut(
        id=option_id,
        label="Test option",
        description="Test",
        status=status,  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        source_types=["deeplink"],
        sources=sources or [
            DoorToDoorSourceOut(
                provider="test",
                source_provider="test",
                source_type="deeplink",
                confidence="deeplink",
                checked_at=_NOW,
            )
        ],
        legs=legs or [
            _make_leg(source_type="deeplink"),
            DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
            _make_leg(source_type="deeplink"),
        ],
        transfer_count=2,
    )


def test_full_when_all_ground_legs_have_api_data():
    """Full completeness when both ground legs carry real api/maps/open_data with duration."""
    legs = [
        _make_leg(source_type="api", duration=120),
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
        _make_leg(source_type="maps", duration=35),
    ]
    options = [_make_option("opt1", legs=legs, status="real_result")]
    assign_completeness(options)
    assert options[0].completeness == "full"


def test_full_when_all_ground_legs_have_schedule():
    """Full completeness when ground legs have departure/arrival from open_data."""
    d1 = datetime(2026, 6, 14, 8, 0, tzinfo=timezone.utc)
    d2 = datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc)
    legs = [
        _make_leg(source_type="open_data", departure=d1, arrival=d2),
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
        _make_leg(source_type="open_data", departure=d1, arrival=d2),
    ]
    options = [_make_option("opt1", legs=legs)]
    assign_completeness(options)
    assert options[0].completeness == "full"


def test_partial_actionable_when_one_leg_is_deeplink():
    """Partial actionable when one leg has api data but the other is deeplink-only."""
    legs = [
        _make_leg(source_type="api", duration=120),
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
        _make_leg(source_type="deeplink"),
    ]
    options = [_make_option("opt1", legs=legs)]
    assign_completeness(options)
    assert options[0].completeness == "partial_actionable"


def test_partial_actionable_when_both_legs_are_deeplink():
    """Partial actionable when all ground legs are deeplink-based (actionable but no real data)."""
    legs = [
        _make_leg(source_type="deeplink"),
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
        _make_leg(source_type="external_deeplink"),
    ]
    options = [_make_option("opt1", legs=legs)]
    assign_completeness(options)
    assert options[0].completeness == "partial_actionable"


def test_exploratory_when_legs_are_estimate_only():
    """Exploratory when all ground legs are estimate/mock with no real data or actions."""
    legs = [
        _make_leg(source_type="estimate"),
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
        _make_leg(source_type="mock"),
    ]
    options = [_make_option("opt1", status="estimate_only", legs=legs)]
    assign_completeness(options)
    assert options[0].completeness == "exploratory"


def test_exploratory_when_no_ground_legs():
    """Exploratory when there are no ground legs at all."""
    legs = [
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
    ]
    options = [_make_option("opt1", legs=legs)]
    assign_completeness(options)
    assert options[0].completeness == "exploratory"


def test_full_beats_partial_in_mixed_list():
    """When mixing full and partial options, each gets its own correct label."""
    full_legs = [
        _make_leg(source_type="api", duration=120),
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
        _make_leg(source_type="maps", duration=35),
    ]
    partial_legs = [
        _make_leg(source_type="api", duration=120),
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
        _make_leg(source_type="deeplink"),
    ]
    options = [
        _make_option("opt_full", legs=full_legs, status="real_result"),
        _make_option("opt_partial", legs=partial_legs),
    ]
    assign_completeness(options)
    assert options[0].completeness == "full"
    assert options[1].completeness == "partial_actionable"


def test_completeness_persists_through_build_summary():
    """build_summary calls assign_completeness implicitly, so options get classified."""
    from app.door_to_door.services.itinerary_builder import build_summary

    legs = [
        _make_leg(source_type="api", duration=120),
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
        _make_leg(source_type="api", duration=35),
    ]
    option = _make_option("opt_full", legs=legs, status="real_result")
    option.score = 75

    summary = build_summary([option])
    assert summary.recommended_option_id == "opt_full"
    assert option.completeness == "full"


def test_full_airport_only_with_one_ground_leg_api():
    """Full when airport_only has a single ground leg with real api data + duration."""
    legs = [
        _make_leg(source_type="api", duration=120),
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
    ]
    options = [_make_option("opt", legs=legs, status="real_result")]
    assign_completeness(options)
    assert options[0].completeness == "full"


def test_api_source_without_concrete_data_is_not_full():
    """A leg with source_type=api but no duration or schedule should NOT count as full."""
    legs = [
        _make_leg(source_type="api"),  # api source but no duration or schedule
        DoorToDoorLegOut(type="flight", mode="flight", from_location="AGP", to_location="TSF"),
        _make_leg(source_type="api"),
    ]
    options = [_make_option("opt", legs=legs)]
    assign_completeness(options)
    assert options[0].completeness != "full"
    assert options[0].completeness == "partial_actionable"
