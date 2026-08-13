"""Unit tests for hotel area search."""

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.hotels.contracts import ProviderRateRecord
from app.infrastructure.db.models import (
    Base,
    HotelProperty,
    HotelProviderAlias,
    HotelRateSnapshot,
    HotelProviderBudget,
    HotelSweepLease,
)
from app.services.hotels_service import area_search, create_tracked_offer


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def _close(db: Session) -> None:
    engine = db._test_engine  # type: ignore[attr-defined]
    db.close()
    engine.dispose()


def _create_hotel(
    db: Session,
    *,
    name: str = "Hotel Test",
    city: str = "Madrid",
    country: str = "ES",
    lat: float = 40.4168,
    lng: float = -3.7038,
    stars: int | None = 4,
) -> HotelProperty:
    hotel = HotelProperty(
        canonical_name=name,
        normalized_name=name.lower(),
        city=city,
        country_code=country,
        latitude=lat,
        longitude=lng,
        stars=stars,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def _create_rate(
    db: Session,
    *,
    hotel_id: str,
    check_in: date,
    check_out: date,
    guests: int = 2,
    currency: str = "EUR",
    amount: float,
    provider: str = "mock",
    availability_status: str = "available",
    price_semantics: str = "unknown",
    amount_total: float | None = None,
) -> HotelRateSnapshot:
    rate = HotelRateSnapshot(
        hotel_id=hotel_id,
        provider=provider,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        currency=currency,
        amount=amount,
        availability_status=availability_status,
        price_semantics=price_semantics,
        amount_total=amount_total,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


def test_area_search_external_budget_zero_skips_adapter(monkeypatch) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", "true")
    monkeypatch.delenv("HOTEL_PROVIDER_MAKCORPS_DAILY_REQUEST_BUDGET", raising=False)

    db = _db()
    try:
        hotel = _create_hotel(db)
        db.add(HotelProviderAlias(
            hotel_id=hotel.id,
            provider="makcorps",
            provider_hotel_id="makcorps-area-budget-zero",
        ))
        db.commit()
        class RecordingProvider:
            provider_id = "makcorps"
            calls = 0

            def fetch_hotel_rates(self, **kwargs):
                self.calls += 1
                raise AssertionError("budget denial must happen before provider call")

        adapter = RecordingProvider()
        monkeypatch.setattr("app.hotels.ingestion.resolve_hotel_provider", lambda provider: adapter)
        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            use_provider=True,
        )
        assert results
        assert adapter.calls == 0
        budget = db.scalar(select(HotelProviderBudget))
        assert budget is not None
        assert budget.units_reserved == 0
        assert db.scalar(select(HotelSweepLease)) is None
    finally:
        _close(db)


def test_area_search_empty_provider_emits_empty_latency_sample(monkeypatch) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_DAILY_REQUEST_BUDGET", "1")

    db = _db()
    try:
        hotel = _create_hotel(db)
        db.add(HotelProviderAlias(hotel_id=hotel.id, provider="makcorps", provider_hotel_id="area-empty"))
        db.commit()

        class EmptyProvider:
            provider_id = "makcorps"

            def fetch_hotel_rates(self, **kwargs):
                return []

        monkeypatch.setattr("app.hotels.ingestion.resolve_hotel_provider", lambda provider: EmptyProvider())
        samples = []
        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            use_provider=True,
            latency_sink=samples.append,
        )
        assert results
        assert len(samples) == 1
        assert samples[0].operation == "area_search"
        assert samples[0].outcome == "empty"
    finally:
        _close(db)


def test_area_search_success_provider_emits_success_latency_sample(monkeypatch) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_DAILY_REQUEST_BUDGET", "1")

    db = _db()
    try:
        hotel = _create_hotel(db)
        db.add(HotelProviderAlias(hotel_id=hotel.id, provider="makcorps", provider_hotel_id="area-success"))
        db.commit()

        class SuccessProvider:
            provider_id = "makcorps"

            def fetch_hotel_rates(self, **kwargs):
                return [
                    ProviderRateRecord(
                        check_in=date(2026, 8, 1),
                        check_out=date(2026, 8, 3),
                        amount=88.0,
                        currency="EUR",
                        guests=2,
                    )
                ]

        monkeypatch.setattr("app.hotels.ingestion.resolve_hotel_provider", lambda provider: SuccessProvider())
        samples = []
        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            use_provider=True,
            latency_sink=samples.append,
        )
        assert results
        assert results[0]["lowest_price"] == 88.0
        assert len(samples) == 1
        assert samples[0].operation == "area_search"
        assert samples[0].provider == "makcorps"
        assert samples[0].outcome == "success"
    finally:
        _close(db)


