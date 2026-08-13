from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Base, HotelDailyMetric
from app.services.hotel_observability_metrics import (
    METRIC_HOTEL_DELIVERY,
    METRIC_SWEEP_RUN,
    list_hotel_daily_metrics,
    record_hotel_daily_metric,
)


def _db() -> tuple[Session, object]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = Session(engine)
    return db, engine


def test_daily_metric_upsert_accumulates_without_private_dimensions() -> None:
    db, engine = _db()
    try:
        record_hotel_daily_metric(
            db,
            metric_name=METRIC_HOTEL_DELIVERY,
            provider="LOCAL",
            outcome="delivered",
            metric_date=date(2026, 8, 9),
        )
        record_hotel_daily_metric(
            db,
            metric_name=METRIC_HOTEL_DELIVERY,
            provider="local",
            outcome="delivered",
            increment=2,
            metric_date=date(2026, 8, 9),
        )
        db.commit()
        rows = list(db.scalars(select(HotelDailyMetric)))
        assert len(rows) == 1
        assert rows[0].count == 3
        assert rows[0].provider == "local"
        assert "user_id" not in rows[0].__table__.columns
        assert "hotel_id" not in rows[0].__table__.columns
    finally:
        db.close()
        engine.dispose()


def test_daily_metric_rejects_unknown_dimensions_and_bounds() -> None:
    db, engine = _db()
    try:
        with pytest.raises(ValueError, match="metric_name"):
            record_hotel_daily_metric(db, metric_name="user_metric", provider="mock", outcome="created")
        with pytest.raises(ValueError, match="provider"):
            record_hotel_daily_metric(db, metric_name=METRIC_SWEEP_RUN, provider="user@example.com", outcome="completed")
        with pytest.raises(ValueError, match="outcome"):
            record_hotel_daily_metric(db, metric_name=METRIC_SWEEP_RUN, provider="mock", outcome="unknown")
        with pytest.raises(ValueError, match="increment"):
            record_hotel_daily_metric(db, metric_name=METRIC_SWEEP_RUN, provider="mock", outcome="completed", increment=0)
        with pytest.raises(ValueError, match="days"):
            list_hotel_daily_metrics(db, days=32)
    finally:
        db.close()
        engine.dispose()


def test_daily_metric_query_is_bounded_and_filterable() -> None:
    db, engine = _db()
    try:
        record_hotel_daily_metric(db, metric_name=METRIC_SWEEP_RUN, provider="mock", outcome="completed")
        record_hotel_daily_metric(db, metric_name=METRIC_SWEEP_RUN, provider="makcorps", outcome="failed")
        db.commit()
        rows = list_hotel_daily_metrics(db, days=1, provider="mock", metric_name=METRIC_SWEEP_RUN)
        assert len(rows) == 1
        assert rows[0].outcome == "completed"
    finally:
        db.close()
        engine.dispose()


@pytest.mark.parametrize("provider", ["local_scrape", "osm_overpass"])
def test_daily_metric_accepts_the_catalog_providers(provider: str) -> None:
    db, engine = _db()
    try:
        record_hotel_daily_metric(
            db,
            metric_name=METRIC_SWEEP_RUN,
            provider=provider,
            outcome="completed",
        )
        db.commit()

        rows = list_hotel_daily_metrics(db, days=1, provider=provider)

        assert len(rows) == 1
        assert rows[0].provider == provider
    finally:
        db.close()
        engine.dispose()
