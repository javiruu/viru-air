from __future__ import annotations

import os

from sqlalchemy.orm import Session

from app.infrastructure.providers.adsb_exchange_operational_provider import (
    AdsbExchangeOperationalFlightProvider,
)
from app.infrastructure.providers.aerodatabox_operational_provider import (
    AeroDataBoxOperationalFlightProvider,
)
from app.infrastructure.providers.amadeus_operational_provider import (
    AmadeusOperationalFlightProvider,
)
from app.infrastructure.providers.aviationstack_operational_provider import (
    AviationstackOperationalFlightProvider,
)
from app.infrastructure.providers.flightaware_operational_provider import (
    FlightAwareOperationalFlightProvider,
)
from app.infrastructure.providers.multi_provider_operational_provider import (
    OperationalProviderRegistration,
    ProviderCapability,
    QuotaAwareOperationalFlightProvider,
)
from app.infrastructure.providers.opensky_operational_provider import (
    OpenSkyOperationalFlightProvider,
)
from app.infrastructure.providers.operational_flight_provider import (
    OperationalFlightProvider,
    OperationalNotConfigured,
)
from app.services.live_flight_provider_quota import (
    ProviderBudgetPolicy,
    QuotaWindow,
    SqlAlchemyProviderQuotaLedger,
)


def build_operational_provider(
    db: Session,
) -> QuotaAwareOperationalFlightProvider | OperationalNotConfigured:
    zero_cost_only = _bool_env("LIVE_FLIGHT_ZERO_COST_ONLY", True)
    allow_paid = _bool_env("LIVE_FLIGHT_ALLOW_PAID_PROVIDERS", False)
    billable_enabled = not zero_cost_only and allow_paid
    registrations = _free_registrations(allow_billable=billable_enabled)
    if billable_enabled:
        registrations.extend(_paid_registrations())
    if not registrations:
        return OperationalNotConfigured()
    return QuotaAwareOperationalFlightProvider(
        registrations,
        SqlAlchemyProviderQuotaLedger(db.get_bind()),
    )


def _free_registrations(*, allow_billable: bool) -> list[OperationalProviderRegistration]:
    timeout = _timeout()
    registrations: list[OperationalProviderRegistration] = []
    amadeus_id = os.getenv("AMADEUS_CLIENT_ID", "").strip()
    amadeus_secret = os.getenv("AMADEUS_CLIENT_SECRET", "").strip()
    amadeus_environment = os.getenv("AMADEUS_ENV", "test").strip().lower()
    amadeus_limit = _int_env(
        "AMADEUS_MONTHLY_REQUEST_LIMIT",
        1_000 if amadeus_environment == "test" else 0,
    )
    if (
        amadeus_id
        and amadeus_secret
        and amadeus_limit > 0
        and (amadeus_environment == "test" or allow_billable)
    ):
        default_url = (
            "https://test.api.amadeus.com"
            if amadeus_environment == "test"
            else "https://api.amadeus.com"
        )
        registrations.append(
            _registration(
                "amadeus",
                AmadeusOperationalFlightProvider(
                    amadeus_id,
                    amadeus_secret,
                    os.getenv("AMADEUS_BASE_URL", default_url),
                    timeout,
                ),
                {"status_schedule"},
                "month",
                amadeus_limit,
                1,
            )
        )
    aviationstack_key = os.getenv("AVIATIONSTACK_API_KEY", "").strip()
    if aviationstack_key:
        registrations.append(
            _registration(
                "aviationstack",
                AviationstackOperationalFlightProvider(
                    aviationstack_key,
                    os.getenv("AVIATIONSTACK_BASE_URL", "https://api.aviationstack.com/v1"),
                    timeout,
                ),
                {"status_schedule", "position"},
                "month",
                _int_env("AVIATIONSTACK_MONTHLY_REQUEST_LIMIT", 90),
                1,
            )
        )
    aerodatabox_key = os.getenv("AERODATABOX_API_KEY", "").strip()
    if aerodatabox_key:
        registrations.append(
            _registration(
                "aerodatabox",
                AeroDataBoxOperationalFlightProvider(
                    aerodatabox_key,
                    os.getenv("AERODATABOX_BASE_URL", "https://aerodatabox.p.rapidapi.com"),
                    os.getenv("AERODATABOX_HOST", "aerodatabox.p.rapidapi.com"),
                    timeout,
                ),
                {"status_schedule", "position"},
                "month",
                _int_env("AERODATABOX_MONTHLY_UNIT_LIMIT", 540),
                2,
            )
        )
    if (
        _bool_env("LIVE_FLIGHT_OPENSKY_ANONYMOUS", True)
        or os.getenv("OPENSKY_USERNAME", "").strip()
    ):
        registrations.append(
            _registration(
                "opensky",
                OpenSkyOperationalFlightProvider(
                    os.getenv("OPENSKY_BASE_URL", "https://opensky-network.org/api"),
                    timeout,
                    os.getenv("OPENSKY_USERNAME", "").strip() or None,
                    os.getenv("OPENSKY_PASSWORD", "").strip() or None,
                ),
                {"position"},
                "day",
                _int_env("OPENSKY_DAILY_CREDIT_LIMIT", 360),
                4,
            )
        )
    return registrations


def _paid_registrations() -> list[OperationalProviderRegistration]:
    timeout = _timeout()
    registrations: list[OperationalProviderRegistration] = []
    flightaware_key = os.getenv("FLIGHTAWARE_API_KEY", "").strip()
    flightaware_limit = _int_env("FLIGHTAWARE_MONTHLY_REQUEST_LIMIT", 0)
    if flightaware_key and flightaware_limit > 0:
        registrations.append(
            _registration(
                "flightaware",
                FlightAwareOperationalFlightProvider(
                    flightaware_key,
                    os.getenv("FLIGHTAWARE_BASE_URL", "https://aeroapi.flightaware.com/aeroapi"),
                    timeout,
                ),
                {"status_schedule", "position"},
                "month",
                flightaware_limit,
                1,
            )
        )
    adsb_key = os.getenv("ADSB_EXCHANGE_API_KEY", "").strip()
    adsb_limit = _int_env("ADSB_EXCHANGE_MONTHLY_REQUEST_LIMIT", 0)
    if adsb_key and adsb_limit > 0:
        registrations.append(
            _registration(
                "adsb_exchange",
                AdsbExchangeOperationalFlightProvider(
                    adsb_key,
                    os.getenv(
                        "ADSB_EXCHANGE_BASE_URL", "https://api.adsbexchange.com/api/aircraft/v2"
                    ),
                    timeout,
                    os.getenv("ADSB_EXCHANGE_API_HEADER", "api-auth"),
                ),
                {"position"},
                "month",
                adsb_limit,
                1,
            )
        )
    return registrations


def _registration(
    name: str,
    provider: OperationalFlightProvider,
    capabilities: set[ProviderCapability],
    window: QuotaWindow,
    hard_limit: int,
    units_per_request: int,
) -> OperationalProviderRegistration:
    return OperationalProviderRegistration(
        name=name,
        provider=provider,
        capabilities=frozenset(capabilities),
        budget=ProviderBudgetPolicy(name, window, max(0, hard_limit), units_per_request),
    )


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _timeout() -> float:
    try:
        return max(1.0, min(20.0, float(os.getenv("LIVE_FLIGHT_PROVIDER_TIMEOUT_SECONDS", "8"))))
    except ValueError:
        return 8.0
