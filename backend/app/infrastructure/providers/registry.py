from __future__ import annotations

import os

from app.infrastructure.providers.base import FlightProvider
from app.infrastructure.providers.duffel_provider import DuffelProvider
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider
from app.infrastructure.providers.wizz_air_provider import WizzAirProvider


def _env_enabled(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class FlightProviderRegistry:
    def __init__(self) -> None:
        self._provider_factories: dict[str, callable] = {
            "ryanair": RyanairPublicProvider,
            "wizzair": WizzAirProvider,
            "duffel": DuffelProvider,
        }

    def resolve_enabled_providers(self) -> list[FlightProvider]:
        ordered = [
            item.strip().lower()
            for item in os.getenv("FLIGHT_PROVIDER_ORDER", "ryanair,wizzair,duffel").split(",")
            if item.strip()
        ]
        providers: list[FlightProvider] = []
        for provider_id in ordered:
            factory = self._provider_factories.get(provider_id)
            if factory is None:
                continue
            flag_name = f"FLIGHT_PROVIDER_{provider_id.upper()}_ENABLED"
            if not _env_enabled(flag_name, default=True):
                continue
            provider = factory()
            if provider.is_enabled():
                providers.append(provider)
        return providers
