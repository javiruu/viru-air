from datetime import datetime

from app.services.incoming_delay_prediction import (
    DelayPredictionSignal,
    estimate_incoming_delay,
)


def test_estimate_incoming_delay_flags_late_aircraft_with_tight_turnaround() -> None:
    # Given: the inbound aircraft is still airborne and now leaves only 20 minutes on stand.
    signal = DelayPredictionSignal(
        target_scheduled_departure_at=datetime(2026, 7, 28, 12, 0),
        target_estimated_departure_at=None,
        incoming_scheduled_arrival_at=datetime(2026, 7, 28, 10, 30),
        incoming_estimated_arrival_at=datetime(2026, 7, 28, 11, 40),
        incoming_actual_arrival_at=None,
        incoming_status="active",
        incoming_freshness="fresh",
    )

    # When: Viru applies its deterministic rotation rules.
    estimate = estimate_incoming_delay(signal)

    # Then: the result is high-risk, bounded, and explains the rotation pressure.
    assert estimate.risk == "high"
    assert estimate.risk_score == 90
    assert estimate.confidence == "high"
    assert estimate.predicted_delay_min_minutes == 20
    assert estimate.predicted_delay_max_minutes == 40
    assert estimate.turnaround_minutes == 20
    assert estimate.factor_codes == (
        "incoming_running_late",
        "tight_turnaround",
        "incoming_airborne",
    )


def test_estimate_incoming_delay_keeps_healthy_landed_rotation_low_risk() -> None:
    # Given: the exact inbound aircraft landed with 100 minutes before the next departure.
    signal = DelayPredictionSignal(
        target_scheduled_departure_at=datetime(2026, 7, 28, 12, 0),
        target_estimated_departure_at=None,
        incoming_scheduled_arrival_at=datetime(2026, 7, 28, 10, 20),
        incoming_estimated_arrival_at=None,
        incoming_actual_arrival_at=datetime(2026, 7, 28, 10, 20),
        incoming_status="landed",
        incoming_freshness="fresh",
    )

    # When: Viru evaluates the available turnaround.
    estimate = estimate_incoming_delay(signal)

    # Then: it reports a low-risk window instead of manufacturing a delay.
    assert estimate.risk == "low"
    assert estimate.risk_score == 15
    assert estimate.confidence == "high"
    assert estimate.predicted_delay_min_minutes == 0
    assert estimate.predicted_delay_max_minutes == 15
    assert estimate.turnaround_minutes == 100
    assert estimate.factor_codes == ("incoming_landed", "healthy_turnaround")


def test_estimate_incoming_delay_marks_stale_rotation_as_low_confidence() -> None:
    # Given: the inbound estimate is late, but its operational observation has expired.
    signal = DelayPredictionSignal(
        target_scheduled_departure_at=datetime(2026, 7, 28, 12, 0),
        target_estimated_departure_at=None,
        incoming_scheduled_arrival_at=datetime(2026, 7, 28, 10, 30),
        incoming_estimated_arrival_at=datetime(2026, 7, 28, 11, 30),
        incoming_actual_arrival_at=None,
        incoming_status="active",
        incoming_freshness="stale",
    )

    # When: Viru evaluates the same rules with stale evidence.
    estimate = estimate_incoming_delay(signal)

    # Then: risk remains visible while confidence and the delay range become conservative.
    assert estimate.risk == "high"
    assert estimate.risk_score == 75
    assert estimate.confidence == "low"
    assert estimate.predicted_delay_min_minutes == 5
    assert estimate.predicted_delay_max_minutes == 55
    assert estimate.turnaround_minutes == 30
    assert estimate.factor_codes == (
        "incoming_running_late",
        "tight_turnaround",
        "incoming_airborne",
        "stale_observation",
    )
