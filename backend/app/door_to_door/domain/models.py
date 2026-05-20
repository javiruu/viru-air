from dataclasses import dataclass

from app.door_to_door.schemas import DoorToDoorConfidence, DoorToDoorSourceType


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    status: str
    source_type: DoorToDoorSourceType
    confidence: DoorToDoorConfidence
    message: str | None = None
