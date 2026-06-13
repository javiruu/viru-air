"""Itinerary builder: composes and classifies door-to-door options.

Fase 6: introduces completeness as a first-class signal per option.
- full: all ground legs carry real data (api/maps/open_data with schedule or duration)
- partial_actionable: at least one ground leg has real data or deeplink actions
- exploratory: no ground leg has real data — informational only
"""

from app.door_to_door.schemas import DoorToDoorOptionOut, DoorToDoorSummaryOut


_REAL_SOURCE_TYPES = {"api", "maps", "open_data"}
_ACTIONABLE_SOURCE_TYPES = _REAL_SOURCE_TYPES | {"deeplink", "external_deeplink"}


def _leg_has_real_data(leg) -> bool:
    """A ground leg has real data if it has duration or schedule from a real source."""
    if leg.type != "ground":
        return False
    if leg.source_type not in _REAL_SOURCE_TYPES:
        return False
    # Must have at least one concrete data point (duration or schedule)
    if leg.duration_minutes is not None:
        return True
    if leg.departure_at is not None and leg.arrival_at is not None:
        return True
    return False


def _leg_has_actions(leg) -> bool:
    """A ground leg is actionable if it has external actions or booking_url."""
    if leg.type != "ground":
        return False
    if leg.actions:
        return True
    if leg.booking_url:
        return True
    return False


def _leg_has_any_data(leg) -> bool:
    """A ground leg has any data if source is actionable or it has actions."""
    if leg.type != "ground":
        return False
    if leg.source_type in _ACTIONABLE_SOURCE_TYPES:
        return True
    if leg.actions or leg.booking_url:
        return True
    return False


def assign_completeness(options: list[DoorToDoorOptionOut]) -> None:
    """Classify each option by completeness and annotate it in-place."""
    for option in options:
        ground_legs = [leg for leg in option.legs if leg.type == "ground"]

        if not ground_legs:
            option.completeness = "exploratory"
            continue

        real_count = sum(1 for leg in ground_legs if _leg_has_real_data(leg))
        actionable_count = sum(1 for leg in ground_legs if _leg_has_actions(leg))
        any_data_count = sum(1 for leg in ground_legs if _leg_has_any_data(leg))

        if real_count == len(ground_legs):
            option.completeness = "full"
        elif real_count > 0 or actionable_count > 0 or any_data_count > 0:
            option.completeness = "partial_actionable"
        else:
            option.completeness = "exploratory"


def build_summary(options: list[DoorToDoorOptionOut]) -> DoorToDoorSummaryOut:
    if not options:
        return DoorToDoorSummaryOut()

    # Assign completeness before scoring
    assign_completeness(options)

    recommended = max(options, key=lambda option: option.score or 0)
    cheapest = min(
        options,
        key=lambda option: (option.total_price_min is None, option.total_price_min or 10_000, -(option.score or 0)),
    )
    fastest = min(options, key=lambda option: (option.total_duration_minutes is None, option.total_duration_minutes or 999_999))
    fewest_changes = min(options, key=lambda option: (option.transfer_count, -(option.score or 0)))
    for option in options:
        option.is_recommended = option.id == recommended.id
    return DoorToDoorSummaryOut(
        recommended_option_id=recommended.id,
        cheapest_option_id=cheapest.id,
        fastest_option_id=fastest.id,
        fewest_changes_option_id=fewest_changes.id,
    )
