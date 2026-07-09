import datetime as dt

from app.api.v1.search import _normalize_quick_search_request
from app.services.fare_memory import (
    build_offer_fingerprint,
    build_search_fingerprint,
    canonicalize_offer_fingerprint_payload,
    canonicalize_search_fingerprint_payload,
)
from app.services.quick_search_execution import build_cache_source_hash, build_unit_cache_key


def _canonical_request(**payload_overrides):
    payload = {
        "origin": {
            "seed_iata": "lei",
            "include_nearby": False,
            "radius_km": 150,
            "max_candidates": 6,
        },
        "destination": {
            "seed_iata": "fco",
            "include_nearby": True,
            "radius_km": 180,
            "max_candidates": 8,
        },
        "travel": {"date": "2026-07-20", "flex_before": 0, "flex_after": 0},
        "constraints": {"strict_filters": True, "soft_filters_weight": 0.6},
        "execution": {"max_pairs": 24, "max_requests": 120, "timeout_ms": 8000, "concurrency_limit": 6},
        "pagination": {"page": 1, "page_size": 10},
    }
    payload.update(payload_overrides)
    canonical, *_ = _normalize_quick_search_request(payload, {})
    return canonical


def test_search_fingerprint_normalizes_case_and_default_fields() -> None:
    canonical = _canonical_request()
    same = _canonical_request(
        origin={
            "seed_iata": "LEI",
            "include_nearby": False,
            "radius_km": 400,
            "max_candidates": 6,
        },
        destination={
            "seed_iata": "FCO",
            "include_nearby": True,
            "radius_km": 180,
            "max_candidates": 8,
        },
        constraints={
            "strict_filters": True,
            "soft_filters_weight": 0.6,
            "exclude_origins": [],
            "exclude_destinations": [],
        },
    )

    assert build_search_fingerprint(canonical) == build_search_fingerprint(same)


def test_search_fingerprint_changes_when_date_changes() -> None:
    first = _canonical_request()
    second = _canonical_request(travel={"date": "2026-07-21", "flex_before": 0, "flex_after": 0})

    assert build_search_fingerprint(first) != build_search_fingerprint(second)


def test_search_fingerprint_changes_when_nearby_destinations_change() -> None:
    first = _canonical_request()
    second = _canonical_request(
        destination={
            "seed_iata": "FCO",
            "include_nearby": False,
            "radius_km": 180,
            "max_candidates": 8,
        }
    )

    assert build_search_fingerprint(first) != build_search_fingerprint(second)


def test_search_fingerprint_changes_when_provider_set_changes() -> None:
    canonical = _canonical_request()

    assert build_search_fingerprint(canonical, provider_set=["multi"]) != build_search_fingerprint(
        canonical,
        provider_set=["duffel", "ryanair"],
    )


def test_search_fingerprint_ignores_provider_and_seed_pool_order() -> None:
    first = _canonical_request(
        origin={
            "seed_iata": "FCO",
            "seed_iata_list": ["CIA", "FCO", "MXP"],
            "include_nearby": True,
            "radius_km": 180,
            "max_candidates": 6,
        }
    )
    second = _canonical_request(
        origin={
            "seed_iata": "fco",
            "seed_iata_list": ["mxp", "cia", "fco"],
            "include_nearby": True,
            "radius_km": 180,
            "max_candidates": 6,
        }
    )

    assert build_search_fingerprint(first, provider_set=["vueling", "ryanair"]) == build_search_fingerprint(
        second,
        provider_set=["ryanair", "vueling"],
    )


def test_search_fingerprint_ignores_locale_unless_it_affects_data() -> None:
    canonical = _canonical_request()
    base = build_search_fingerprint(canonical, locale="es", locale_affects_data=False)
    same = build_search_fingerprint(canonical, locale="en", locale_affects_data=False)
    changed = build_search_fingerprint(canonical, locale="en", locale_affects_data=True)

    assert base == same
    assert base != changed


def test_search_payload_normalization_sorts_seed_pools() -> None:
    canonical = _canonical_request(
        origin={
            "seed_iata": "FCO",
            "seed_iata_list": ["CIA", "fco", "MXP", "cia"],
            "include_nearby": False,
            "radius_km": 150,
            "max_candidates": 6,
        }
    )

    payload = canonicalize_search_fingerprint_payload(canonical)

    assert payload["origin"]["seed_pool"] == ["CIA", "FCO", "MXP"]


def test_cache_source_hash_is_stable_for_same_route_provider_and_currency() -> None:
    first = build_cache_source_hash(
        origin_iata=" agp ",
        destination_iata="dub",
        travel_date=dt.date(2026, 7, 20),
        provider="Ryanair",
        currency="eur",
    )
    second = build_cache_source_hash(
        origin_iata="AGP",
        destination_iata="DUB",
        travel_date="2026-07-20",
        provider="ryanair",
        currency="EUR",
    )

    assert first == second


