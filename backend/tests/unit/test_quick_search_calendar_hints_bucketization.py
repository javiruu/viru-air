import datetime as dt

from app.api.v1.search import (
    _aggregate_day_prices,
    _bucketize_day_prices_guidelines,
    _bucketize_day_prices_terciles,
    _rank_pairs_adaptive,
)


def test_bucketize_day_prices_terciles_assigns_low_mid_high() -> None:
    values = {
        dt.date(2030, 6, 5): 59.0,
        dt.date(2030, 6, 10): 119.0,
        dt.date(2030, 6, 15): 189.0,
    }

    buckets = _bucketize_day_prices_terciles(values)

    assert buckets[dt.date(2030, 6, 5)] == "low"
    assert buckets[dt.date(2030, 6, 10)] == "mid"
    assert buckets[dt.date(2030, 6, 15)] == "high"


def test_bucketize_day_prices_terciles_handles_small_sets() -> None:
    one_day = {dt.date(2030, 6, 2): 80.0}
    two_days = {dt.date(2030, 6, 2): 80.0, dt.date(2030, 6, 3): 120.0}

    one_bucket = _bucketize_day_prices_terciles(one_day)
    two_buckets = _bucketize_day_prices_terciles(two_days)

    assert one_bucket == {dt.date(2030, 6, 2): "low"}
    assert two_buckets[dt.date(2030, 6, 2)] == "low"
    assert two_buckets[dt.date(2030, 6, 3)] == "high"


def test_bucketize_day_prices_guidelines_uses_inclusive_boundaries() -> None:
    values = {
        dt.date(2030, 6, 5): 90.0,
        dt.date(2030, 6, 10): 150.0,
        dt.date(2030, 6, 15): 150.01,
    }

    buckets = _bucketize_day_prices_guidelines(values, low_max=90.0, mid_max=150.0)

    assert buckets[dt.date(2030, 6, 5)] == "low"
    assert buckets[dt.date(2030, 6, 10)] == "mid"
    assert buckets[dt.date(2030, 6, 15)] == "high"


def test_rank_pairs_adaptive_is_deterministic_and_prefers_coverage_then_price() -> None:
    pairs = [("MAD", "DUB"), ("BCN", "DUB"), ("AGP", "DUB")]
    pair_prices = {
        ("MAD", "DUB"): {dt.date(2030, 6, 5): 70.0, dt.date(2030, 6, 10): 120.0},
        ("BCN", "DUB"): {dt.date(2030, 6, 5): 90.0},
        ("AGP", "DUB"): {dt.date(2030, 6, 5): 65.0, dt.date(2030, 6, 10): 105.0},
    }

    ranked = _rank_pairs_adaptive(pairs, pair_prices)
    assert ranked[0] == ("AGP", "DUB")
    assert ranked[1] == ("MAD", "DUB")
    assert ranked[2] == ("BCN", "DUB")


def test_aggregate_day_prices_supports_min_median_and_fixed_route() -> None:
    day = dt.date(2030, 6, 10)
    pairs = [("MAD", "DUB"), ("BCN", "DUB"), ("AGP", "DUB")]
    pair_prices_by_day = {
        ("MAD", "DUB"): {day: 120.0},
        ("BCN", "DUB"): {day: 110.0},
        ("AGP", "DUB"): {day: 100.0},
    }

    min_prices = _aggregate_day_prices(pairs, pair_prices_by_day, [day], "min")
    median_prices = _aggregate_day_prices(pairs, pair_prices_by_day, [day], "median")
    fixed_prices = _aggregate_day_prices([("AGP", "DUB")], pair_prices_by_day, [day], "fixed_route")

    assert min_prices[day] == 100.0
    assert median_prices[day] == 110.0
    assert fixed_prices[day] == 100.0
