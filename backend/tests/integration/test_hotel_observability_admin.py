from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.time import utc_now_naive
from app.infrastructure.db.models import (
    HotelProviderBudget,
    HotelProviderCircuit,
    HotelProviderLatencyAggregate,
    HotelProviderRun,
    HotelSweepLease,
    User,
)
from app.services.hotel_observability_metrics import (
    METRIC_HOTEL_DELIVERY,
    METRIC_SWEEP_RUN,
    build_hotel_health_snapshot,
    list_hotel_provider_controls,
    list_hotel_provider_latency_diagnostics,
    list_hotel_provider_outcome_diagnostics,
    list_hotel_provider_run_diagnostics,
    list_hotel_sweep_lease_diagnostics,
    record_hotel_daily_metric,
)
from tests.helpers import register_and_token


def test_hotel_observability_endpoint_requires_admin(client: TestClient) -> None:
    token = register_and_token(client, email="hotel-metrics-user@viru.dev")
    response = client.get(
        "/api/v1/admin/hotels/observability",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_hotel_observability_endpoint_returns_aggregates_without_private_ids(client: TestClient) -> None:
    email = "hotel-metrics-admin@viru.dev"
    token = register_and_token(client, email=email)
    from app.infrastructure.db.session import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        record_hotel_daily_metric(
            db,
            metric_name=METRIC_HOTEL_DELIVERY,
            provider="local",
            outcome="delivered",
            increment=4,
        )
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(
        "/api/v1/admin/hotels/observability",
        headers={"Authorization": f"Bearer {token}"},
        params={"days": 1, "metric_name": METRIC_HOTEL_DELIVERY},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["days"] == 1
    assert payload["metrics"]
    metric = payload["metrics"][0]
    assert metric["metric_name"] == METRIC_HOTEL_DELIVERY
    assert metric["count"] == 4
    assert "user_id" not in metric
    assert "hotel_id" not in metric


def test_hotel_provider_latency_endpoint_requires_admin(client: TestClient) -> None:
    token = register_and_token(client, email="hotel-latency-user@viru.dev")
    response = client.get(
        "/api/v1/admin/hotels/provider-latency",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_hotel_provider_latency_endpoint_returns_bounded_safe_aggregates(client: TestClient) -> None:
    email = "hotel-latency-admin@viru.dev"
    token = register_and_token(client, email=email)
    from app.infrastructure.db.session import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        run = HotelProviderRun(provider="mock", status="completed")
        db.add(run)
        db.flush()
        db.add_all([
            HotelProviderLatencyAggregate(
                provider_run_id=run.id,
                provider="mock",
                operation="ingestion",
                outcome="success",
                error_code="none",
                sample_count=2,
                total_duration_ms=30,
                min_duration_ms=10,
                max_duration_ms=20,
            ),
            HotelProviderLatencyAggregate(
                provider_run_id=run.id,
                provider="mock",
                operation="revalidation",
                outcome="failed",
                error_code="provider_error",
                sample_count=1,
                total_duration_ms=40,
                min_duration_ms=40,
                max_duration_ms=40,
            ),
        ])
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(
        "/api/v1/admin/hotels/provider-latency",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 10, "provider": "mock", "operation": "ingestion"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sample_size"] == 1
    row = payload["aggregates"][0]
    assert row["operation"] == "ingestion"
    assert row["sample_count"] == 2
    assert row["average_duration_ms"] == 15.0
    assert row["error_code"] is None
    assert "provider_run_id" not in response.text
    assert "user_id" not in response.text
    assert "hotel_id" not in response.text


def test_hotel_provider_latency_diagnostics_reject_unbounded_limit() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.infrastructure.db.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            with pytest.raises(ValueError, match="hotel_latency_diagnostic_limit_out_of_bounds"):
                list_hotel_provider_latency_diagnostics(db, limit=51)
    finally:
        engine.dispose()


def test_hotel_provider_outcomes_endpoint_requires_admin(client: TestClient) -> None:
    token = register_and_token(client, email="hotel-outcomes-user@viru.dev")
    response = client.get(
        "/api/v1/admin/hotels/provider-outcomes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_hotel_provider_outcomes_endpoint_returns_aggregated_safe_counts(client: TestClient) -> None:
    email = "hotel-outcomes-admin@viru.dev"
    token = register_and_token(client, email=email)
    from app.infrastructure.db.session import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        now = utc_now_naive()
        db.add_all([
            HotelProviderRun(
                provider="local",
                started_at=now,
                status="completed",
                tracked_outcomes={"offers_scanned": 5, "snapshots_created": 3, "unsafe_id": 99},
            ),
            HotelProviderRun(
                provider="local",
                started_at=now,
                status="legacy_state",
                tracked_outcomes={"provider_fetch_failed": 2, "provider_fetch_budget_denied": 1},
            ),
        ])
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(
        "/api/v1/admin/hotels/provider-outcomes",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sample_size"] == 2
    local = next(item for item in payload["providers"] if item["provider"] == "local")
    assert local["runs"] == 2
    assert local["statuses"]["completed"] == 1
    assert local["statuses"]["unknown"] == 1
    assert local["outcomes"] == {
        "offers_scanned": 5,
        "provider_fetch_budget_denied": 1,
        "provider_fetch_failed": 2,
        "snapshots_created": 3,
    }
    assert payload["totals"] == local["outcomes"]
    assert "unsafe_id" not in response.text
    assert "tracked_outcomes" not in response.text
    assert "provider_run_id" not in response.text


def test_hotel_provider_outcomes_reject_unbounded_limit() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.infrastructure.db.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            with pytest.raises(ValueError, match="hotel_outcome_diagnostic_limit_out_of_bounds"):
                list_hotel_provider_outcome_diagnostics(db, limit=51)
    finally:
        engine.dispose()


def test_hotel_sweep_leases_endpoint_requires_admin(client: TestClient) -> None:
    token = register_and_token(client, email="hotel-leases-user@viru.dev")
    response = client.get(
        "/api/v1/admin/hotels/sweep-leases",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_hotel_sweep_leases_endpoint_returns_safe_expiry_diagnostics(client: TestClient) -> None:
    email = "hotel-leases-admin@viru.dev"
    token = register_and_token(client, email=email)
    from app.infrastructure.db.session import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        now = utc_now_naive()
        db.add_all([
            HotelSweepLease(
                fingerprint="a" * 64,
                status="running",
                lock_token="private-lock-token",
                lease_expires_at=now,
                attempt_count=2,
                last_provider_run_id="private-run-id",
                updated_at=now,
            ),
            HotelSweepLease(
                fingerprint="b" * 64,
                status="done",
                lease_expires_at=None,
                attempt_count=1,
                last_error_code="raw-external-error",
                finished_at=now,
                updated_at=now,
            ),
        ])
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(
        "/api/v1/admin/hotels/sweep-leases",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sample_size"] == 2
    assert payload["attention_count"] == 1
    expired = next(item for item in payload["leases"] if item["state"] == "expired")
    assert expired["attention"] is True
    assert expired["has_provider_run"] is True
    done = next(item for item in payload["leases"] if item["state"] == "done")
    assert done["last_error_code"] == "unknown"
    assert "fingerprint" not in response.text
    assert "lock_token" not in response.text
    assert "last_provider_run_id" not in response.text
    assert "private-lock-token" not in response.text
    assert "private-run-id" not in response.text


def test_hotel_sweep_lease_diagnostics_reject_unbounded_limit() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.infrastructure.db.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            with pytest.raises(ValueError, match="hotel_sweep_lease_diagnostic_limit_out_of_bounds"):
                list_hotel_sweep_lease_diagnostics(db, limit=51)
    finally:
        engine.dispose()


def test_hotel_provider_controls_endpoint_requires_admin(client: TestClient) -> None:
    token = register_and_token(client, email="hotel-controls-user@viru.dev")
    response = client.get(
        "/api/v1/admin/hotels/provider-controls",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_hotel_provider_controls_endpoint_returns_safe_persisted_state(client: TestClient) -> None:
    email = "hotel-controls-admin@viru.dev"
    token = register_and_token(client, email=email)
    from app.infrastructure.db.session import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        now = utc_now_naive()
        db.add_all([
            HotelProviderBudget(
                provider="makcorps",
                operation="revalidation",
                window_key=now.strftime("%Y-%m-%d"),
                hard_limit=10,
                units_reserved=2,
                units_used=3,
                units_released=1,
                window_expires_at=now.replace(hour=23, minute=59, second=59),
                source="local_config",
            ),
            HotelProviderCircuit(
                provider="makcorps",
                operation="area_search",
                status="open",
                failure_threshold=3,
                consecutive_failures=3,
                opened_at=now,
                next_probe_at=now,
                last_error_code="timeout",
                probe_token="private-probe-token",
            ),
            HotelProviderCircuit(
                provider="makcorps",
                operation="ingestion",
                status="legacy_state",
                last_error_code="raw-provider-error",
            ),
            HotelProviderBudget(
                provider="makcorps",
                operation="ingestion",
                window_key="not-a-window",
                hard_limit=4,
                window_expires_at=now.replace(hour=23, minute=59, second=59),
                source="unexpected-source",
            ),
        ])
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(
        "/api/v1/admin/hotels/provider-controls",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 50},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 50
    budget = next(item for item in payload["budgets"] if item["operation"] == "revalidation")
    assert budget["units_remaining"] == 5
    assert budget["units_used"] == 3
    circuit = next(item for item in payload["circuits"] if item["operation"] == "area_search")
    assert circuit["status"] == "open"
    assert circuit["last_error_code"] == "timeout"
    legacy = next(item for item in payload["circuits"] if item["operation"] == "ingestion")
    assert legacy["status"] == "unknown"
    assert legacy["last_error_code"] == "unknown"
    legacy_budget = next(item for item in payload["budgets"] if item["operation"] == "ingestion")
    assert legacy_budget["window_key"] == "unknown"
    assert legacy_budget["source"] == "unknown"
    assert all("id" not in item for item in payload["budgets"] + payload["circuits"])
    assert all("probe_token" not in item for item in payload["circuits"])
    assert "private-probe-token" not in response.text
    assert "raw-provider-error" not in response.text


def test_hotel_provider_controls_reject_unbounded_limit() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.infrastructure.db.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            with pytest.raises(ValueError, match="hotel_provider_control_limit_out_of_bounds"):
                list_hotel_provider_controls(db, limit=51)
    finally:
        engine.dispose()


def test_hotel_provider_runs_endpoint_requires_admin(client: TestClient) -> None:
    token = register_and_token(client, email="hotel-runs-user@viru.dev")
    response = client.get(
        "/api/v1/admin/hotels/runs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_hotel_provider_runs_endpoint_returns_safe_bounded_diagnostics(client: TestClient) -> None:
    email = "hotel-runs-admin@viru.dev"
    token = register_and_token(client, email=email)
    from app.infrastructure.db.session import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        now = utc_now_naive()
        db.add_all([
            HotelProviderRun(
                provider="local",
                started_at=now,
                finished_at=now,
                status="completed",
                items_processed=3,
                error_message='secret-token https://provider.test?api_key="secret"',
                tracked_outcomes={"items_scanned": 99, "snapshots_created": 2, "unsafe_identifier": 7},
            ),
            HotelProviderRun(provider="local", started_at=now, status="legacy_state"),
        ])
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(
        "/api/v1/admin/hotels/runs",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 2
    assert len(payload["runs"]) == 2
    completed = next(run for run in payload["runs"] if run["status"] == "completed")
    legacy = next(run for run in payload["runs"] if run["status"] == "unknown")
    assert completed["provider"] == "local"
    assert completed["duration_seconds"] == 0
    assert completed["items_processed"] == 3
    assert completed["has_error"] is True
    assert completed["outcomes"] == {"snapshots_created": 2}
    assert legacy["duration_seconds"] is None
    assert "id" not in completed
    assert "error_message" not in completed
    assert "secret" not in response.text


def test_hotel_provider_run_diagnostics_rejects_unbounded_limit() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.infrastructure.db.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            with pytest.raises(ValueError, match="hotel_run_diagnostic_limit_out_of_bounds"):
                list_hotel_provider_run_diagnostics(db, limit=51)
    finally:
        engine.dispose()


def test_hotel_health_endpoint_requires_admin(client: TestClient) -> None:
    token = register_and_token(client, email="hotel-health-user@viru.dev")
    response = client.get(
        "/api/v1/admin/hotels/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_hotel_health_endpoint_reports_persisted_run_without_provider_call(
    client: TestClient,
    monkeypatch,
) -> None:
    email = "hotel-health-admin@viru.dev"
    token = register_and_token(client, email=email)
    monkeypatch.setattr(
        "app.hotels.makcorps_provider.requests.Session",
        lambda: (_ for _ in ()).throw(AssertionError("health must not construct a provider")),
    )
    from app.infrastructure.db.session import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        now = utc_now_naive()
        db.add(
            HotelProviderRun(
                provider="local",
                started_at=now,
                finished_at=now,
                status="completed",
                items_processed=3,
            )
        )
        record_hotel_daily_metric(
            db,
            metric_name=METRIC_SWEEP_RUN,
            provider="local",
            outcome="completed",
            increment=1,
        )
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(
        "/api/v1/admin/hotels/health",
        headers={"Authorization": f"Bearer {token}"},
        params={"window_hours": 24},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["window_hours"] == 24
    assert payload["latest_run"]["provider"] == "local"
    assert payload["latest_run"]["status"] == "completed"
    local = next(item for item in payload["providers"] if item["provider"] == "local")
    assert local["status"] == "ok"
    assert local["completed"] == 1
    assert "user_id" not in payload
    assert "hotel_id" not in payload


def test_hotel_health_snapshot_is_honest_when_no_runs_exist() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.infrastructure.db.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            payload = build_hotel_health_snapshot(db)
            assert payload["status"] == "unknown"
            assert payload["latest_run"] is None
            assert all(item["status"] == "unknown" for item in payload["providers"])
    finally:
        engine.dispose()


def test_hotel_health_normalizes_unknown_persisted_run_status() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.infrastructure.db.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            now = utc_now_naive()
            db.add(HotelProviderRun(provider="local", started_at=now, status="legacy_state"))
            db.commit()
            payload = build_hotel_health_snapshot(db)
            local = next(item for item in payload["providers"] if item["provider"] == "local")
            assert local["status"] == "unknown"
            assert local["last_run_status"] == "unknown"
            assert payload["latest_run"]["status"] == "unknown"
    finally:
        engine.dispose()


def test_hotel_observability_endpoint_rejects_unbounded_window(client: TestClient) -> None:
    email = "hotel-metrics-bounds-admin@viru.dev"
    token = register_and_token(client, email=email)
    from app.infrastructure.db.session import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get(
        "/api/v1/admin/hotels/observability",
        headers={"Authorization": f"Bearer {token}"},
        params={"days": 32},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "hotel_metric_days_out_of_bounds"
