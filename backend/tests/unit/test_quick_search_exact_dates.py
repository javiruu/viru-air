from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.api.v1.search import _normalize_quick_search_request


def _canonical_payload(travel: dict[str, object]) -> dict[str, object]:
    return {
        "origin": {"seed_iata": "MAD"},
        "destination": {"seed_iata": "DUB"},
        "travel": travel,
    }


def test_exact_travel_dates_are_sorted_and_preserved() -> None:
    first = date.today() + timedelta(days=20)
    second = date.today() + timedelta(days=27)

    canonical, _, _, _ = _normalize_quick_search_request(
        _canonical_payload({"date": str(second), "dates": [str(second), str(first)]}),
        {},
    )

    assert canonical.travel.flex_before == 0
    assert canonical.travel.flex_after == 0
    assert canonical.travel.dates == [first, second]


def test_exact_travel_dates_reject_flexibility() -> None:
    selected_date = date.today() + timedelta(days=20)

    with pytest.raises(HTTPException) as exc_info:
        _normalize_quick_search_request(
            _canonical_payload({"date": str(selected_date), "dates": [str(selected_date)], "flex_before": 1}),
            {},
        )

    assert exc_info.value.status_code == 422


def test_flat_travel_dates_use_the_same_exact_dates_contract() -> None:
    first = date.today() + timedelta(days=20)
    second = date.today() + timedelta(days=27)

    canonical, _, _, _ = _normalize_quick_search_request(
        {
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date": str(first),
            "travel_dates": [str(second), str(first)],
        },
        {},
    )

    assert canonical.travel.dates == [first, second]
