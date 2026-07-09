from app.infrastructure.providers.registry import FlightProviderRegistry


def test_registry_defaults_to_ryanair_and_vueling_only(monkeypatch):
    monkeypatch.delenv("FLIGHT_PROVIDER_ORDER", raising=False)
    monkeypatch.delenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", raising=False)
    monkeypatch.delenv("FLIGHT_PROVIDER_VUELING_ENABLED", raising=False)
    monkeypatch.delenv("FLIGHT_PROVIDER_WIZZAIR_ENABLED", raising=False)
    monkeypatch.delenv("FLIGHT_PROVIDER_EASYJET_ENABLED", raising=False)
    monkeypatch.delenv("FLIGHT_PROVIDER_IBERIA_ENABLED", raising=False)
    monkeypatch.delenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", raising=False)

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["ryanair", "vueling"]


def test_registry_keeps_non_core_providers_disabled_unless_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,vueling,wizzair,easyjet,iberia,duffel")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_VUELING_ENABLED", "true")
    monkeypatch.delenv("FLIGHT_PROVIDER_WIZZAIR_ENABLED", raising=False)
    monkeypatch.delenv("FLIGHT_PROVIDER_EASYJET_ENABLED", raising=False)
    monkeypatch.delenv("FLIGHT_PROVIDER_IBERIA_ENABLED", raising=False)
    monkeypatch.delenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", raising=False)

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["ryanair", "vueling"]


def test_registry_ignores_stale_non_core_provider_flags_without_global_opt_in(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,vueling,wizzair,easyjet,iberia,duffel")
    monkeypatch.delenv("FLIGHT_PROVIDER_NON_CORE_ENABLED", raising=False)
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_VUELING_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_WIZZAIR_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_EASYJET_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_IBERIA_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", "true")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["ryanair", "vueling"]


def test_registry_respects_provider_order_from_env(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "duffel,ryanair")
    monkeypatch.setenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "true")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["ryanair"]


def test_registry_registers_wizzair_when_enabled_and_ordered(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,wizzair")
    monkeypatch.setenv("FLIGHT_PROVIDER_NON_CORE_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_WIZZAIR_ENABLED", "true")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["ryanair", "wizzair"]


def test_registry_accepts_wizz_air_order_aliases(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,wizz_air,wizz-air,wizz air,wizz")
    monkeypatch.setenv("FLIGHT_PROVIDER_NON_CORE_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_WIZZ_AIR_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_DUFFEL_ENABLED", "false")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["wizzair"]


def test_registry_respects_wizz_air_enabled_alias(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "wizz_air")
    monkeypatch.setenv("FLIGHT_PROVIDER_NON_CORE_ENABLED", "true")
    monkeypatch.delenv("FLIGHT_PROVIDER_WIZZAIR_ENABLED", raising=False)
    monkeypatch.setenv("FLIGHT_PROVIDER_WIZZ_AIR_ENABLED", "false")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert providers == []


def test_registry_registers_vueling_without_api_credentials(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,vy,vueling")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_VUELING_ENABLED", "true")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["vueling"]


def test_registry_registers_easyjet_without_api_credentials(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,easyjet,easy_jet,easy-jet,ezy,ezj,u2")
    monkeypatch.setenv("FLIGHT_PROVIDER_NON_CORE_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_EASYJET_ENABLED", "true")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["easyjet"]


def test_registry_registers_iberia_without_api_credentials(monkeypatch):
    monkeypatch.setenv("FLIGHT_PROVIDER_ORDER", "ryanair,iberia,ib,iberia-ndc")
    monkeypatch.setenv("FLIGHT_PROVIDER_NON_CORE_ENABLED", "true")
    monkeypatch.setenv("FLIGHT_PROVIDER_RYANAIR_ENABLED", "false")
    monkeypatch.setenv("FLIGHT_PROVIDER_IBERIA_ENABLED", "true")

    registry = FlightProviderRegistry()
    providers = registry.resolve_enabled_providers()

    assert [provider.provider_id for provider in providers] == ["iberia"]
