import datetime as dt

from app.api.v1.search import _bucketize_day_prices_terciles


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