def test_area_search_provider_exception_finishes_lease_as_failed(monkeypatch) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_DAILY_REQUEST_BUDGET", "1")

    db = _db()
    try:
        hotel = _create_hotel(db)
        db.add(HotelProviderAlias(
            hotel_id=hotel.id,
            provider="makcorps",
            provider_hotel_id="makcorps-area-error",
        ))
        db.commit()

        class FailingProvider:
            provider_id = "makcorps"

            def fetch_hotel_rates(self, **kwargs):
                raise RuntimeError("provider unavailable")

        monkeypatch.setattr("app.hotels.ingestion.resolve_hotel_provider", lambda provider: FailingProvider())
        samples = []
        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            use_provider=True,
            latency_sink=samples.append,
        )
        assert results
        assert len(samples) == 1
        assert samples[0].operation == "area_search"
        assert samples[0].provider == "makcorps"
        assert samples[0].outcome == "failed"
        assert samples[0].error_code == "provider_fetch_failed"
        lease = db.scalar(select(HotelSweepLease))
        assert lease is not None
        assert lease.status == "failed"
        assert lease.lease_expires_at is None
        assert db.scalar(select(HotelRateSnapshot).where(HotelRateSnapshot.provider == "makcorps")) is None
    finally:
        _close(db)


def test_area_search_finds_hotels_within_radius() -> None:
    db = _db()
    try:
        # Madrid center ~ 40.4168, -3.7038
        h1 = _create_hotel(db, name="Hotel Sol", lat=40.4168, lng=-3.7038)
        h2 = _create_hotel(db, name="Hotel Retiro", lat=40.4200, lng=-3.6900)
        h3 = _create_hotel(db, name="Hotel Barcelona", city="Barcelona", lat=41.3874, lng=2.1686)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)
        _create_rate(db, hotel_id=h2.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=120.00)
        _create_rate(db, hotel_id=h3.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=200.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        result_ids = {r["hotel_id"] for r in results}
        assert h1.id in result_ids
        assert h2.id in result_ids
        assert h3.id not in result_ids  # Barcelona is far away
        assert len(results) == 2
    finally:
        _close(db)


def test_area_search_returns_lowest_price_per_hotel() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel Sol", lat=40.4168, lng=-3.7038)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00, provider="mock")
        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=85.00, provider="booking")
        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=95.00, provider="makcorps")

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        assert len(results) == 1
        assert results[0]["lowest_price"] == 85.00
        assert results[0]["provider"] == "booking"
    finally:
        _close(db)


def test_area_search_excludes_unavailable_rate_from_lowest_price() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db, name="Sold Out Hotel", lat=40.4168, lng=-3.7038)
        _create_rate(
            db,
            hotel_id=hotel.id,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            amount=50.00,
            availability_status="unavailable",
        )
        _create_rate(
            db,
            hotel_id=hotel.id,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            amount=120.00,
            availability_status="available",
        )

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        assert results[0]["lowest_price"] == 120.00
    finally:
        _close(db)


def test_area_search_excludes_stale_rate_from_lowest_price() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db, name="Stale Hotel", lat=40.4168, lng=-3.7038)
        _create_rate(
            db,
            hotel_id=hotel.id,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            amount=50.00,
            availability_status="stale",
        )
        _create_rate(
            db,
            hotel_id=hotel.id,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            amount=120.00,
            availability_status="available",
        )

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        assert results[0]["lowest_price"] == 120.00
    finally:
        _close(db)


def test_area_search_provider_sold_out_does_not_reuse_historical_price(monkeypatch) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_DAILY_REQUEST_BUDGET", "1")

    db = _db()
    try:
        hotel = _create_hotel(db, name="Sold Out Provider Hotel", lat=40.4168, lng=-3.7038)
        _create_rate(
            db,
            hotel_id=hotel.id,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            amount=90.00,
            provider="makcorps",
            availability_status="available",
        )
        db.add(HotelProviderAlias(hotel_id=hotel.id, provider="makcorps", provider_hotel_id="sold-out"))
        db.commit()

        class SoldOutProvider:
            provider_id = "makcorps"

            def fetch_hotel_rates(self, **kwargs):
                return [
                    ProviderRateRecord(
                        check_in=date(2026, 8, 1),
                        check_out=date(2026, 8, 3),
                        amount=90.00,
                        currency="EUR",
                        guests=2,
                        availability_status="unavailable",
                    )
                ]

        monkeypatch.setattr("app.hotels.ingestion.resolve_hotel_provider", lambda provider: SoldOutProvider())
        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            use_provider=True,
        )

        assert results[0]["lowest_price"] is None
        assert results[0]["provider"] is None
    finally:
        _close(db)


