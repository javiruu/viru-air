import importlib


def test_global_disable_turns_off_all_runtime_fare_memory_features(monkeypatch) -> None:
    monkeypatch.setenv("FARE_MEMORY_ENABLED", "false")
    monkeypatch.setenv("FARE_MEMORY_SEARCH_CACHE_ENABLED", "true")
    monkeypatch.setenv("FARE_MEMORY_OFFER_CACHE_ENABLED", "true")
    monkeypatch.setenv("FARE_MEMORY_NEGATIVE_CACHE_ENABLED", "true")

    module = importlib.import_module("app.services.fare_memory_config")
    module = importlib.reload(module)

    assert module.FARE_MEMORY_ENABLED is False
    assert module.FARE_MEMORY_SEARCH_CACHE_ENABLED is False
    assert module.FARE_MEMORY_OFFER_CACHE_ENABLED is False
    assert module.FARE_MEMORY_NEGATIVE_CACHE_ENABLED is False


def test_fare_memory_boot_defaults_are_safe(monkeypatch) -> None:
    monkeypatch.delenv("FARE_MEMORY_ENABLED", raising=False)
    monkeypatch.delenv("FARE_MEMORY_BOOT_WARMUP_ENABLED", raising=False)
    monkeypatch.delenv("FARE_MEMORY_MAX_BOOT_JOBS", raising=False)
    monkeypatch.delenv("FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE", raising=False)

    module = importlib.import_module("app.services.fare_memory_config")
    module = importlib.reload(module)

    assert module.FARE_MEMORY_ENABLED is True
    assert module.FARE_MEMORY_BOOT_WARMUP_ENABLED is False
    assert module.FARE_MEMORY_MAX_BOOT_JOBS == 25
    assert module.FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE == 60
