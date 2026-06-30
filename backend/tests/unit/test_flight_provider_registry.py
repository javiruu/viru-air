from app.infrastructure.providers.registry import FlightProviderRegistry


def test_registry_respects_provider_order_from_env(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "duffel,ryanair")
    monkeypatch.setenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "true")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["ryanair"]


def test_registry_registers_wizzair_when_enabled_and_ordered(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,wizzair")
    monkeypatch.setenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_WIZZAIR_ENABLED", "true")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["ryanair", "wizzair"]


def test_registry_accepts_wizz_air_order_aliases(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,wizz_air,wizz-air,wizz air,wizz")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_WIZZ_AIR_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", "false")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["wizzair"]


def test_registry_respects_wizz_air_enabled_alias(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "wizz_air")
    monkeypatch.delenv("FLIGHT_PROVIDER_WIZZAIR_ENABLED", raising=False)
    monkeypatch.setenv("FLIGHT_PROVIDER_WIZZ_AIR_ENABLED", "false")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert providers == []


def test_registry_registers_vueling_when_configured(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,vy,vueling")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_VUELING_ENABLED", "true")
    monkeypatch.setenv("VUELING_FLIGHTCALENDAR_TOKEN", "token")
    monkeypatch.setenv("VUELING_FLIGHTCALENDAR_PRICES_URL", "https://example.test/prices")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["vueling"]
