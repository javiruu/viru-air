import os
from dataclasses import dataclass
from typing import Callable

from app.door_to_door.providers.base import DoorToDoorProvider
from app.door_to_door.providers.deeplink_blablacar import BlaBlaCarDeepLinkProvider
from app.door_to_door.providers.deeplink_goopti import GoOptiDeepLinkProvider
from app.door_to_door.providers.google_places import GooglePlacesSuggestionsProvider
from app.door_to_door.providers.google_routes import GoogleRoutesProvider
from app.door_to_door.providers.mock import MockDoorToDoorProvider
from app.door_to_door.schemas import DoorToDoorProviderStatusOut, DoorToDoorSourceType


@dataclass(frozen=True)
class ProviderDescriptor:
    name: str
    source_type: DoorToDoorSourceType
    base_status: str
    production_ready: bool
    supports_search: bool
    supports_booking_url: bool
    has_tests: bool
    notes: str
    is_mock: bool = False
    is_real: bool = False
    is_scraper: bool = False
    factory: Callable[[], DoorToDoorProvider] | None = None


@dataclass(frozen=True)
class ProviderRuntime:
    providers: list[DoorToDoorProvider]
    statuses: list[DoorToDoorProviderStatusOut]
    mock_enabled: bool
    real_enabled: bool
    scrapers_enabled: bool
    google_places_provider: GooglePlacesSuggestionsProvider | None


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _has_google_key() -> bool:
    return bool(os.getenv("GOOGLE_MAPS_API_KEY", "").strip())


