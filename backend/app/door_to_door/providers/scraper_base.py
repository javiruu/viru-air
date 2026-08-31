import os
import time

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import DoorToDoorOptionOut


class ScraperCircuitOpen(RuntimeError):
    pass


class ScraperProviderBase(DoorToDoorProvider):
    source_type = "scraper"
    feature_flag: str = ""
    user_agent = "ViruAirDoorToDoorBot/0.1 (+https://viru.app; contact: soporte@viru.app)"
    timeout_seconds = 8.0
    max_failures_before_open = 3

    def __init__(self) -> None:
        self._failure_count = 0
        self._circuit_open_until = 0.0

    def enabled(self) -> bool:
        return os.getenv(self.feature_flag, "false").lower() in {"1", "true", "yes"}

    async def healthcheck(self) -> ProviderHealth:
        if not self.enabled():
            return ProviderHealth(
                provider=self.provider_name,
                status="disabled",
                source_type="scraper",
                confidence="unavailable",
                message="Scraper opt-in flag is disabled.",
            )
        if self._circuit_open_until > time.monotonic():
            return ProviderHealth(
                provider=self.provider_name,
                status="circuit_open",
                source_type="scraper",
                confidence="unavailable",
                message="Circuit breaker is open after repeated scraper errors.",
            )
        return ProviderHealth(self.provider_name, "ok", "scraper", "estimated")

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        if not self.enabled():
            return []
        if self._circuit_open_until > time.monotonic():
            raise ScraperCircuitOpen(f"{self.provider_name} scraper circuit is open")
        return await self.search_enabled(query)

    async def search_enabled(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        return []
