from __future__ import annotations

import os
from collections.abc import Callable

from app.infrastructure.providers.base import FlightProvider
from app.infrastructure.providers.duffel_provider import DuffelProvider
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider
from app.infrastructure.providers.vueling_provider import VuelingProvider
from app.infrastructure.providers.wizz_air_provider import WizzAirProvider


def _env_enabled(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


_PROVIDER_ALIASES = {
    "duffel": "duffel",
    "ryanair": "ryanair",
    "ryan_air": "ryanair",
    "vy": "vueling",
    "vueling": "vueling",
    "wizz": "wizzair",
    "wizzair": "wizzair",
    "wizz_air": "wizzair",
}

_PROVIDER_ENABLED_FLAGS = {
    "duffel": ("FLIGHT_PROVIDER_DUFFEL_ENABLED",),
    "ryanair": ("FLIGHT_PROVIDER_RYANAIR_ENABLED", "FLIGHT_PROVIDER_RYAN_AIR_ENABLED"),
    "vueling": ("FLIGHT_PROVIDER_VUELING_ENABLED", "FLIGHT_PROVIDER_VY_ENABLED"),
    "wizzair": (
        "FLIGHT_PROVIDER_WIZZAIR_ENABLED",
        "FLIGHT_PROVIDER_WIZZ_AIR_ENABLED",
        "FLIGHT_PROVIDER_WIZZ_ENABLED",
    ),
}


def _normalize_provider_id(value: str) -> str:
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    return _PROVIDER_ALIASES.get(key, key)


def _provider_enabled(provider_id: str) -> bool:
    for flag_name in _PROVIDER_ENABLED_FLAGS.get(provider_id, (f"FLIGHT_PROVIDER_{provider_id.upper()}_ENABLED",)):
        if os.getenv(flag_name) is not None:
            return _env_enabled(flag_name, default=True)
    return True


class FlightProviderRegistry:
    def __init__(self) -> None:
        self._provider_factories: dict[str, Callable[[], FlightProvider]] = {
            "ryanair": RyanairPublicProvider,
            "vueling": VuelingProvider,
            "wizzair": WizzAirProvider,
            "duffel": DuffelProvider,
        }

    def resolve_enabled_providers(self) -> list[FlightProvider]:
        ordered = [
            _normalize_provider_id(item)
            for item in os.getenv("FLIGHT_PROVIDER_ORDER", "ryanair,vueling,wizzair,duffel").split(",")
            if item.strip()
        ]
        providers: list[FlightProvider] = []
        seen: set[str] = set()
        for provider_id in ordered:
            if provider_id in seen:
                continue
            seen.add(provider_id)
            factory = self._provider_factories.get(provider_id)
            if factory is None:
                continue
            if not _provider_enabled(provider_id):
                continue
            provider = factory()
            if provider.is_enabled():
                providers.append(provider)
        return providers
