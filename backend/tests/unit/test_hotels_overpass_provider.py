from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.hotels.activation import resolve_hotel_activation
from app.hotels.ingestion import HotelIngestionBudgetDeniedError, HotelIngestionService, resolve_hotel_provider
from app.hotels.overpass_provider import (
    OverpassCatalogConfig,
    OverpassConfigurationError,
    OverpassHotelProviderAdapter,
    OverpassRequestError,
)
from app.infrastructure.db.models import Base
from app.services.hotel_provider_latency import ProviderLatencySample
from app.services.hotels_service import run_hotel_sweep


@dataclass
class FakeOverpassTransport:
    response: bytes
    queries: list[str] = field(default_factory=list)
    user_agents: list[str] = field(default_factory=list)

    def fetch(self, *, query: str, user_agent: str) -> bytes:
        self.queries.append(query)
        self.user_agents.append(user_agent)
        return self.response


def test_overpass_catalog_maps_hotels_without_inventing_rates() -> None:
    transport = FakeOverpassTransport(
        response=b'''{
          "elements": [
            {
              "type": "node",
              "id": 184049280,
              "lat": 40.4161,
              "lon": -3.7037,
              "tags": {
                "tourism": "hotel",
                "name": "Hotel Europa",
                "stars": "3",
                "addr:street": "Calle del Carmen",
                "addr:housenumber": "4",
                "website": "https://example.test/hotel?token=must-not-persist"
              }
            },
            {
              "type": "way",
              "id": 123,
              "center": {"lat": 40.417, "lon": -3.704},
              "tags": {"tourism": "hotel", "name": "Hotel Centro"}
            }
          ]
        }'''
    )
    adapter = OverpassHotelProviderAdapter(
        config=OverpassCatalogConfig(
            south=40.414,
            west=-3.706,
            north=40.418,
            east=-3.700,
            city="Madrid",
            country_code="ES",
            user_agent="ViruTracker/0.1 (hotel catalog)",
        ),
        transport=transport,
    )

    hotels = adapter.fetch_hotels()

    assert [(hotel.provider_hotel_id, hotel.raw_name) for hotel in hotels] == [
        ("osm:node:184049280", "Hotel Europa"),
        ("osm:way:123", "Hotel Centro"),
    ]
    assert hotels[0].raw_address == "Calle del Carmen 4"
    assert hotels[0].stars == 3
    assert hotels[0].rates == []
    assert hotels[0].raw_payload == {
        "source": "openstreetmap_overpass",
        "element_id": "184049280",
        "element_type": "node",
        "tourism": "hotel",
    }
    assert "nwr[\"tourism\"=\"hotel\"]" in transport.queries[0]
    assert "out center tags 100;" in transport.queries[0]
    assert transport.user_agents == ["ViruTracker/0.1 (hotel catalog)"]


@pytest.mark.parametrize(
    "response",
    [
        b"{}",
        b'{"remark":"runtime error: Query timed out","elements":[]}',
    ],
)
def test_overpass_rejects_missing_or_error_catalog_responses(response: bytes) -> None:
    adapter = OverpassHotelProviderAdapter(
        config=OverpassCatalogConfig(40.414, -3.706, 40.418, -3.700, "Madrid", "ES", "ViruTracker/0.1"),
        transport=FakeOverpassTransport(response=response),
    )

    with pytest.raises(OverpassRequestError, match="invalid_response"):
        adapter.fetch_hotels()


def test_overpass_ignores_non_ascii_star_digits() -> None:
    transport = FakeOverpassTransport(
        response=b'''{
          "elements": [{
            "type": "node",
            "id": 1,
            "lat": 40.4161,
            "lon": -3.7037,
            "tags": {"tourism": "hotel", "name": "Hotel Seguro", "stars": "\\u00b2"}
          }]
        }'''
    )
    adapter = OverpassHotelProviderAdapter(
        config=OverpassCatalogConfig(40.414, -3.706, 40.418, -3.700, "Madrid", "ES", "ViruTracker/0.1"),
        transport=transport,
    )

    hotels = adapter.fetch_hotels()

    assert len(hotels) == 1
    assert hotels[0].stars is None


@pytest.mark.parametrize(
    ("raw_bbox", "expected_error"),
    [
        ("40.414,-3.706,40.414,-3.700", "hotel_overpass_bbox_invalid"),
        ("40.0,-3.9,40.2,-3.7", "hotel_overpass_bbox_too_large"),
        ("40.414,-3.706,40.418", "hotel_overpass_bbox_invalid"),
    ],
)
def test_overpass_configuration_rejects_invalid_or_wide_area(
    monkeypatch: pytest.MonkeyPatch,
    raw_bbox: str,
    expected_error: str,
) -> None:
    monkeypatch.setenv("HOTEL_OVERPASS_BBOX", raw_bbox)
    monkeypatch.setenv("HOTEL_OVERPASS_CITY", "Madrid")
    monkeypatch.setenv("HOTEL_OVERPASS_COUNTRY_CODE", "ES")
    monkeypatch.setenv("HOTEL_OVERPASS_USER_AGENT", "ViruTracker/0.1 (hotel catalog)")

    with pytest.raises(OverpassConfigurationError, match=expected_error):
        OverpassHotelProviderAdapter.from_environment()


def test_overpass_capabilities_are_catalog_only() -> None:
    adapter = OverpassHotelProviderAdapter(
        config=OverpassCatalogConfig(
            south=40.414,
            west=-3.706,
            north=40.418,
            east=-3.700,
            city="Madrid",
            country_code="ES",
            user_agent="ViruTracker/0.1 (hotel catalog)",
        ),
        transport=FakeOverpassTransport(response=b'{"elements": []}'),
    )

    capabilities = adapter.capabilities()

    assert capabilities.supports_catalog is True
    assert capabilities.supports_area_search is False
    assert capabilities.supports_hotel_rates is False
    assert capabilities.supports_total_fees is False
    assert capabilities.supports_direct_revalidation is False
    assert adapter.fetch_hotel_rates(
        "osm:node:184049280", date(2026, 9, 10), date(2026, 9, 12)
    ) == []


