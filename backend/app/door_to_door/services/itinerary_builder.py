from app.door_to_door.schemas import DoorToDoorOptionOut, DoorToDoorSummaryOut

RISK_ORDER = {"low": 0, "medium": 1, "unknown": 2, "high": 3}


def build_summary(options: list[DoorToDoorOptionOut]) -> DoorToDoorSummaryOut:
    if not options:
        return DoorToDoorSummaryOut()
    recommended = max(options, key=lambda option: option.score)
    cheapest = min(
        options,
        key=lambda option: (option.total_price_min is None, option.total_price_min or 10_000, -option.score),
    )
    lowest_risk = min(options, key=lambda option: (RISK_ORDER[option.risk_level], -option.score))
    fastest = min(options, key=lambda option: option.total_duration_minutes)
    fewest_changes = min(options, key=lambda option: (option.transfer_count, -option.score))
    for option in options:
        option.is_recommended = option.id == recommended.id
    return DoorToDoorSummaryOut(
        recommended_option_id=recommended.id,
        cheapest_option_id=cheapest.id,
        lowest_risk_option_id=lowest_risk.id,
        fastest_option_id=fastest.id,
        fewest_changes_option_id=fewest_changes.id,
    )
