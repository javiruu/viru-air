import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.door_to_door.providers.base import DoorToDoorProvider

logger = logging.getLogger(__name__)
from app.door_to_door.providers.deeplink_blablacar import BlaBlaCarDeepLinkProvider  # noqa: E402
from app.door_to_door.providers.deeplink_goopti import GoOptiDeepLinkProvider  # noqa: E402
from app.door_to_door.providers.deeplink_provider import DeeplinkDoorToDoorProvider  # noqa: E402
from app.door_to_door.providers.deeplink_maps import GoogleMapsDeepLinkProvider  # noqa: E402
from app.door_to_door.providers.google_places import GooglePlacesSuggestionsProvider  # noqa: E402
from app.door_to_door.providers.google_routes import GoogleRoutesProvider  # noqa: E402
from app.door_to_door.providers.gtfs_transit import GtfsTransitProvider  # noqa: E402
from app.door_to_door.providers.mock import MockDoorToDoorProvider  # noqa: E402
from app.door_to_door.providers.navitia import NavitiaProvider  # noqa: E402
from app.door_to_door.providers.nominatim import NominatimSuggestionsProvider  # noqa: E402
from app.door_to_door.schemas import DoorToDoorProviderStatusOut, DoorToDoorSourceType  # noqa: E402


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
    # Key-less providers construct external URLs (Google Maps directions,
    # BlaBlaCar/GoOpti search links) without external HTTP calls or API keys.
    # Always enabled — they are the user's guaranteed "real out" action,
    # even in empty deployments, because the link itself is the value.
    is_keyless: bool = False
    factory: Callable[[], DoorToDoorProvider] | None = None


@dataclass(frozen=True)
class ProviderRuntime:
    providers: list[DoorToDoorProvider]
    statuses: list[DoorToDoorProviderStatusOut]
    mock_enabled: bool
    real_enabled: bool
    scrapers_enabled: bool
    google_places_provider: GooglePlacesSuggestionsProvider | None
    nominatim_provider: NominatimSuggestionsProvider | None


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _has_google_key() -> bool:
    return bool(os.getenv("GOOGLE_MAPS_API_KEY", "").strip())


def _has_navitia_key() -> bool:
    return bool(os.getenv("NAVITIA_API_KEY", "").strip())


def _has_gtfs_feeds() -> bool:
    """Check whether GTFS feed descriptors are configured via any source.

    Mirrors the priority order in gtfs_feed_service.load_feed_descriptors():
    1. DOOR_TO_DOOR_GTFS_FEEDS_JSON env var (inline JSON)
    2. DOOR_TO_DOOR_GTFS_FEEDS_FILE env var (path to JSON file)
    3. Default manifest at providers/gtfs_feeds.json
    """
    raw = os.getenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", "").strip()
    if raw:
        return True
    file_path = os.getenv("DOOR_TO_DOOR_GTFS_FEEDS_FILE", "").strip()
    if file_path and Path(file_path).exists():
        return True
    # Fallback: default manifest next to this module
    default_manifest = Path(__file__).resolve().parent / "gtfs_feeds.json"
    return default_manifest.exists()


def _is_non_local_env() -> bool:
    """Return True when APP_ENV is staging or production (mock must be blocked)."""
    app_env = os.getenv("APP_ENV", "local").strip().lower()
    return app_env in {"staging", "production", "prod"}


