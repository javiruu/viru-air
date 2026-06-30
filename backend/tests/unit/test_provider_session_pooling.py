import pytest
import requests as std_requests

from app.infrastructure.providers.duffel_provider import DuffelProvider
from app.infrastructure.providers import ryanair_public_provider
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider


def test_ryanair_provider_uses_expanded_http_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_session(*args, **kwargs):
        if "impersonate" in kwargs:
            raise TypeError("standard requests fallback")
        return std_requests.Session()

    monkeypatch.setattr(ryanair_public_provider.requests, "Session", fake_session)
    provider = RyanairPublicProvider()

    https_adapter = provider._session.adapters["https://"]
    assert https_adapter._pool_connections == 32
    assert https_adapter._pool_maxsize == 32


def test_duffel_provider_uses_expanded_http_pool() -> None:
    provider = DuffelProvider(api_key="test-key")

    https_adapter = provider._session.adapters["https://"]
    assert https_adapter._pool_connections == 32
    assert https_adapter._pool_maxsize == 32
