from datetime import date, datetime, timedelta

from app.core.time import utc_now_naive
from fastapi.testclient import TestClient

import app.api.v1.watchlist as watchlist_api
from app.domain.entities import ProviderFetchResult, ProviderFlight
from app.infrastructure.db.models import PriceSnapshot
from app.infrastructure.db.session import get_db
from app.main import app
from tests.helpers import register_and_token


class _FakeProvider:
    def get_flights(self, origin: str, destination: str, travel_date: str) -> list[ProviderFlight]:
        return [
            ProviderFlight(
                price=44.0,
                currency="EUR",
                departure_time_local="09:15",
                captured_at=utc_now_naive(),
                source="fake-provider",
            )
        ]


class _FakeProviderFetchResult:
    def get_flights(self, origin: str, destination: str, travel_date: str) -> ProviderFetchResult:
        return ProviderFetchResult(
            flights=[
                ProviderFlight(
                    price=47.0,
                    currency="EUR",
                    departure_time_local="07:40",
                    captured_at=utc_now_naive(),
                    source="fake-provider-result",
                )
            ],
            warnings=[],
        )


class _ManyOffersProvider:
    def get_flights(self, origin: str, destination: str, travel_date: str) -> list[ProviderFlight]:
        return [
            ProviderFlight(
                price=52.0,
                currency="EUR",
                departure_time_local="09:15",
                captured_at=utc_now_naive(),
                source="fake-provider-a",
            ),
            ProviderFlight(
                price=44.0,
                currency="EUR",
                departure_time_local="07:40",
                captured_at=utc_now_naive(),
                source="fake-provider-b",
            ),
            ProviderFlight(
                price=47.5,
                currency="EUR",
                departure_time_local="06:50",
                captured_at=utc_now_naive(),
                source="fake-provider-c",
            ),
        ]


class _SequentialPriceProvider:
    def __init__(self, prices: list[float]) -> None:
        self._prices = iter(prices)

    def get_flights(self, origin: str, destination: str, travel_date: str) -> list[ProviderFlight]:
        return [
            ProviderFlight(
                price=next(self._prices),
                currency="EUR",
                departure_time_local="07:10",
                captured_at=utc_now_naive(),
                source="sequential-provider",
            )
        ]


def _open_test_db_session():
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    return db, generator


def _close_test_db_session(generator) -> None:
    try:
        next(generator)
    except StopIteration:
        pass


