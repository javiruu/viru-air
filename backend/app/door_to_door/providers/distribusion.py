from app.door_to_door.domain.models import ProviderHealth
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import DoorToDoorOptionOut


class DistribusionProvider(DoorToDoorProvider):
    provider_name = "distribusion"
    source_type = "aggregator"

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
