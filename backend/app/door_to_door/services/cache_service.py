from datetime import datetime, timedelta
from typing import Any


class DoorToDoorCacheService:
    def __init__(self, ttl_seconds: int = 900) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[datetime, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if not item:
            return None
        created_at, value = item
        if created_at + timedelta(seconds=self.ttl_seconds) < datetime.utcnow():
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._items[key] = (datetime.utcnow(), value)
