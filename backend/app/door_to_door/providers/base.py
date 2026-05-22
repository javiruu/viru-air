import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.schemas import (
    DoorToDoorFlightOut,
    DoorToDoorLocation,
    DoorToDoorOptionOut,
    DoorToDoorPreferences,
    DoorToDoorSourceType,
    DoorToDoorWarningOut,
)


@dataclass(frozen=True)
class DoorToDoorProviderQuery:
    origin: DoorToDoorLocation
    final_destination: DoorToDoorLocation
    preferences: DoorToDoorPreferences
    flight: DoorToDoorFlightOut
    checked_at: datetime


class DoorToDoorProvider(ABC):
    provider_name: str
    source_type: DoorToDoorSourceType
    timeout_seconds: float = 4.0
    rate_limit_per_minute: int = 30
    _warnings: list[DoorToDoorWarningOut]

    def __init__(self) -> None:
        self._warnings = []

    async def run_search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        self._warnings = []
        return await asyncio.wait_for(self.search(query), timeout=self.timeout_seconds)

    def push_warning(self, code: str, message: str, provider: str | None = None) -> None:
        self._warnings.append(
            DoorToDoorWarningOut(code=code, message=message, provider=provider or self.provider_name)
        )

    def consume_warnings(self) -> list[DoorToDoorWarningOut]:
        warnings = self._warnings
        self._warnings = []
        return warnings

    @abstractmethod
    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        raise NotImplementedError

    @abstractmethod
    async def healthcheck(self) -> ProviderHealth:
        raise NotImplementedError