def test_cache_source_hash_changes_when_currency_changes() -> None:
    eur = build_cache_source_hash(
        origin_iata="AGP",
        destination_iata="DUB",
        travel_date="2026-07-20",
        provider="ryanair",
        currency="EUR",
    )
    usd = build_cache_source_hash(
        origin_iata="AGP",
        destination_iata="DUB",
        travel_date="2026-07-20",
        provider="ryanair",
        currency="USD",
    )

    assert eur != usd


def test_expanded_nearby_routes_get_their_own_unit_keys() -> None:
    seed_route = build_unit_cache_key(
        origin_iata="AGP",
        destination_iata="DUB",
        travel_date="2026-07-20",
        provider="ryanair",
    )
    nearby_route = build_unit_cache_key(
        origin_iata="GRX",
        destination_iata="DUB",
        travel_date="2026-07-20",
        provider="ryanair",
    )

    assert seed_route != nearby_route


def test_round_trip_legs_can_be_cached_as_separate_units() -> None:
    outbound = build_unit_cache_key(
        origin_iata="AGP",
        destination_iata="DUB",
        travel_date="2026-07-20",
        provider="ryanair",
    )
    inbound = build_unit_cache_key(
        origin_iata="DUB",
        destination_iata="AGP",
        travel_date="2026-07-27",
        provider="ryanair",
    )

    assert outbound != inbound


def test_offer_fingerprint_ignores_price_changes() -> None:
    offer = {
        "provider": "ryanair",
        "carrier": "FR",
        "flight_number": "FR 1234",
        "origin_airport": "LEI",
        "destination_airport": "FCO",
        "departure_at": "2026-07-20T10:15:00Z",
        "arrival_at": "2026-07-20T12:45:00Z",
        "stops_count": 0,
        "price_amount": 49.99,
        "currency": "EUR",
    }
    repriced = dict(offer, price_amount=79.99, currency="USD")

    assert build_offer_fingerprint(offer) == build_offer_fingerprint(repriced)


def test_offer_fingerprint_changes_when_schedule_changes() -> None:
    first = {
        "provider": "ryanair",
        "carrier": "FR",
        "flight_number": "FR1234",
        "origin_airport": "LEI",
        "destination_airport": "FCO",
        "departure_at": "2026-07-20T10:15:00Z",
        "arrival_at": "2026-07-20T12:45:00Z",
        "stops_count": 0,
    }
    second = dict(first, departure_at="2026-07-20T11:15:00Z")

    assert build_offer_fingerprint(first) != build_offer_fingerprint(second)


def test_offer_fingerprint_falls_back_to_segments_when_flight_number_missing() -> None:
    outbound = {
        "provider": "duffel",
        "carrier": "AZ",
        "origin_airport": "LEI",
        "destination_airport": "FCO",
        "departure_at": dt.datetime(2026, 7, 20, 10, 15),
        "arrival_at": dt.datetime(2026, 7, 20, 13, 30),
        "stops_count": 1,
        "segments": [
            {
                "carrier": "IB",
                "origin": "LEI",
                "destination": "MAD",
                "departure_at": "2026-07-20T10:15:00Z",
                "arrival_at": "2026-07-20T11:30:00Z",
            },
            {
                "carrier": "AZ",
                "origin": "MAD",
                "destination": "FCO",
                "departure_at": "2026-07-20T12:10:00Z",
                "arrival_at": "2026-07-20T13:30:00Z",
            },
        ],
    }
    same = {
        "provider": "duffel",
        "origin_airport": "LEI",
        "destination_airport": "FCO",
        "departure_at": "2026-07-20T10:15:00Z",
        "arrival_at": "2026-07-20T13:30:00Z",
        "segments": list(reversed(outbound["segments"])),
        "stops_count": 1,
    }

    assert build_offer_fingerprint(outbound) != build_offer_fingerprint(same)


def test_offer_payload_carries_source_kind_and_provider_ids() -> None:
    payload = canonicalize_offer_fingerprint_payload(
        {
            "provider": "duffel",
            "origin": "LEI",
            "destination": "FCO",
            "departure_at": "2026-07-20T10:15:00Z",
            "provider_offer_id": "abc123",
            "deeplink_signature": "deeplink-1",
            "booking_url_hash": "urlhash-1",
        },
        source_kind="deeplink",
    )

    assert payload["source_kind"] == "deeplink"
    assert payload["provider_ids"] == ["abc123", "deeplink-1", "urlhash-1"]
