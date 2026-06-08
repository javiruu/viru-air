from app.door_to_door.schemas import DoorToDoorOptionOut, DoorToDoorSummaryOut


def build_summary(options: list[DoorToDoorOptionOut]) -> DoorToDoorSummaryOut:
    if not options:
        return DoorToDoorSummaryOut()
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
