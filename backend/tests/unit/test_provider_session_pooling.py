from app.infrastructure.providers.duffel_provider import DuffelProvider
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider


def test_ryanair_provider_uses_expanded_http_pool() -> None:
    provider = RyanairPublicProvider()

    https_adapter = provider._session.adapters["https://"]
    assert https_adapter._pool_connections == 32
    assert https_adapter._pool_maxsize == 32


def test_duffel_provider_uses_expanded_http_pool() -> None:
    provider = DuffelProvider(api_key="test-key")

    https_adapter = provider._session.adapters["https://"]
    assert https_adapter._pool_connections == 32
    assert https_adapter._pool_maxsize == 32
