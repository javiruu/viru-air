import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.calendar_price_intelligence import (
    CalendarComparableObservation,
    build_calendar_query_fingerprint,
    classify_contextual_price,
    convert_calendar_price,
    load_fresh_calendar_reference,
    record_calendar_prices,
)
from app.api.v1.search import _build_calendar_scope_signature, _calendar_observation_route_signature
from app.infrastructure.db.models import CalendarPriceObservation
from app.infrastructure.db.session import Base


def test_calendar_query_fingerprint_separates_comparable_search_dimensions() -> None:
    base = build_calendar_query_fingerprint(
        origin_scope=("MAD",),
        destination_scope=("DUB",),
        travel_date=dt.date(2030, 6, 5),
        leg="outbound",
        adults=1,
        currency="EUR",
        provider_set=("fake",),
        aggregation_mode="min",
    )
    different_currency = build_calendar_query_fingerprint(
        origin_scope=("MAD",),
        destination_scope=("DUB",),
        travel_date=dt.date(2030, 6, 5),
        leg="outbound",
        adults=1,
        currency="USD",
        provider_set=("fake",),
        aggregation_mode="min",
    )

    assert base != different_currency


def test_calendar_observation_scope_signature_is_bounded_for_large_valid_scopes() -> None:
    raw_signature = _build_calendar_scope_signature(
        [f"A{index:02d}" for index in range(100)],
        [f"B{index:02d}" for index in range(100)],
    )

    stored_signature = _calendar_observation_route_signature(raw_signature)

    assert len(raw_signature) > 255
    assert len(stored_signature) == 64


def test_convert_calendar_price_normalizes_known_currencies_and_rejects_unknown() -> None:
    assert convert_calendar_price(100.0, "USD", "EUR") == 93.0
    assert convert_calendar_price(100.0, "ZZZ", "EUR") is None


def test_contextual_price_requires_a_comparable_sample_before_assigning_color() -> None:
    observations = [
        CalendarComparableObservation(price=90.0, observed_at=dt.datetime(2030, 1, 1)),
        CalendarComparableObservation(price=95.0, observed_at=dt.datetime(2030, 1, 2)),
        CalendarComparableObservation(price=100.0, observed_at=dt.datetime(2030, 1, 3)),
    ]

    classification = classify_contextual_price(80.0, observations)

    assert classification.bucket is None
    assert classification.reason == "insufficient_reference"


def test_contextual_price_uses_recent_comparable_baseline_instead_of_monthly_terciles() -> None:
    observations = [
        CalendarComparableObservation(price=90.0, observed_at=dt.datetime(2030, 1, 1)),
        CalendarComparableObservation(price=95.0, observed_at=dt.datetime(2030, 1, 2)),
        CalendarComparableObservation(price=100.0, observed_at=dt.datetime(2030, 1, 3)),
        CalendarComparableObservation(price=105.0, observed_at=dt.datetime(2030, 1, 4)),
        CalendarComparableObservation(price=110.0, observed_at=dt.datetime(2030, 1, 5)),
    ]

    low = classify_contextual_price(80.0, observations)
    typical = classify_contextual_price(100.0, observations)
    high = classify_contextual_price(130.0, observations)

    assert low.bucket == "low"
    assert typical.bucket == "mid"
    assert high.bucket == "high"


def test_calendar_reference_keeps_validated_observations_within_the_context_window_after_cache_expiry() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    now = dt.datetime(2030, 6, 10, 12, 0, 0)
    session.add(
        CalendarPriceObservation(
            query_fingerprint="q" * 64,
            reference_fingerprint="r" * 64,
            route_signature="o:MAD|d:DUB",
            travel_date=dt.date(2030, 6, 5),
            leg="outbound",
            adults=1,
            cabin="economy",
            aggregation_mode="min",
            currency="EUR",
            provider="fake",
            normalized_price_amount=100.0,
            observed_at=now - dt.timedelta(days=2),
            expires_at=now - dt.timedelta(days=1),
            freshness_status="fresh",
            coverage_status="available",
            validation_status="observed",
        )
    )
    session.commit()

    reference = load_fresh_calendar_reference(session, reference_fingerprint="r" * 64, now=now)

    assert [(item.travel_date, item.price) for item in reference] == [(dt.date(2030, 6, 5), 100.0)]
    session.close()
    engine.dispose()


def test_record_calendar_prices_prunes_only_observations_outside_contextual_retention() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    now = dt.datetime(2030, 6, 10, 12, 0, 0)
    stale = CalendarPriceObservation(
        query_fingerprint="s" * 64,
        reference_fingerprint="r" * 64,
        route_signature="stale",
        travel_date=dt.date(2030, 5, 1),
        normalized_price_amount=70.0,
        observed_at=now - dt.timedelta(days=31),
        expires_at=now - dt.timedelta(days=30),
    )
    recent = CalendarPriceObservation(
        query_fingerprint="r" * 64,
        reference_fingerprint="r" * 64,
        route_signature="recent",
        travel_date=dt.date(2030, 6, 5),
        normalized_price_amount=100.0,
        observed_at=now - dt.timedelta(days=2),
        expires_at=now - dt.timedelta(days=1),
        coverage_status="available",
    )
    session.add_all([stale, recent])
    session.commit()

    record_calendar_prices(
        session,
        query_fingerprints={dt.date(2030, 6, 10): "n" * 64},
        reference_fingerprint="r" * 64,
        route_signature="new",
        prices_by_day={dt.date(2030, 6, 10): 90.0},
        coverage_status_by_day={dt.date(2030, 6, 10): "available"},
        leg="outbound",
        adults=1,
        cabin="economy",
        currency="EUR",
        aggregation_mode="min",
        provider="fake",
        observed_at=now,
        expires_at=now + dt.timedelta(days=1),
    )

    rows = session.query(CalendarPriceObservation).all()
    assert {row.route_signature for row in rows} == {"recent", "new"}
    session.close()
    engine.dispose()
