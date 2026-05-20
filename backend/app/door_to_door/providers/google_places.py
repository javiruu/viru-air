from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import DoorToDoorOptionOut


class GooglePlacesProvider(DoorToDoorProvider):
    provider_name = "google_places"
    source_type = "api"

    async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        return []

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            status="configured_placeholder",
            source_type=self.source_type,
            confidence="unavailable",
            message="Adapter preparado; no activo en V1 mock estable.",
        )
