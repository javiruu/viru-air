from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.infrastructure.db.models import Base, HotelProviderRun
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


def test_worker_run_once_executes_mock_sweep(monkeypatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    session_factory = _session_factory()
    try:
        provider_run = hotels_sweep_worker.run_once(session_factory=session_factory, provider="mock")
        assert provider_run.status == "completed"
        assert provider_run.provider == "mock"
    finally:
        _dispose(session_factory)


def test_worker_run_once_records_failed_provider_run(monkeypatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
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
    monkeypatch.setattr(hotels_sweep_worker, "DEFAULT_SWEEP_ENABLED", False)
    monkeypatch.setattr(hotels_sweep_worker, "_parse_args", lambda: type("Args", (), {"once": True, "loop": False, "provider": "mock", "sleep_seconds": 1})())

    called = {"run_once": False}

    def _unexpected_run_once(**kwargs):
        called["run_once"] = True
        raise AssertionError("run_once should not be called when the worker is disabled")

    monkeypatch.setattr(hotels_sweep_worker, "run_once", _unexpected_run_once)
    assert hotels_sweep_worker.main() == 0
    assert called["run_once"] is False
