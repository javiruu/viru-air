from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.search import quick_search
from app.core.errors import ApiError
from app.main import app


class _ProviderNotUsedWhenAliasesAreBlocked:
    def provider_ids(self) -> list[str]:
        return ["test-provider"]


def test_quick_search_canary_blocks_legacy_aliases_before_provider_execution(monkeypatch) -> None:
    monkeypatch.setenv("QUICK_SEARCH_LEGACY_ALIASES_MODE", "block")

    with patch("app.api.v1.search._build_request_provider", return_value=_ProviderNotUsedWhenAliasesAreBlocked()):
        with pytest.raises(ApiError) as error:
            quick_search(
                payload={
                    "origin_iata": "LEI",
                    "destination_iata": "DUB",
                    "travel_date": "2026-06-14",
                },
                origin_iata=None,
                destination_iata=None,
                travel_date=None,
                radius_km=None,
                include_stops=None,
                include_nearby_origins=None,
                include_nearby_destinations=None,
                depart_after=None,
                depart_before=None,
                max_stops=None,
                exclude_origins=None,
                exclude_destinations=None,
                strict_filters=None,
                soft_filters_weight=None,
                flex_days_before=None,
                flex_days_after=None,
                page=None,
                page_size=None,
                sort_by=None,
                debug=False,
                db=None,
            )

    assert error.value.status == 400
    assert error.value.code == "quick_search_legacy_aliases_blocked"
    assert error.value.details == [
        {
            "aliases": ["payload.flat"],
            "contract_version": "quick_search.v2",
        }
    ]


def test_quick_search_canary_returns_the_documented_http_error(monkeypatch) -> None:
    monkeypatch.setenv("QUICK_SEARCH_LEGACY_ALIASES_MODE", "block")

    response = TestClient(app).post(
        "/api/v1/search/quick",
        json={
            "origin_iata": "LEI",
            "destination_iata": "DUB",
            "travel_date": "2026-06-14",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "quick_search_legacy_aliases_blocked"
