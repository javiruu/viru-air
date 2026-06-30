import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.models import Base, FlightWatch, PriceSnapshot, RevalidationJob, User
from app.services.watchlist_revalidation import (
    enqueue_startup_refresh_jobs,
    process_due_route_revalidation_jobs,
)


class _StableProvider:
    def get_flights(self, origin: str, destination: str, travel_date: str):
        return [
            type(
                "ProviderFlightStub",
                (),
                {
                    "price": 61.0,
                    "currency": "EUR",
                    "departure_time_local": "08:25",
                    "source": "startup-stable-provider",
                },
            )()
        ]


def _session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _seed_user(db: Session, email: str) -> User:
    user = User(email=email, password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_watch(db: Session, *, user_id: str, travel_date: dt.date) -> FlightWatch:
    watch = FlightWatch(
        user_id=user_id,
        origin_iata="MAD",
        destination_iata="DUB",
        travel_date_local=travel_date,
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


def _seed_snapshot(
    db: Session,
    *,
    watch_id: str,
    captured_at: dt.datetime,
    price: float,
) -> PriceSnapshot:
    snapshot = PriceSnapshot(
        watch_id=watch_id,
        captured_at_utc=captured_at,
        departure_time_local="08:25",
        raw_price=price,
        raw_currency="EUR",
        provider="seed-provider",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def test_startup_refresh_enqueues_fresh_routes_on_each_server_open() -> None:
    engine, testing_session_local = _session_factory()
    db = testing_session_local()
    try:
        reference_now = dt.datetime(2026, 6, 30, 10, 0)
        owner = _seed_user(db, "startup-fresh-regression@example.com")
        watch = _seed_watch(db, user_id=owner.id, travel_date=reference_now.date() + dt.timedelta(days=30))
        _seed_snapshot(
            db,
            watch_id=watch.id,
            captured_at=reference_now - dt.timedelta(hours=1),
            price=61.0,
        )

        report = enqueue_startup_refresh_jobs(db, now=reference_now)
        jobs = db.execute(select(RevalidationJob)).scalars().all()

        assert report["evaluated_route_count"] == 1
        assert report["stale_route_count"] == 0
        assert report["enqueued_job_count"] == 1
        assert report["jobs"][0]["reason"] == "fresh"
        assert len(jobs) == 1
        assert jobs[0].job_type == "startup_refresh"
    finally:
        db.close()
        engine.dispose()


def test_startup_revalidation_does_not_add_invariant_price_points() -> None:
    engine, testing_session_local = _session_factory()
    db = testing_session_local()
    try:
        reference_now = dt.datetime(2026, 6, 30, 10, 0)
        owner_a = _seed_user(db, "startup-flat-a@example.com")
        owner_b = _seed_user(db, "startup-flat-b@example.com")
        travel_date = reference_now.date() + dt.timedelta(days=30)
        watch_a = _seed_watch(db, user_id=owner_a.id, travel_date=travel_date)
        watch_b = _seed_watch(db, user_id=owner_b.id, travel_date=travel_date)
        _seed_snapshot(db, watch_id=watch_a.id, captured_at=reference_now, price=61.0)
        _seed_snapshot(db, watch_id=watch_b.id, captured_at=reference_now, price=61.0)
        db.add(
            RevalidationJob(
                job_type="startup_refresh",
                target_type="route",
                target_fingerprint=f"route:MAD:DUB:{travel_date.isoformat()}",
                provider="multi",
                status="queued",
                priority=15,
                scheduled_at=reference_now,
            )
        )
        db.commit()

        report = process_due_route_revalidation_jobs(
            testing_session_local,
            provider_client=_StableProvider(),
        )
        snapshots = db.execute(
            select(PriceSnapshot).where(PriceSnapshot.watch_id.in_([watch_a.id, watch_b.id]))
        ).scalars().all()
        jobs = db.execute(select(RevalidationJob)).scalars().all()

        assert report["processed_job_count"] == 1
        assert report["refreshed_job_count"] == 1
        assert len(snapshots) == 2
        assert len(jobs) == 1
        assert jobs[0].status == "done"
    finally:
        db.close()
        engine.dispose()