def test_area_search_empty_when_no_hotels_in_radius() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel Sol", lat=40.4168, lng=-3.7038)

        results = area_search(
            db,
            latitude=41.3874,
            longitude=2.1686,
            radius_km=1,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        assert results == []
    finally:
        _close(db)


def test_area_search_filters_by_min_stars() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel 3*", lat=40.4168, lng=-3.7038, stars=3)
        h2 = _create_hotel(db, name="Hotel 4*", lat=40.4200, lng=-3.6900, stars=4)
        h3 = _create_hotel(db, name="Hotel 5*", lat=40.4150, lng=-3.7000, stars=5)

        for h in [h1, h2, h3]:
            _create_rate(db, hotel_id=h.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            min_stars=4,
        )

        result_ids = {r["hotel_id"] for r in results}
        assert h1.id not in result_ids
        assert h2.id in result_ids
        assert h3.id in result_ids
        assert len(results) == 2
    finally:
        _close(db)


def test_area_search_filters_by_max_price() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Cheap", lat=40.4168, lng=-3.7038)
        h2 = _create_hotel(db, name="Expensive", lat=40.4200, lng=-3.6900)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=80.00)
        _create_rate(db, hotel_id=h2.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=150.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            max_price=100.00,
        )

        result_ids = {r["hotel_id"] for r in results}
        assert h1.id in result_ids
        assert h2.id not in result_ids
        assert len(results) == 1
    finally:
        _close(db)


def test_area_search_max_price_uses_the_total_stay_price_shown_by_v2() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db, name="Total stay", lat=40.4168, lng=-3.7038)
        _create_rate(
            db,
            hotel_id=hotel.id,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            amount=100.00,
            price_semantics="total",
            amount_total=300.00,
        )

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            max_price=200.00,
        )

        assert results == []
    finally:
        _close(db)


def test_area_search_sorts_by_price() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel A", lat=40.4168, lng=-3.7038)
        h2 = _create_hotel(db, name="Hotel B", lat=40.4200, lng=-3.6900)
        h3 = _create_hotel(db, name="Hotel C", lat=40.4150, lng=-3.7000)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)
        _create_rate(db, hotel_id=h2.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=50.00)
        _create_rate(db, hotel_id=h3.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=75.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            sort="price",
        )

        assert len(results) == 3
        assert results[0]["lowest_price"] == 50.00
        assert results[1]["lowest_price"] == 75.00
        assert results[2]["lowest_price"] == 100.00
    finally:
        _close(db)


def test_area_search_sorts_by_the_total_stay_price_shown_by_v2() -> None:
    db = _db()
    try:
        higher_total = _create_hotel(db, name="Higher total", lat=40.4168, lng=-3.7038)
        lower_total = _create_hotel(db, name="Lower total", lat=40.4200, lng=-3.6900)
        _create_rate(
            db,
            hotel_id=higher_total.id,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            amount=50.00,
            price_semantics="total",
            amount_total=300.00,
        )
        _create_rate(
            db,
            hotel_id=lower_total.id,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            amount=100.00,
            price_semantics="total",
            amount_total=200.00,
        )

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            sort="price",
        )

        assert [result["hotel_id"] for result in results] == [lower_total.id, higher_total.id]
    finally:
        _close(db)


def test_area_search_provider_chooses_the_total_stay_price_shown_by_v2(monkeypatch) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_DAILY_REQUEST_BUDGET", "1")
    db = _db()
    try:
        hotel = _create_hotel(db, name="Provider totals", lat=40.4168, lng=-3.7038)
        db.add(HotelProviderAlias(hotel_id=hotel.id, provider="makcorps", provider_hotel_id="provider-totals"))
        db.commit()

        class TotalPriceProvider:
            provider_id = "makcorps"

            def fetch_hotel_rates(self, **kwargs):
                return [
                    ProviderRateRecord(
                        check_in=date(2026, 8, 1),
                        check_out=date(2026, 8, 3),
                        amount=50.00,
                        amount_total=300.00,
                        price_semantics="total",
                        currency="EUR",
                        guests=2,
                    ),
                    ProviderRateRecord(
                        check_in=date(2026, 8, 1),
                        check_out=date(2026, 8, 3),
                        amount=100.00,
                        amount_total=200.00,
                        price_semantics="total",
                        currency="EUR",
                        guests=2,
                    ),
                ]

        monkeypatch.setattr(
            "app.hotels.ingestion.resolve_hotel_provider",
            lambda **kwargs: TotalPriceProvider(),
        )
        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            use_provider=True,
        )

        assert results[0]["lowest_price"] == 100.00
        assert results[0]["amount_total"] == 200.00
    finally:
        _close(db)


