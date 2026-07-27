import json

from app.infrastructure.providers.multi_provider_operational_provider import (
    QuotaAwareOperationalFlightProvider,
)
from app.infrastructure.providers.operational_provider_registry import build_operational_provider
from app.infrastructure.providers.operational_flight_provider import OperationalNotConfigured


class _Db:
    def get_bind(self):
        return None


def test_zero_cost_mode_never_registers_paid_providers(monkeypatch) -> None:
    monkeypatch.setenv("LIVE_FLIGHT_ZERO_COST_ONLY", "true")
    monkeypatch.setenv("LIVE_FLIGHT_ALLOW_PAID_PROVIDERS", "true")
    monkeypatch.setenv("FLIGHTAWARE_API_KEY", "secret")
    monkeypatch.setenv("ADSB_EXCHANGE_API_KEY", "secret")
    monkeypatch.setenv("AVIATIONSTACK_API_KEY", "free-secret")

    provider = build_operational_provider(_Db())

    assert isinstance(provider, QuotaAwareOperationalFlightProvider)
    names = [item.name for item in provider.registrations]
    assert names == ["aviationstack", "opensky"]
    assert "flightaware" not in names
    assert "adsb_exchange" not in names


def test_no_credentials_and_anonymous_opensky_still_builds_free_chain(monkeypatch) -> None:
    for key in (
        "AMADEUS_CLIENT_ID",
        "AMADEUS_CLIENT_SECRET",
        "AVIATIONSTACK_API_KEY",
        "AERODATABOX_API_KEY",
        "FLIGHTAWARE_API_KEY",
        "ADSB_EXCHANGE_API_KEY",
        "OPENSKY_CLIENT_ID",
        "OPENSKY_CLIENT_SECRET",
        "OPENSKY_CREDENTIALS_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LIVE_FLIGHT_OPENSKY_ANONYMOUS", "true")

    provider = build_operational_provider(_Db())

    assert not isinstance(provider, OperationalNotConfigured)
    assert [item.name for item in provider.registrations] == ["opensky"]


def test_zero_cost_mode_blocks_amadeus_production_even_with_paid_flag(monkeypatch) -> None:
    monkeypatch.setenv("LIVE_FLIGHT_ZERO_COST_ONLY", "true")
    monkeypatch.setenv("LIVE_FLIGHT_ALLOW_PAID_PROVIDERS", "true")
    monkeypatch.setenv("AMADEUS_CLIENT_ID", "client")
    monkeypatch.setenv("AMADEUS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("AMADEUS_ENV", "production")
    monkeypatch.setenv("AMADEUS_MONTHLY_REQUEST_LIMIT", "100")
    monkeypatch.setenv("LIVE_FLIGHT_OPENSKY_ANONYMOUS", "false")

    provider = build_operational_provider(_Db())

    assert isinstance(provider, OperationalNotConfigured)


def test_opensky_loads_oauth_credentials_file(monkeypatch, tmp_path) -> None:
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text(
        json.dumps({"clientId": "viru-api-client", "clientSecret": "secret"}),
        encoding="utf-8",
    )
    for key in (
        "AMADEUS_CLIENT_ID",
        "AMADEUS_CLIENT_SECRET",
        "AVIATIONSTACK_API_KEY",
        "AERODATABOX_API_KEY",
        "FLIGHTAWARE_API_KEY",
        "ADSB_EXCHANGE_API_KEY",
        "OPENSKY_CLIENT_ID",
        "OPENSKY_CLIENT_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LIVE_FLIGHT_OPENSKY_ANONYMOUS", "false")
    monkeypatch.setenv("OPENSKY_CREDENTIALS_FILE", str(credentials_path))

    provider = build_operational_provider(_Db())

    assert isinstance(provider, QuotaAwareOperationalFlightProvider)
    assert [item.name for item in provider.registrations] == ["opensky"]
    opensky = provider.registrations[0].provider
    assert opensky._client_id == "viru-api-client"
    assert opensky._client_secret == "secret"