def resolve_provider_runtime() -> ProviderRuntime:
    app_env = os.getenv("APP_ENV", "local").strip().lower()
    mock_default = app_env in {"local", "dev", "development", "test"}
    mock_enabled = _env_flag("DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER", mock_default and app_env != "production")
    real_enabled = _env_flag("DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS", False)
    scrapers_enabled = _env_flag("DOOR_TO_DOOR_ENABLE_SCRAPERS", False)
    google_routes_flag = _env_flag("DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES", False)
    google_places_flag = _env_flag("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", False)
    has_google_key = _has_google_key()

    google_routes_enabled = real_enabled and google_routes_flag and has_google_key
    google_places_enabled = real_enabled and google_places_flag and has_google_key

    descriptors: list[ProviderDescriptor] = [
        ProviderDescriptor(
            name="mock_multimodal",
            source_type="mock",
            base_status="functional_mock",
            production_ready=False,
            supports_search=True,
            supports_booking_url=False,
            has_tests=True,
            notes="Provider mock de desarrollo y QA. No debe estar activo por defecto en produccion.",
            is_mock=True,
            factory=MockDoorToDoorProvider,
        ),
        ProviderDescriptor(
            name="google_routes",
            source_type="api",
            base_status="functional_api" if google_routes_enabled else "disabled",
            production_ready=google_routes_enabled,
            supports_search=True,
            supports_booking_url=False,
            has_tests=True,
            notes=(
                "Duracion/distancia real de tramos terrestres."
                if google_routes_enabled
                else (
                    "Desactivado: falta GOOGLE_MAPS_API_KEY."
                    if real_enabled and google_routes_flag and not has_google_key
                    else "Desactivado: requiere DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS, DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES y GOOGLE_MAPS_API_KEY."
                )
            ),
            is_real=True,
            factory=GoogleRoutesProvider,
        ),
        ProviderDescriptor(
            name="blablacar_deeplink",
            source_type="deeplink",
            base_status="functional_deeplink",
            production_ready=True,
            supports_search=True,
            supports_booking_url=True,
            has_tests=True,
            notes="Genera deeplink funcional para tramo terrestre de salida.",
            is_real=True,
            factory=BlaBlaCarDeepLinkProvider,
        ),
        ProviderDescriptor(
            name="goopti_deeplink",
            source_type="deeplink",
            base_status="functional_deeplink",
            production_ready=True,
            supports_search=True,
            supports_booking_url=True,
            has_tests=True,
            notes="Genera deeplink funcional para tramo terrestre de llegada.",
            is_real=True,
            factory=GoOptiDeepLinkProvider,
        ),
        ProviderDescriptor(
            name="google_places",
            source_type="api",
            base_status="functional_api" if google_places_enabled else "disabled",
            production_ready=google_places_enabled,
            supports_search=False,
            supports_booking_url=False,
            has_tests=True,
            notes=(
                "Sugerencias reales de lugares para autocompletar."
                if google_places_enabled
                else (
                    "Desactivado: falta GOOGLE_MAPS_API_KEY."
                    if real_enabled and google_places_flag and not has_google_key
                    else "Desactivado: requiere DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS, DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES y GOOGLE_MAPS_API_KEY."
                )
            ),
            is_real=False,
            factory=None,
        ),
        ProviderDescriptor(
            name="gtfs",
            source_type="open_data",
            base_status="pure_stub",
            production_ready=False,
            supports_search=False,
            supports_booking_url=False,
            has_tests=False,
            notes="Placeholder GTFS sin busqueda operativa.",
        ),
        ProviderDescriptor(
            name="opentripplanner",
            source_type="open_data",
            base_status="pure_stub",
            production_ready=False,
            supports_search=False,
            supports_booking_url=False,
            has_tests=False,
            notes="Placeholder para motor multimodal propio.",
        ),
        ProviderDescriptor(
            name="navitia",
            source_type="api",
            base_status="pure_stub",
            production_ready=False,
            supports_search=False,
            supports_booking_url=False,
            has_tests=False,
            notes="Stub de API de transporte publico.",
        ),
        ProviderDescriptor(
            name="amadeus_transfers",
            source_type="api",
            base_status="pure_stub",
            production_ready=False,
            supports_search=False,
            supports_booking_url=False,
            has_tests=False,
            notes="Stub API de transfers.",
        ),
        ProviderDescriptor(
            name="mozio",
            source_type="aggregator",
            base_status="pure_stub",
            production_ready=False,
            supports_search=False,
            supports_booking_url=False,
            has_tests=False,
            notes="Stub partner API.",
        ),
        ProviderDescriptor(
            name="omio",
            source_type="aggregator",
            base_status="pure_stub",
            production_ready=False,
            supports_search=False,
            supports_booking_url=False,
            has_tests=False,
            notes="Stub B2B.",
        ),
        ProviderDescriptor(
            name="distribusion",
            source_type="aggregator",
            base_status="pure_stub",
            production_ready=False,
            supports_search=False,
            supports_booking_url=False,
            has_tests=False,
            notes="Stub B2B.",
        ),
        ProviderDescriptor(
            name="rome2rio",
            source_type="aggregator",
            base_status="deeplink_stub",
            production_ready=False,
            supports_search=False,
            supports_booking_url=False,
            has_tests=False,
            notes="Referencia de producto, sin integracion real.",
        ),
        ProviderDescriptor(
            name="blablacar_scraper",
            source_type="scraper",
            base_status="scraper_base_only",
            production_ready=False,
            supports_search=False,
            supports_booking_url=True,
            has_tests=False,
            notes="Existe base scraper con flag, sin parser/fixtures funcionales.",
            is_scraper=True,
        ),
        ProviderDescriptor(
            name="goopti_scraper",
            source_type="scraper",
            base_status="scraper_base_only",
            production_ready=False,
            supports_search=False,
            supports_booking_url=True,
            has_tests=False,
            notes="Existe base scraper con flag, sin parser/fixtures funcionales.",
            is_scraper=True,
        ),
        ProviderDescriptor(
            name="alsa_scraper",
            source_type="scraper",
            base_status="scraper_base_only",
            production_ready=False,
            supports_search=False,
            supports_booking_url=True,
            has_tests=False,
            notes="Existe base scraper con flag, sin parser/fixtures funcionales.",
            is_scraper=True,
        ),
        ProviderDescriptor(
            name="renfe_scraper",
            source_type="scraper",
            base_status="scraper_base_only",
            production_ready=False,
            supports_search=False,
            supports_booking_url=True,
            has_tests=False,
            notes="Existe base scraper con flag, sin parser/fixtures funcionales.",
            is_scraper=True,
        ),
    ]

    statuses: list[DoorToDoorProviderStatusOut] = []
    providers: list[DoorToDoorProvider] = []
    for descriptor in descriptors:
        enabled = False
        status = descriptor.base_status
        supports_search = descriptor.supports_search
        if descriptor.is_mock:
            enabled = mock_enabled
            status = descriptor.base_status if enabled else "disabled"
        elif descriptor.name == "google_routes":
            enabled = google_routes_enabled
            status = "functional_api" if enabled else "disabled"
        elif descriptor.is_real:
            enabled = real_enabled
            status = descriptor.base_status if enabled else "disabled"
        elif descriptor.is_scraper:
            enabled = real_enabled and scrapers_enabled
            status = descriptor.base_status
        elif descriptor.name == "google_places":
            enabled = google_places_enabled
            status = "functional_api" if enabled else "disabled"

        statuses.append(
            DoorToDoorProviderStatusOut(
                name=descriptor.name,
                enabled=enabled,
                status=status,  # type: ignore[arg-type]
                source_type=descriptor.source_type,
                production_ready=descriptor.production_ready,
                supports_search=supports_search and enabled,
                supports_booking_url=descriptor.supports_booking_url,
                has_tests=descriptor.has_tests,
                notes=descriptor.notes,
            )
        )
        if enabled and descriptor.factory is not None and descriptor.supports_search:
            providers.append(descriptor.factory())

    google_places_provider = (
        GooglePlacesSuggestionsProvider() if google_places_enabled else None
    )

    return ProviderRuntime(
        providers=providers,
        statuses=statuses,
        mock_enabled=mock_enabled,
        real_enabled=real_enabled,
        scrapers_enabled=scrapers_enabled,
        google_places_provider=google_places_provider,
    )