def test_overpass_activation_requires_explicit_external_enablement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.delenv("HOTEL_PROVIDER_OSM_OVERPASS_ENABLED", raising=False)

    decision = resolve_hotel_activation(operation="ingestion", provider="osm_overpass")

    assert decision.enabled is False
    assert decision.reason_code == "provider_not_explicitly_enabled"


def test_overpass_provider_resolves_after_explicit_canary_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_OSM_OVERPASS_ENABLED", "true")
    monkeypatch.setenv("HOTEL_OVERPASS_BBOX", "40.414,-3.706,40.418,-3.700")
    monkeypatch.setenv("HOTEL_OVERPASS_CITY", "Madrid")
    monkeypatch.setenv("HOTEL_OVERPASS_COUNTRY_CODE", "ES")
    monkeypatch.setenv("HOTEL_OVERPASS_USER_AGENT", "ViruTracker/0.1 (hotel catalog)")

    provider = resolve_hotel_provider(provider="osm_overpass")

    assert provider.provider_id == "osm_overpass"


def test_overpass_default_budget_blocks_catalog_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_OSM_OVERPASS_ENABLED", "true")
    monkeypatch.delenv("HOTEL_PROVIDER_OSM_OVERPASS_DAILY_REQUEST_BUDGET", raising=False)
    transport = FakeOverpassTransport(response=b'{"elements": []}')
    adapter = OverpassHotelProviderAdapter(
        config=OverpassCatalogConfig(
            south=40.414,
            west=-3.706,
            north=40.418,
            east=-3.700,
            city="Madrid",
            country_code="ES",
            user_agent="ViruTracker/0.1 (hotel catalog)",
        ),
        transport=transport,
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        with pytest.raises(HotelIngestionBudgetDeniedError, match="osm_overpass"):
            HotelIngestionService(db, provider=adapter).ingest()
        assert transport.queries == []
    finally:
        db.close()
        engine.dispose()


def test_overpass_request_error_survives_context_manager_traceback_assignment() -> None:
    @contextmanager
    def response_context() -> Iterator[None]:
        yield

    with pytest.raises(OverpassRequestError, match="rate_limited"):
        with response_context():
            raise OverpassRequestError("rate_limited")


def test_overpass_discards_hostile_text_fields_without_persisting_them() -> None:
    transport = FakeOverpassTransport(
        response=b'''{
          "elements": [
            {
              "type": "node",
              "id": 1,
              "lat": 40.4161,
              "lon": -3.7037,
              "tags": {
                "tourism": "hotel",
                "name": "Hotel Seguro",
                "addr:street": "https://example.test/?token=must-not-persist",
                "addr:housenumber": "1"
              }
            },
            {
              "type": "node",
              "id": 2,
              "lat": 40.4161,
              "lon": -3.7037,
              "tags": {"tourism": "hotel", "name": "''' + b'x' * 161 + b'''"}
            }
          ]
        }'''
    )
    adapter = OverpassHotelProviderAdapter(
        config=OverpassCatalogConfig(40.414, -3.706, 40.418, -3.700, "Madrid", "ES", "ViruTracker/0.1"),
        transport=transport,
    )

    hotels = adapter.fetch_hotels()

    assert len(hotels) == 1
    assert hotels[0].raw_name == "Hotel Seguro"
    assert hotels[0].raw_address == "1"
    assert "token" not in repr(hotels[0])


def test_overpass_sweep_is_denied_before_catalog_or_tracking_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_OSM_OVERPASS_ENABLED", "true")
    decision = resolve_hotel_activation(operation="sweep", provider="osm_overpass")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        provider_run = run_hotel_sweep(db, provider="osm_overpass")

        assert decision.enabled is False
        assert decision.reason_code == "provider_operation_unsupported"
        assert provider_run.status == "failed"
        assert provider_run.items_processed == 0
        assert provider_run.error_message == (
            "The selected hotel provider supports catalog ingestion only. Hotel sweeps are disabled."
        )
    finally:
        db.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("error_code", "expected_outcome"),
    [
        ("rate_limited", "rate_limited"),
        ("timeout", "timeout"),
        ("invalid_response", "invalid_response"),
        ("provider_unavailable", "unavailable"),
    ],
)
def test_overpass_error_taxonomy_reaches_ingestion_measurement(
    monkeypatch: pytest.MonkeyPatch,
    error_code: Literal["rate_limited", "timeout", "invalid_response", "provider_unavailable"],
    expected_outcome: str,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_OSM_OVERPASS_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_OSM_OVERPASS_DAILY_REQUEST_BUDGET", "1")

    class FailingTransport:
        def fetch(self, *, query: str, user_agent: str) -> bytes:
            raise OverpassRequestError(error_code)

    adapter = OverpassHotelProviderAdapter(
        config=OverpassCatalogConfig(40.414, -3.706, 40.418, -3.700, "Madrid", "ES", "ViruTracker/0.1"),
        transport=FailingTransport(),
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    samples: list[ProviderLatencySample] = []
    try:
        with pytest.raises(OverpassRequestError, match=error_code):
            HotelIngestionService(db, provider=adapter, latency_sink=samples.append).ingest()
        assert len(samples) == 1
        assert samples[0].outcome == expected_outcome
        assert samples[0].error_code == error_code
    finally:
        db.close()
        engine.dispose()
