import datetime as dt
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.domain.entities import ProviderFetchResult, ProviderFlight
from app.infrastructure.db.models import Base, FlightWatch, PriceSnapshot, QuickSearchCacheEntry, RevalidationJob, User
from app.infrastructure.db.session import get_db
from app.main import app
from app.services.quick_search_cache_service import serialize_fetch_result, set_cache_entry
from app.services.quick_search_execution import build_cache_source_hash


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


def _seed_snapshot(db: Session, *, watch_id: str, price: float) -> PriceSnapshot:
    snapshot = PriceSnapshot(
        watch_id=watch_id,
        captured_at_utc=dt.datetime(2026, 7, 1, 8, 0),
        departure_time_local="10:00",
        raw_price=price,
        raw_currency="EUR",
        provider="seed-provider",
        is_stale=True,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _provider_result(price: float, *, source: str) -> ProviderFetchResult:
    return ProviderFetchResult(
        flights=[
            ProviderFlight(
                price=price,
                currency="EUR",
                departure_time_local="10:30",
                captured_at=dt.datetime(2026, 7, 10, 8, 0),
                source=source,
            )
        ],
        warnings=[],
    )


def _cache_route_result(db: Session, watch: FlightWatch, result: ProviderFetchResult) -> None:
    payload_json, warnings_json = serialize_fetch_result(result)
    set_cache_entry(
        db,
        origin_iata=watch.origin_iata,
        destination_iata=watch.destination_iata,
        travel_date=str(watch.travel_date_local),
        provider="multi",
        source_hash=build_cache_source_hash(
            origin_iata=watch.origin_iata,
            destination_iata=watch.destination_iata,
            travel_date=str(watch.travel_date_local),
            provider="multi",
        ),
        category="ready",
        payload_json=payload_json,
        warnings_json=warnings_json,
    )


def _override_db(db: Session):
    def _get_db_override():
        yield db

    return _get_db_override


def test_refresh_now_uses_fresh_global_cache_without_provider_call() -> None:
    db = _db()
    current_user = _seed_user(db, "fare-memory-owner@example.com")
    watch = _seed_watch(db, user_id=current_user.id)
    _cache_route_result(db, watch, _provider_result(66.0, source="cache-provider"))

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: current_user
    client = TestClient(app)

    try:
        with (
            patch("app.api.v1.watchlist.REFRESH_COOLDOWN_SECONDS", 0),
            patch("app.services.watchlist_revalidation.WATCH_SHARED_CACHE_ENABLED", True),
            patch("app.api.v1.watchlist.provider.get_flights") as provider_get_flights,
        ):
            response = client.post(f"/api/v1/watchlist/{watch.id}/refresh-now")

        snapshots = db.execute(select(PriceSnapshot).where(PriceSnapshot.watch_id == watch.id)).scalars().all()
        jobs = db.execute(select(RevalidationJob)).scalars().all()

        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        provider_get_flights.assert_not_called()
        assert len(snapshots) == 1
        assert float(snapshots[0].raw_price) == 66.0
        assert snapshots[0].provider == "cache-provider"
        assert len(jobs) == 1
        assert jobs[0].status == "done"
    finally:
        app.dependency_overrides.clear()
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_refresh_now_cache_miss_calls_provider_and_persists_global_cache() -> None:
    db = _db()
    current_user = _seed_user(db, "fare-memory-provider-owner@example.com")
    watch = _seed_watch(db, user_id=current_user.id, origin="AGP", destination="FCO")

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: current_user
    client = TestClient(app)

    try:
        with (
            patch("app.api.v1.watchlist.REFRESH_COOLDOWN_SECONDS", 0),
            patch("app.services.watchlist_revalidation.WATCH_SHARED_CACHE_ENABLED", True),
            patch(
                "app.api.v1.watchlist.provider.get_flights",
                return_value=_provider_result(77.0, source="provider-live"),
            ) as provider_get_flights,
        ):
            response = client.post(f"/api/v1/watchlist/{watch.id}/refresh-now")

        snapshots = db.execute(select(PriceSnapshot).where(PriceSnapshot.watch_id == watch.id)).scalars().all()
        cache_entries = db.execute(select(QuickSearchCacheEntry)).scalars().all()

        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        provider_get_flights.assert_called_once()
        assert len(snapshots) == 1
        assert float(snapshots[0].raw_price) == 77.0
        assert len(cache_entries) == 1
        assert cache_entries[0].status == "ready"
        assert cache_entries[0].provider == "multi"
    finally:
        app.dependency_overrides.clear()
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_refresh_now_provider_failure_with_history_keeps_stale_data_explicit() -> None:
    db = _db()
    current_user = _seed_user(db, "fare-memory-degraded-owner@example.com")
    watch = _seed_watch(db, user_id=current_user.id, origin="MAD", destination="DUB")
    _seed_snapshot(db, watch_id=watch.id, price=99.0)

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: current_user
    client = TestClient(app)

    try:
        with (
            patch("app.api.v1.watchlist.REFRESH_COOLDOWN_SECONDS", 0),
            patch("app.services.watchlist_revalidation.WATCH_SHARED_CACHE_ENABLED", True),
            patch("app.api.v1.watchlist.provider.get_flights", side_effect=RuntimeError("provider unavailable")),
        ):
            response = client.post(f"/api/v1/watchlist/{watch.id}/refresh-now")

        payload = response.json()
        snapshots = db.execute(select(PriceSnapshot).where(PriceSnapshot.watch_id == watch.id)).scalars().all()
        jobs = db.execute(select(RevalidationJob)).scalars().all()

        assert response.status_code == 200
        assert payload["status"] == "queued"
        assert payload["stale_data"] is True
        assert payload["provider_status"] == "degraded"
        assert len(snapshots) == 1
        assert float(snapshots[0].raw_price) == 99.0
        assert snapshots[0].is_stale is True
        assert len(jobs) == 1
        assert jobs[0].status == "failed"
    finally:
        app.dependency_overrides.clear()
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
