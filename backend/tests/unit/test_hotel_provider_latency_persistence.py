import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import Base, HotelProviderLatencyAggregate, HotelProviderRun
from app.services.hotel_provider_latency import (
    HotelProviderLatencyAccumulator,
    ProviderLatencySample,
    compose_provider_latency_sinks,
    persist_hotel_provider_latency_aggregates,
)


def _db() -> tuple[object, Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def _sample(
    *,
    operation: str = "ingestion",
    outcome: str = "success",
    duration_ms: int = 10,
    error_code: str | None = None,
) -> ProviderLatencySample:
    return ProviderLatencySample(
        provider="mock",
        operation=operation,
        outcome=outcome,
        duration_ms=duration_ms,
        attempt=1,
        error_code=error_code,
    )


def test_accumulator_groups_and_orders_without_raw_data() -> None:
    accumulator = HotelProviderLatencyAccumulator()
    accumulator.add(_sample(operation="revalidation", duration_ms=30))
    accumulator.add(_sample(duration_ms=10))
    accumulator.add(_sample(duration_ms=20))
    accumulator.add(_sample(outcome="failed", duration_ms=40, error_code="provider_error"))

    rows = accumulator.snapshot()
    assert [(row.operation, row.outcome, row.error_code) for row in rows] == [
        ("ingestion", "failed", "provider_error"),
        ("ingestion", "success", "none"),
        ("revalidation", "success", "none"),
    ]
    assert rows[1].sample_count == 2
    assert rows[1].total_duration_ms == 30
    assert rows[1].min_duration_ms == 10
    assert rows[1].max_duration_ms == 20
    assert rows[0].sample_count == 1
    assert rows[0].outcome == "failed"
    assert rows[0].error_code == "provider_error"


def test_persistence_upserts_in_same_transaction_without_commit() -> None:
    engine, db = _db()
    try:
        run = HotelProviderRun(provider="mock", status="completed", started_at=utc_now_naive())
        db.add(run)
        db.flush()
        accumulator = HotelProviderLatencyAccumulator()
        accumulator.add(_sample(duration_ms=10))
        assert persist_hotel_provider_latency_aggregates(db, provider_run_id=run.id, accumulator=accumulator) == 1
        assert persist_hotel_provider_latency_aggregates(db, provider_run_id=run.id, accumulator=accumulator) == 1
        assert db.scalar(select(HotelProviderLatencyAggregate.sample_count)) == 1
        assert db.scalar(select(HotelProviderLatencyAggregate.total_duration_ms)) == 10
        db.rollback()
        with Session(engine) as fresh:
            assert fresh.scalar(select(HotelProviderLatencyAggregate.sample_count)) is None
    finally:
        db.close()
        engine.dispose()


def test_empty_accumulator_is_noop_and_sink_failures_are_isolated() -> None:
    engine, db = _db()
    try:
        run = HotelProviderRun(provider="mock", status="completed")
        db.add(run)
        db.flush()
        assert persist_hotel_provider_latency_aggregates(
            db,
            provider_run_id=run.id,
            accumulator=HotelProviderLatencyAccumulator(),
        ) == 0
        seen: list[ProviderLatencySample] = []

        def broken(_: ProviderLatencySample) -> None:
            raise RuntimeError("secret payload")

        sink = compose_provider_latency_sinks(broken, seen.append)
        assert sink is not None
        sink(_sample())
        assert len(seen) == 1
        assert "secret payload" not in repr(seen)
    finally:
        db.close()
        engine.dispose()


def test_accumulator_normalizes_unsafe_dimensions_and_rejects_bad_duration() -> None:
    accumulator = HotelProviderLatencyAccumulator()
    with pytest.raises(ValueError, match="provider_not_allowed"):
        accumulator.add(
            ProviderLatencySample(
                provider="live-secret-provider",
                operation="raw-request",
                outcome="made-up",
                duration_ms=3,
                attempt=1,
                error_code="private-error",
            )
        )
    with pytest.raises(ValueError, match="duration_out_of_bounds"):
        accumulator.add(_sample(duration_ms=-1))
