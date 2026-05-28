"""Door-to-door provider adapters."""

from app.door_to_door.providers.deeplink_blablacar import BlaBlaCarDeepLinkProvider
from app.door_to_door.providers.deeplink_goopti import GoOptiDeepLinkProvider
from app.door_to_door.providers.google_places import GooglePlacesSuggestionsProvider
from app.door_to_door.providers.google_routes import GoogleRoutesProvider
from app.door_to_door.providers.gtfs_transit import GtfsTransitProvider
from app.door_to_door.providers.mock import MockDoorToDoorProvider
from app.door_to_door.providers.nominatim import NominatimSuggestionsProvider
from app.door_to_door.providers.registry import ProviderRuntime, resolve_provider_runtime

__all__ = [
    "BlaBlaCarDeepLinkProvider",
    "GoOptiDeepLinkProvider",
    "GtfsTransitProvider",
    "GooglePlacesSuggestionsProvider",
    "NominatimSuggestionsProvider",
    "GoogleRoutesProvider",
    "MockDoorToDoorProvider",
    "ProviderRuntime",
    "resolve_provider_runtime",
]
