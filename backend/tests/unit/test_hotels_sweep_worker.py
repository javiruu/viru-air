from __future__ import annotations

import json
import re
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.logging import SafeJsonFormatter
from app.core.request_context import (
    get_correlation_id,
    reset_client_event_id,
    reset_correlation_id,
    set_client_event_id,
    set_correlation_id,
)
from app.infrastructure.db.models import Base, HotelProviderRun, HotelTrackedOffer, HotelTrackedOfferLifecycleEvent
from app.services.hotels_service import run_hotel_sweep
from app.worker import hotels_sweep as hotels_sweep_worker


def _session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    testing._test_engine = engine  # type: ignore[attr-defined]
    return testing


def _dispose(session_factory) -> None:
    engine = session_factory._test_engine  # type: ignore[attr-defined]
    engine.dispose()


def test_worker_run_once_persists_correlation_execution_and_client_event_context(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    context_token = set_correlation_id("corr-worker-test")
    event_token = set_client_event_id("intent-worker-test")
    session_factory = _session_factory()
    try:
        provider_run = hotels_sweep_worker.run_once(session_factory=session_factory, provider="mock")
        assert provider_run.correlation_id == "corr-worker-test"
        # An autonomous worker must not inherit a browser intent from its
        # caller context; only the worker execution/correlation is persisted.
        assert provider_run.client_event_id is None
        assert provider_run.execution_id
        assert len(provider_run.execution_id) == 36

        with session_factory() as db:
            persisted = db.get(HotelProviderRun, provider_run.id)
            assert persisted is not None
            assert persisted.correlation_id == "corr-worker-test"
            assert persisted.client_event_id is None
            assert persisted.execution_id == provider_run.execution_id
    finally:
        _dispose(session_factory)
        reset_client_event_id(event_token)
        reset_correlation_id(context_token)


def test_direct_sweep_does_not_inherit_browser_client_event_context(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    context_token = set_client_event_id("intent-browser-global-sweep")
    session_factory = _session_factory()
    try:
        with session_factory() as db:
            provider_run = run_hotel_sweep(db, provider="mock")
            assert provider_run.client_event_id is None
    finally:
        _dispose(session_factory)
        reset_client_event_id(context_token)


def test_worker_run_once_emits_cycle_with_context_correlation(monkeypatch, caplog) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    context_token = set_correlation_id("")
    session_factory = _session_factory()
    try:
        with caplog.at_level("INFO", logger="app.worker.hotels_sweep"):
            provider_run = hotels_sweep_worker.run_once(
                session_factory=session_factory,
                provider="mock",
            )

        cycle = next(record for record in caplog.records if "hotel_sweep_cycle" in record.message)
        rendered = SafeJsonFormatter().format(cycle)
        payload = json.loads(rendered)
        assert payload["correlation_id"] == provider_run.correlation_id
        assert payload["provider_run_id"] == provider_run.id
        assert payload["execution_id"] == provider_run.execution_id
        assert json.loads(cycle.message)["expired_tracked_offers"] == 0
    finally:
        _dispose(session_factory)
        reset_correlation_id(context_token)


def test_worker_normalizes_inherited_correlation_id(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    context_token = set_correlation_id("PII value with spaces")
    session_factory = _session_factory()
    try:
        provider_run = hotels_sweep_worker.run_once(session_factory=session_factory, provider="mock")
        assert provider_run.correlation_id is not None
        assert re.fullmatch(r"[A-Za-z0-9._\\-]{8,64}", provider_run.correlation_id)
        assert provider_run.correlation_id != "PII value with spaces"
        assert get_correlation_id() == "PII value with spaces"
    finally:
        _dispose(session_factory)
        reset_correlation_id(context_token)


def test_worker_restores_context_when_session_factory_fails(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    context_token = set_correlation_id("outer-context")

    def failing_session_factory():
        raise RuntimeError("session factory failed")

    try:
        with pytest.raises(RuntimeError, match="session factory failed"):
            hotels_sweep_worker.run_once(session_factory=failing_session_factory, provider="mock")
        assert get_correlation_id() == "outer-context"
    finally:
        reset_correlation_id(context_token)


def test_worker_run_once_executes_mock_sweep(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    session_factory = _session_factory()
    try:
        provider_run = hotels_sweep_worker.run_once(session_factory=session_factory, provider="mock")
        assert provider_run.status == "completed"
        assert provider_run.provider == "mock"
    finally:
        _dispose(session_factory)


def test_worker_run_once_expires_due_tracking_before_the_provider_sweep(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    session_factory = _session_factory()
    try:
        with session_factory() as db:
            tracked_offer = HotelTrackedOffer(
                user_id="worker-expiration-user",
                hotel_id="worker-expiration-hotel",
                provider="mock",
                check_in=date.today() - timedelta(days=3),
                check_out=date.today() - timedelta(days=1),
            )
            db.add(tracked_offer)
            db.commit()
            tracked_offer_id = tracked_offer.id

        hotels_sweep_worker.run_once(session_factory=session_factory, provider="mock")

        with session_factory() as db:
            tracked_offer = db.get(HotelTrackedOffer, tracked_offer_id)
            assert tracked_offer is not None
            assert tracked_offer.lifecycle_state == "expired"
            assert tracked_offer.is_active is False
            event = db.scalar(
                select(HotelTrackedOfferLifecycleEvent).where(
                    HotelTrackedOfferLifecycleEvent.tracked_offer_id == tracked_offer_id,
                )
            )
            assert event is not None
            assert event.action == "expire"
            assert event.source == "sweep_expiration"
    finally:
        _dispose(session_factory)


def test_worker_run_once_records_failed_provider_run(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    session_factory = _session_factory()
    try:
        provider_run = hotels_sweep_worker.run_once(session_factory=session_factory, provider="unsupported")
        assert provider_run.status == "failed"
        assert "Unsupported sweep provider" in (provider_run.error_message or "")

        with session_factory() as db:
            persisted = db.scalar(select(HotelProviderRun).where(HotelProviderRun.id == provider_run.id))
            assert persisted is not None
            assert persisted.status == "failed"
    finally:
        _dispose(session_factory)


def test_worker_main_skips_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "false")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "false")
    monkeypatch.setattr(hotels_sweep_worker, "_parse_args", lambda: type("Args", (), {"once": True, "loop": False, "provider": "mock", "sleep_seconds": 1})())

    called = {"run_once": False}

    def _unexpected_run_once(**kwargs):
        called["run_once"] = True
        raise AssertionError("run_once should not be called when the worker is disabled")

    monkeypatch.setattr(hotels_sweep_worker, "run_once", _unexpected_run_once)
    assert hotels_sweep_worker.main() == 0
    assert called["run_once"] is False
