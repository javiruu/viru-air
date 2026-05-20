from app.door_to_door.schemas import DoorToDoorConfidence, DoorToDoorRiskLevel

RISK_PENALTY: dict[DoorToDoorRiskLevel, int] = {
    "low": 0,
    "medium": 14,
    "high": 34,
    "unknown": 24,
}

CONFIDENCE_PENALTY: dict[DoorToDoorConfidence, int] = {
    "live": 0,
    "cached": 5,
    "estimated": 10,
    "deeplink": 14,
    "unavailable": 28,
}


def score_itinerary(
    price_midpoint: float | None,
    duration_minutes: int,
    airport_buffer_minutes: int | None,
    transfer_count: int,
    risk_level: DoorToDoorRiskLevel,
    confidence: DoorToDoorConfidence,
    uncomfortable_hour: bool = False,
    luggage_penalty: int = 0,
) -> int:
    price_penalty = 16 if price_midpoint is None else min(24, int(price_midpoint / 8))
    duration_penalty = min(22, max(0, int((duration_minutes - 360) / 35)))
    transfer_penalty = min(16, transfer_count * 4)
    buffer_bonus = 0
    if airport_buffer_minutes is not None and airport_buffer_minutes >= 150:
        buffer_bonus = 5
    hour_penalty = 6 if uncomfortable_hour else 0
    raw = (
        100
        - price_penalty
        - duration_penalty
        - transfer_penalty
        - RISK_PENALTY[risk_level]
        - CONFIDENCE_PENALTY[confidence]
        - hour_penalty
        - luggage_penalty
        + buffer_bonus
    )
    return max(0, min(100, raw))
