from app.door_to_door.schemas import DoorToDoorConfidence, DoorToDoorRiskLevel


def calculate_risk_level(
    airport_buffer_minutes: int | None,
    transfer_count: int,
    confidence: DoorToDoorConfidence,
) -> DoorToDoorRiskLevel:
    if airport_buffer_minutes is None:
        return "unknown"
    if confidence == "unavailable":
        return "high"
    if airport_buffer_minutes < 90:
        return "high"
    if airport_buffer_minutes < 120 or transfer_count > 3:
        return "medium"
    return "low"