def test_watchlist_create_list_and_refresh(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=30)),
            "target_price": 40,
        },
    )
    assert create.status_code == 200
    watch_id = create.json()["id"]

    listing = client.get("/api/v1/watchlist", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["watchers_count"] == 0

    refresh = client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    assert refresh.status_code == 200

    history = client.get(f"/api/v1/prices/history?watch_id={watch_id}", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1

    detail = client.get(f"/api/v1/watchlist/{watch_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == watch_id
    assert detail.json()["latest_snapshot"] is not None
    assert detail.json()["watchers_count"] == 0


def test_watchlist_list_exposes_watchers_count_per_route(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    travel_date = str(date.today() + timedelta(days=36))
    payload = {
        "origin_iata": "MAD",
        "destination_iata": "DUB",
        "travel_date_local": travel_date,
        "target_price": 50,
    }

    token_a = register_and_token(client, email="watchers-a@viru.dev")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    token_b = register_and_token(client, email="watchers-b@viru.dev")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    first = client.post("/api/v1/watchlist", headers=headers_a, json=payload)
    second = client.post("/api/v1/watchlist", headers=headers_b, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200

    list_a = client.get("/api/v1/watchlist", headers=headers_a)
    list_b = client.get("/api/v1/watchlist", headers=headers_b)

    assert list_a.status_code == 200
    assert list_b.status_code == 200
    assert list_a.json()[0]["watchers_count"] == 1
    assert list_b.json()[0]["watchers_count"] == 1


def test_watchlist_refresh_supports_provider_fetch_result(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProviderFetchResult())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client, email="provider-fetch-result@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=31)),
            "target_price": 45,
        },
    )
    assert create.status_code == 200
    watch_id = create.json()["id"]

    refresh = client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    assert refresh.status_code == 200

    history = client.get(f"/api/v1/prices/history?watch_id={watch_id}", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_watchlist_refresh_persists_one_canonical_snapshot_per_refresh(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _ManyOffersProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client, email="canonical-refresh@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "ALC",
            "destination_iata": "TSF",
            "travel_date_local": str(date.today() + timedelta(days=32)),
            "target_price": 45,
        },
    )
    assert create.status_code == 200
    watch_id = create.json()["id"]

    refresh = client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    assert refresh.status_code == 200

    history = client.get(f"/api/v1/prices/history?watch_id={watch_id}", headers=headers)
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload) == 1
    assert history_payload[0]["departure_time_local"] == "07:40"
    assert history_payload[0]["raw_price"] == 44.0

    summary = client.get(f"/api/v1/prices/summary?watch_id={watch_id}", headers=headers)
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["count"] == 1
    assert summary_payload["latest_price"] == 44.0
    assert summary_payload["min_price"] == 44.0

    detail = client.get(f"/api/v1/watchlist/{watch_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["latest_snapshot"]["raw_price"] == 44.0
    assert detail.json()["latest_snapshot"]["departure_time_local"] == "07:40"


def test_watchlist_collapses_legacy_same_second_snapshots_across_read_endpoints(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client, email="legacy-collapse@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "LPA",
            "destination_iata": "BLQ",
            "travel_date_local": str(date.today() + timedelta(days=35)),
            "target_price": 470,
        },
    )
    assert create.status_code == 200
    watch_id = create.json()["id"]

    db, db_generator = _open_test_db_session()
    try:
        db.add_all(
            [
                PriceSnapshot(
                    watch_id=watch_id,
                    captured_at_utc=datetime(2026, 6, 5, 10, 15, 27, 111111),
                    departure_time_local="07:10",
                    raw_price=473.68,
                    raw_currency="EUR",
                    provider="duffel-a",
                ),
                PriceSnapshot(
                    watch_id=watch_id,
                    captured_at_utc=datetime(2026, 6, 5, 10, 15, 27, 222222),
                    departure_time_local="09:40",
                    raw_price=480.12,
                    raw_currency="EUR",
                    provider="duffel-b",
                ),
                PriceSnapshot(
                    watch_id=watch_id,
                    captured_at_utc=datetime(2026, 6, 5, 10, 15, 27, 333333),
                    departure_time_local="06:50",
                    raw_price=476.0,
                    raw_currency="EUR",
                    provider="ryanair",
                ),
                PriceSnapshot(
                    watch_id=watch_id,
                    captured_at_utc=datetime(2026, 6, 5, 10, 17, 3, 444444),
                    departure_time_local="07:10",
                    raw_price=460.5,
                    raw_currency="EUR",
                    provider="ryanair",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()
        _close_test_db_session(db_generator)

    detail = client.get(f"/api/v1/watchlist/{watch_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["latest_snapshot"]["captured_at_utc"].startswith("2026-06-05T10:17:03")
    assert detail.json()["latest_snapshot"]["raw_price"] == 460.5

    history = client.get(f"/api/v1/prices/history?watch_id={watch_id}", headers=headers)
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload) == 2
    assert history_payload[0]["captured_at_utc"].startswith("2026-06-05T10:17:03")
    assert history_payload[0]["raw_price"] == 460.5
    assert history_payload[1]["captured_at_utc"].startswith("2026-06-05T10:15:27")
    assert history_payload[1]["raw_price"] == 473.68

    batch = client.post(
        "/api/v1/prices/history/batch",
        headers=headers,
        json={"watch_ids": [watch_id]},
    )
    assert batch.status_code == 200
    batch_payload = batch.json()
    assert len(batch_payload) == 2
    assert [item["raw_price"] for item in batch_payload] == [460.5, 473.68]

    summary = client.get(f"/api/v1/prices/summary?watch_id={watch_id}", headers=headers)
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["count"] == 2
    assert summary_payload["latest_price"] == 460.5
    assert summary_payload["min_price"] == 460.5
    assert summary_payload["max_price"] == 473.68


def test_watchlist_refreshes_at_different_times_create_two_history_points(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _SequentialPriceProvider([91.0, 87.0]))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    refresh_times = iter(
        [
            datetime(2026, 6, 5, 10, 15, 27, 123456),
            datetime(2026, 6, 5, 10, 18, 9, 654321),
        ]
    )
    monkeypatch.setattr(watchlist_api, "utc_now_naive", lambda: next(refresh_times))

    token = register_and_token(client, email="refresh-points@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "ALC",
            "destination_iata": "BRI",
            "travel_date_local": str(date.today() + timedelta(days=41)),
            "target_price": 90,
        },
    )
    assert create.status_code == 200
    watch_id = create.json()["id"]

    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200
    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200

    history = client.get(f"/api/v1/prices/history?watch_id={watch_id}", headers=headers)
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload) == 2
    assert history_payload[0]["captured_at_utc"].startswith("2026-06-05T10:18:09")
    assert history_payload[1]["captured_at_utc"].startswith("2026-06-05T10:15:27")

    summary = client.get(f"/api/v1/prices/summary?watch_id={watch_id}", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["count"] == 2


def test_watchlist_create_duplicate_returns_409(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    token = register_and_token(client, email="duplicate-watch@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "origin_iata": "MAD",
        "destination_iata": "DUB",
        "travel_date_local": str(date.today() + timedelta(days=45)),
        "target_price": 55,
    }

    first = client.post("/api/v1/watchlist", headers=headers, json=payload)
    assert first.status_code == 200

    duplicated = client.post("/api/v1/watchlist", headers=headers, json=payload)
    assert duplicated.status_code == 409
    body = duplicated.json()
    assert body.get("code") == "watch_already_exists" or body.get("detail") == "watch_already_exists"


def test_watchlist_refresh_bulk_returns_summary(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    token = register_and_token(client, email="bulk-refresh@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create_a = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=33)),
        },
    )
    create_b = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "BCN",
            "destination_iata": "LIS",
            "travel_date_local": str(date.today() + timedelta(days=34)),
        },
    )
    watch_a = create_a.json()["id"]
    watch_b = create_b.json()["id"]

    bulk = client.post(
        "/api/v1/watchlist/refresh-bulk",
        headers=headers,
        json={"watch_ids": [watch_a, watch_b, "missing-watch-id"]},
    )
    assert bulk.status_code == 200
    payload = bulk.json()
    assert payload["requested"] == 3
    assert set(payload["refreshed"]) == {watch_a, watch_b}
    assert any(item["code"] == "watch_not_found" for item in payload["failed"])


def test_watchlist_status_bulk_returns_partial_summary(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    token = register_and_token(client, email="bulk-status@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create_a = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=37)),
        },
    )
    create_b = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "BCN",
            "destination_iata": "LIS",
            "travel_date_local": str(date.today() + timedelta(days=38)),
        },
    )
    watch_a = create_a.json()["id"]
    watch_b = create_b.json()["id"]

    bulk = client.post(
        "/api/v1/watchlist/status-bulk",
        headers=headers,
        json={"watch_ids": [watch_a, watch_b, "missing-watch-id"], "status": "paused"},
    )
    assert bulk.status_code == 200
    payload = bulk.json()
    assert payload["requested"] == 3
    assert set(payload["updated_ids"]) == {watch_a, watch_b}
    assert any(item["code"] == "watch_not_found" for item in payload["failed"])


def test_watchlist_delete_bulk_returns_partial_summary(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    token = register_and_token(client, email="bulk-delete@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create_a = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=39)),
        },
    )
    create_b = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "BCN",
            "destination_iata": "LIS",
            "travel_date_local": str(date.today() + timedelta(days=40)),
        },
    )
    watch_a = create_a.json()["id"]
    watch_b = create_b.json()["id"]

    bulk = client.post(
        "/api/v1/watchlist/delete-bulk",
        headers=headers,
        json={"watch_ids": [watch_a, watch_b, "missing-watch-id"]},
    )
    assert bulk.status_code == 200
    payload = bulk.json()
    assert payload["requested"] == 3
    assert set(payload["deleted_ids"]) == {watch_a, watch_b}
    assert any(item["code"] == "watch_not_found" for item in payload["failed"])


def test_watchlist_status_bulk_rejects_invalid_payload(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    token = register_and_token(client, email="bulk-status-invalid@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    invalid_status = client.post(
        "/api/v1/watchlist/status-bulk",
        headers=headers,
        json={"watch_ids": ["watch-a"], "status": "invalid"},
    )
    assert invalid_status.status_code == 422

    empty_ids = client.post(
        "/api/v1/watchlist/status-bulk",
        headers=headers,
        json={"watch_ids": [], "status": "paused"},
    )
    assert empty_ids.status_code == 422
