import os
import time
from collections import deque

import requests

from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import DoorToDoorOptionOut


class ScraperCircuitOpen(RuntimeError):
    pass


class ScraperProviderBase(DoorToDoorProvider):
    source_type = "scraper"
    feature_flag: str = ""
    user_agent = "ViruTrackerDoorToDoorBot/0.1 (+https://viru.app; contact: soporte@viru.app)"
    rate_limit_per_minute = 6
    timeout_seconds = 8.0
    max_failures_before_open = 3

    def __init__(self) -> None:
        self._request_times: deque[float] = deque()
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

    def _check_rate_limit(self) -> None:
        now = time.monotonic()
        while self._request_times and now - self._request_times[0] > 60:
            self._request_times.popleft()
        if len(self._request_times) >= self.rate_limit_per_minute:
            raise RuntimeError(f"{self.provider_name} scraper rate limit reached")
        self._request_times.append(now)

    def _fetch_public_html(self, url: str) -> str:
        self._check_rate_limit()
        try:
            response = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=self.timeout_seconds)
            response.raise_for_status()
            self._failure_count = 0
            return response.text
        except Exception:
            self._failure_count += 1
            if self._failure_count >= self.max_failures_before_open:
                self._circuit_open_until = time.monotonic() + 300
            raise
