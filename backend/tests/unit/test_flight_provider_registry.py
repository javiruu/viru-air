from app.infrastructure.providers.registry import FlightProviderRegistry


def test_registry_respects_provider_order_from_env(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "duffel,ryanair")
    monkeypatch.setenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "true")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["ryanair"]

