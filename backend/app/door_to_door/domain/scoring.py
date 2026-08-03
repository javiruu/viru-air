"""Door-to-door itinerary scoring.

Fase 7: scoring now weighs completeness, graduated buffer, and actionable utility.
A "recommended" route earns its badge — not just cosmetic ordering.
"""

from app.door_to_door.schemas import DoorToDoorCompleteness, DoorToDoorConfidence


CONFIDENCE_PENALTY: dict[DoorToDoorConfidence, int] = {
    "live": 0,
    "cached": 5,
    "estimated": 10,
    "deeplink": 14,
    "unavailable": 28,
}

COMPLETENESS_BONUS: dict[DoorToDoorCompleteness, int] = {
    "full": 12,
    "partial_actionable": 0,
    "exploratory": -24,
}


def _buffer_score(airport_buffer_minutes: int | None) -> int:
    """Graduated buffer score: rewards margin, penalises tight connections."""
    if airport_buffer_minutes is None:
        return 0
    if airport_buffer_minutes >= 180:
        return 10
    if airport_buffer_minutes >= 150:
        return 7
    if airport_buffer_minutes >= 120:
        return 4
    if airport_buffer_minutes >= 90:
        return 2
    # Tight buffer: < 90 min
    return -5


def score_itinerary(
    price_midpoint: float | None,
    duration_minutes: int,
    airport_buffer_minutes: int | None,
    transfer_count: int,
    confidence: DoorToDoorConfidence,
    completeness: DoorToDoorCompleteness = "partial_actionable",
    uncomfortable_hour: bool = False,
    luggage_penalty: int = 0,
    source_quality_bonus: int = 0,
) -> int:
    """Score an itinerary 0–100.

    Weights:
      - completeness: heavy (full +12, partial 0, exploratory -24)
      - confidence: live=0, cached=-5, deeplink=-14, unavailable=-28
      - duration: penalty for very long trips
      - price: penalty when missing (-12) or proportional to cost
      - buffer: graduated — rewards margin, penalises tight (< 90 min)
      - transfers: linear penalty per change
      - hour: small penalty for uncomfortable departure times
      - source_quality_bonus: Fase 6 arbitration — bonus for higher-quality source data
    """
    # Completeness
    completeness_delta = COMPLETENESS_BONUS[completeness]

    # Price: reduced penalty for null (deeplinks are still useful)
    price_penalty = 12 if price_midpoint is None else min(24, int(price_midpoint / 8))

    # Duration: penalty proportional to excess over 6 hours
    duration_penalty = min(22, max(0, int((duration_minutes - 360) / 35)))

    # Transfers: 4 points per transfer, capped at 16
    transfer_penalty = min(16, transfer_count * 4)

    # Buffer: graduated
    buffer_delta = _buffer_score(airport_buffer_minutes)

    # Uncomfortable hour
    hour_penalty = 6 if uncomfortable_hour else 0

    raw = (
        100
        - price_penalty
        - duration_penalty
        - transfer_penalty
        - CONFIDENCE_PENALTY[confidence]
        - hour_penalty
        - luggage_penalty
        + buffer_delta
        + completeness_delta
        + source_quality_bonus
    )
    return max(0, min(100, raw))
