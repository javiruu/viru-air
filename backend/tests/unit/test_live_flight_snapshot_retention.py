import datetime as dt

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightOperationalSnapshot
from app.infrastructure.db.session import Base
from app.services.live_flight_snapshot_retention import prune_old_operational_snapshots


def _snapshot(fingerprint: str, observed_at: dt.datetime) -> FlightOperationalSnapshot:
    return FlightOperationalSnapshot(
        flight_instance_fingerprint=fingerprint,
        provider="aviationstack",
        status="landed",
        observed_at=observed_at,
        expires_at=observed_at + dt.timedelta(hours=6),
        data_quality="status_only",
    )


def test_operational_snapshot_retention_removes_only_expired_history() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = dt.datetime(2026, 7, 21, 12, 0)
    with Session(engine) as db:
        db.add_all(
            [
                _snapshot("old-flight", now - dt.timedelta(days=31)),
                _snapshot("recent-flight", now - dt.timedelta(days=29)),
            ]
        )
        db.commit()

        deleted = prune_old_operational_snapshots(
            db,
            now=now,
            retention_days=30,
            cadence_seconds=0,
        )

        remaining = db.scalar(select(func.count()).select_from(FlightOperationalSnapshot))
        recent = db.scalar(
            select(FlightOperationalSnapshot).where(
                FlightOperationalSnapshot.flight_instance_fingerprint == "recent-flight"
            )
        )
    assert deleted == 1
    assert remaining == 1
    assert recent is not None