def resolve_provider_runtime() -> ProviderRuntime:
    mock_enabled = _env_flag("DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER", False)
    real_enabled = _env_flag("DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS", False)
    scrapers_enabled = _env_flag("DOOR_TO_DOOR_ENABLE_SCRAPERS", False)
    google_routes_flag = _env_flag("DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES", False)
    google_places_flag = _env_flag("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", False)
    gtfs_transit_flag = _env_flag("DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT", False)
    navitia_flag = _env_flag("DOOR_TO_DOOR_ENABLE_NAVITIA", False)
    has_google_key = _has_google_key()
    has_gtfs_feeds = _has_gtfs_feeds()

    # Guard: block mock in staging/production
    mock_flag_original = mock_enabled
    if mock_enabled and _is_non_local_env():
        app_env = os.getenv("APP_ENV", "local").strip().lower()
        logger.warning(
            "mock_blocked_non_local_env",
            extra={"app_env": app_env, "flag": "DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER"},
        )
        mock_enabled = False

    google_routes_enabled = real_enabled and google_routes_flag and has_google_key
    google_places_enabled = real_enabled and google_places_flag and has_google_key
    gtfs_transit_enabled = real_enabled and gtfs_transit_flag and has_gtfs_feeds
    navitia_enabled = real_enabled and navitia_flag and _has_navitia_key()

    descriptors: list[ProviderDescriptor] = [
        ProviderDescriptor(
            name="gtfs_transit",
            source_type="open_data",
            base_status="functional_open_data" if gtfs_transit_enabled else "disabled",
            production_ready=False,
            supports_search=True,
            supports_booking_url=False,
            has_tests=True,
            notes=(
                "Horarios reales desde feeds GTFS/open data; sujeto a cobertura del feed."
                if gtfs_transit_enabled
                else (
                    "Desactivado: faltan feeds configurados."
                    if real_enabled and gtfs_transit_flag and not has_gtfs_feeds
                    else "Desactivado: requiere DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS, DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT y DOOR_TO_DOOR_GTFS_FEEDS_JSON."
                )
            ),
            is_real=True,
            factory=GtfsTransitProvider,
        ),
        ProviderDescriptor(
            name="google_maps_deeplink",
            source_type="maps",
            base_status="functional_maps",
            production_ready=True,
            supports_search=True,
            supports_booking_url=True,
            has_tests=False,
            notes=(
                "Genera enlaces de navegacion real en Google Maps sin API key. Siempre activo."
            ),
            is_real=True,
            is_keyless=True,
            factory=GoogleMapsDeepLinkProvider,
        ),
        ProviderDescriptor(
            name="mock_multimodal",
            source_type="estimate",
            base_status="functional_estimate",
            production_ready=False,
            supports_search=True,
            supports_booking_url=False,
            has_tests=True,
            notes=(
                "Provider de estimacion orientativa. Solo se activa como fallback; nunca como recomendacion principal."
                if not _is_non_local_env() or not mock_flag_original
                else "Bloqueado: mock no permitido en APP_ENV=" + os.getenv("APP_ENV", "local").strip().lower() + ". Usa local_demo en entorno local."
            ),
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
            production_ready=False,
            supports_search=True,
            supports_booking_url=True,
            has_tests=True,
            notes="Deeplink clasico para tramo origen -> aeropuerto de salida con compatibilidad contractual. Siempre activo.",
            is_real=True,
            is_keyless=True,
            factory=BlaBlaCarDeepLinkProvider,
        ),
        ProviderDescriptor(
            name="goopti_deeplink",
            source_type="deeplink",
            base_status="functional_deeplink",
            production_ready=False,
            supports_search=True,
            supports_booking_url=True,
            has_tests=True,
            notes="Deeplink clasico para tramo aeropuerto de llegada -> destino final. Siempre activo.",
            is_real=True,
            is_keyless=True,
            factory=GoOptiDeepLinkProvider,
        ),
        ProviderDescriptor(
            name="external_deeplink",
            source_type="external_deeplink",
            base_status="functional_deeplink",
            production_ready=False,
            supports_search=True,
            supports_booking_url=True,
            has_tests=True,
            notes="Provider unificado que genera acciones reales por tramo terrestre (Google Maps, BlaBlaCar, GoOpti). Siempre activo.",
            is_real=True,
            is_keyless=True,
            factory=DeeplinkDoorToDoorProvider,
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
            base_status="functional_api" if navitia_enabled else "disabled",
            production_ready=False,
            supports_search=True,
            supports_booking_url=False,
            has_tests=True,
            notes=(
                "Horarios reales de transporte publico via Navitia API (cobertura ES/IT)."
                if navitia_enabled
                else (
                    "Desactivado: falta NAVITIA_API_KEY."
                    if real_enabled and navitia_flag and not _has_navitia_key()
                    else "Desactivado: requiere DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS, DOOR_TO_DOOR_ENABLE_NAVITIA y NAVITIA_API_KEY."
                )
            ),
            is_real=True,
            factory=NavitiaProvider,
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
        # Key-less deeplink providers are unconditionally enabled — see is_keyless on
        # ProviderDescriptor. They construct real external URLs without any secret or
        # network call, so they are the user's guaranteed "real out" action.
        if descriptor.is_keyless:
            enabled = True
            status = descriptor.base_status
        elif descriptor.is_mock:
            enabled = mock_enabled
            status = descriptor.base_status if enabled else "disabled"
        elif descriptor.name == "google_routes" or descriptor.name == "gtfs_transit" or descriptor.name == "navitia":
            enabled = (
                google_routes_enabled
                if descriptor.name == "google_routes"
                else gtfs_transit_enabled if descriptor.name == "gtfs_transit"
                else navitia_enabled
            )
            if descriptor.name == "google_routes":
                status = "functional_api" if enabled else "disabled"
            elif descriptor.name == "navitia":
                status = "functional_api" if enabled else "disabled"
            else:
                status = "functional_open_data" if enabled else "disabled"
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
    nominatim_provider = NominatimSuggestionsProvider()
    if not nominatim_provider.enabled:
        nominatim_provider = None

    return ProviderRuntime(
        providers=providers,
        statuses=statuses,
        mock_enabled=mock_enabled,
        real_enabled=real_enabled,
        scrapers_enabled=scrapers_enabled,
        google_places_provider=google_places_provider,
        nominatim_provider=nominatim_provider,
    )