def test_area_search_sorts_by_distance() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel Far", lat=40.4300, lng=-3.7100)
        h2 = _create_hotel(db, name="Hotel Near", lat=40.4170, lng=-3.7040)
        h3 = _create_hotel(db, name="Hotel Mid", lat=40.4200, lng=-3.7000)

        for h in [h1, h2, h3]:
            _create_rate(db, hotel_id=h.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            sort="distance",
        )

        assert len(results) == 3
        assert results[0]["hotel_id"] == h2.id  # nearest
        assert results[0]["distance_km"] <= results[1]["distance_km"]
        assert results[1]["distance_km"] <= results[2]["distance_km"]
    finally:
        _close(db)


def test_area_search_sorts_by_stars() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel 3*", lat=40.4168, lng=-3.7038, stars=3)
        h2 = _create_hotel(db, name="Hotel 5*", lat=40.4200, lng=-3.6900, stars=5)
        h3 = _create_hotel(db, name="Hotel 4*", lat=40.4150, lng=-3.7000, stars=4)

        for h in [h1, h2, h3]:
            _create_rate(db, hotel_id=h.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            sort="stars",
        )

        assert len(results) == 3
        assert results[0]["stars"] == 5
        assert results[1]["stars"] == 4
        assert results[2]["stars"] == 3
    finally:
        _close(db)


def test_area_search_uses_contractual_tie_breakers_for_each_strict_sort() -> None:
    db = _db()
    try:
        check_in = date(2026, 8, 1)
        check_out = date(2026, 8, 3)
        h1 = _create_hotel(db, name="Hotel Tie A", lat=40.4168, lng=-3.7038, stars=4)
        h2 = _create_hotel(db, name="Hotel Tie B", lat=40.4168, lng=-3.7038, stars=4)
        h3 = _create_hotel(db, name="Hotel Tie Unknown", lat=40.4168, lng=-3.7038, stars=None)
        _create_rate(db, hotel_id=h1.id, check_in=check_in, check_out=check_out, amount=100.00)
        _create_rate(db, hotel_id=h2.id, check_in=check_in, check_out=check_out, amount=100.00)

        common = {
            "latitude": 40.4168,
            "longitude": -3.7038,
            "radius_km": 5,
            "check_in": check_in,
            "check_out": check_out,
            "guests": 2,
            "currency": "EUR",
        }
        price_results = area_search(db, **common, sort="price")
        assert [item["hotel_id"] for item in price_results] == sorted([h1.id, h2.id]) + [h3.id]

        distance_results = area_search(db, **common, sort="distance")
        assert [item["hotel_id"] for item in distance_results] == sorted([h1.id, h2.id]) + [h3.id]

        stars_results = area_search(db, **common, sort="stars")
        assert [item["hotel_id"] for item in stars_results] == sorted([h1.id, h2.id]) + [h3.id]
    finally:
        _close(db)


def test_area_search_has_tracking_flag() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Tracked Hotel", lat=40.4168, lng=-3.7038)
        h2 = _create_hotel(db, name="Untracked Hotel", lat=40.4200, lng=-3.6900)

        for h in [h1, h2]:
            _create_rate(db, hotel_id=h.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        create_tracked_offer(db, user_id="user-track", hotel_id=h1.id, provider="mock", initial_price=100.00, currency="EUR")

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            user_id="user-track",
        )

        h1_result = next(r for r in results if r["hotel_id"] == h1.id)
        h2_result = next(r for r in results if r["hotel_id"] == h2.id)
        assert h1_result["has_tracking"] is True
        assert h2_result["has_tracking"] is False
    finally:
        _close(db)


def test_area_search_hotel_without_rates_shows_no_price() -> None:
    db = _db()
    try:
        _h1 = _create_hotel(db, name="No Rates Hotel", lat=40.4168, lng=-3.7038)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        assert len(results) == 1
        assert results[0]["lowest_price"] is None
        assert results[0]["provider"] is None
    finally:
        _close(db)


def test_area_search_respects_currency_filter() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="EUR Hotel", lat=40.4168, lng=-3.7038)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00, currency="EUR")
        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=85.00, currency="USD")

        results_eur = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        results_usd = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="USD",
        )

        assert results_eur[0]["lowest_price"] == 100.00
        assert results_usd[0]["lowest_price"] == 85.00
    finally:
        _close(db)


def test_area_search_excludes_hotels_without_coordinates() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="With Coords", lat=40.4168, lng=-3.7038)
        h2 = HotelProperty(
            canonical_name="No Coords",
            normalized_name="no coords",
            city="Madrid",
            country_code="ES",
            latitude=None,
            longitude=None,
            stars=4,
        )
        db.add(h2)
        db.commit()

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)
        _create_rate(db, hotel_id=h2.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=50,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        result_ids = {r["hotel_id"] for r in results}
        assert h1.id in result_ids
        assert h2.id not in result_ids
    finally:
        _close(db)
