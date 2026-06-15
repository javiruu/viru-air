import datetime as dt
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.infrastructure.db.models import Base, FlightWatch, PriceSnapshot, RevalidationJob, User
from app.infrastructure.db.session import get_db
from app.main import app


def _db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def _seed_user(db: Session, email: str) -> User:
    user = User(email=email, password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_watch(db: Session, *, user_id: str, origin: str = "LEI", destination: str = "DUB") -> FlightWatch:
    watch = FlightWatch(
        user_id=user_id,
        origin_iata=origin,
        destination_iata=destination,
        travel_date_local=dt.date(2026, 7, 20),
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


def _seed_snapshot(db: Session, *, watch_id: str, price: float, is_stale: bool) -> PriceSnapshot:
    snapshot = PriceSnapshot(
        watch_id=watch_id,
        captured_at_utc=dt.datetime(2026, 7, 20, 8, 0),
        departure_time_local="10:00",
        raw_price=price,
        raw_currency="EUR",
        provider="seed-provider",
        is_stale=is_stale,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _flight(price: float):
    return type(
        "ProviderFlightStub",
        (),
        {
            "price": price,
            "currency": "EUR",
            "departure_time_local": "10:30",
            "source": "stub-provider",
        },
    )()


def _override_db(db: Session):
    def _get_db_override():
        yield db
    return _get_db_override


def test_refresh_now_revalidates_stale_watch_and_marks_job_done() -> None:
    db = _db()
    current_user = _seed_user(db, "watch-owner@example.com")
    watch = _seed_watch(db, user_id=current_user.id)
    _seed_snapshot(db, watch_id=watch.id, price=99.0, is_stale=True)

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: current_user
    client = TestClient(app)

    try:
        with (
            patch("app.api.v1.watchlist.REFRESH_COOLDOWN_SECONDS", 0),
            patch("app.api.v1.watchlist.provider.get_flights", return_value=[_flight(75.0)]),
        ):
            response = client.post(f"/api/v1/watchlist/{watch.id}/refresh-now")

        assert response.status_code == 200
        assert response.json()["status"] == "queued"

        snapshots = db.execute(
            select(PriceSnapshot).where(PriceSnapshot.watch_id == watch.id).order_by(PriceSnapshot.captured_at_utc.asc())
        ).scalars().all()
        jobs = db.execute(select(RevalidationJob)).scalars().all()
        refreshed = [snapshot for snapshot in snapshots if float(snapshot.raw_price) == 75.0 and snapshot.is_stale is False]

        assert len(snapshots) == 2
        assert len(refreshed) == 1
        assert len(jobs) == 1
        assert jobs[0].status == "done"
    finally:
        app.dependency_overrides.clear()
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_refresh_now_provider_error_returns_warning_and_failed_job() -> None:
    db = _db()
    current_user = _seed_user(db, "watch-owner-2@example.com")
    watch = _seed_watch(db, user_id=current_user.id)

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: current_user
    client = TestClient(app)

    try:
        with (
            patch("app.api.v1.watchlist.REFRESH_COOLDOWN_SECONDS", 0),
            patch("app.api.v1.watchlist.provider.get_flights", side_effect=RuntimeError("provider unavailable")),
        ):
            response = client.post(f"/api/v1/watchlist/{watch.id}/refresh-now")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "queued"
        assert payload["stale_data"] is True
        assert payload["provider_status"] == "degraded"

        jobs = db.execute(select(RevalidationJob)).scalars().all()
        assert len(jobs) == 1
        assert jobs[0].status == "failed"
        assert jobs[0].last_error_code == "provider_error"
    finally:
        app.dependency_overrides.clear()
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_refresh_now_active_job_returns_429_without_duplicate_provider_call() -> None:
    db = _db()
    current_user = _seed_user(db, "watch-owner-3@example.com")
    watch = _seed_watch(db, user_id=current_user.id)
    active_job = RevalidationJob(
        job_type="manual",
        target_type="route",
        target_fingerprint=f"route:{watch.origin_iata}:{watch.destination_iata}:{watch.travel_date_local.isoformat()}",
        provider="multi",
        status="queued",
        priority=20,
        scheduled_at=dt.datetime(2026, 7, 20, 9, 0),
    )
    db.add(active_job)
    db.commit()
    db.refresh(active_job)

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: current_user
    client = TestClient(app)

    try:
        with (
            patch("app.api.v1.watchlist.REFRESH_COOLDOWN_SECONDS", 0),
            patch("app.api.v1.watchlist.provider.get_flights") as provider_get_flights,
        ):
            response = client.post(f"/api/v1/watchlist/{watch.id}/refresh-now")

        assert response.status_code == 429
        payload = response.json()
        assert payload["code"] == "revalidation_already_in_progress"
        assert payload["details"][0]["job_id"] == active_job.id
        provider_get_flights.assert_not_called()
    finally:
        app.dependency_overrides.clear()
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_refresh_now_cannot_access_another_users_watch() -> None:
    db = _db()
    current_user = _seed_user(db, "watch-owner-4@example.com")
    other_user = _seed_user(db, "watch-owner-5@example.com")
    watch = _seed_watch(db, user_id=other_user.id)

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: current_user
    client = TestClient(app)

    try:
        with patch("app.api.v1.watchlist.REFRESH_COOLDOWN_SECONDS", 0):
            response = client.post(f"/api/v1/watchlist/{watch.id}/refresh-now")

        assert response.status_code == 404
        assert response.json()["code"] == "watch_not_found"
        jobs = db.execute(select(RevalidationJob)).scalars().all()
        assert jobs == []
    finally:
        app.dependency_overrides.clear()
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
