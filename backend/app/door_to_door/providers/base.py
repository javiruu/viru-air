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

    async def run_search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        return await asyncio.wait_for(self.search(query), timeout=self.timeout_seconds)

    @abstractmethod
    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        raise NotImplementedError

    @abstractmethod
    async def healthcheck(self) -> ProviderHealth:
        raise NotImplementedError
