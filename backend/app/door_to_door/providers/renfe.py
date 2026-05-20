from urllib.parse import urlencode

from app.door_to_door.providers.base import DoorToDoorProviderQuery
from app.door_to_door.providers.scraper_base import ScraperProviderBase
from app.door_to_door.schemas import DoorToDoorOptionOut


class RenfeProvider(ScraperProviderBase):
    provider_name = "renfe"
    feature_flag = "DOOR_TO_DOOR_ENABLE_SCRAPER_RENFE"
    search_base_url = "https://www.renfe.com/es/es"

    def build_deeplink(self, query: DoorToDoorProviderQuery) -> str:
        params = urlencode({
            "from": query.origin.label,
            "to": query.final_destination.label,
            "date": query.flight.departure_at.date().isoformat(),
            "passengers": query.preferences.passengers,
        })
        return f"{self.search_base_url}?{params}"

    async def search_enabled(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
        # Real scraping is opt-in and intentionally isolated. The first enabled
        # version must add provider-specific parser fixtures before returning data.
        return []
