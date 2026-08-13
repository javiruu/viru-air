import logging
import time
from collections.abc import Callable

import anyio
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.main as main_module
from app.main import app
from app.services.fare_memory_revalidation_worker import (
    RevalidationWorkerConfig,
    run_periodic_revalidation_worker,
)


def test_periodic_revalidation_worker_keeps_running_after_expected_error(caplog) -> None:
    calls: list[int | None] = []

    def _unused_session_factory() -> Session:
        raise AssertionError("The fake processor must not open a real session")

    def _processor(_session_factory: Callable[[], Session], *, max_jobs: int | None = None) -> dict[str, object]:
        calls.append(max_jobs)
        if len(calls) == 1:
            raise SQLAlchemyError("temporary database hiccup")
        return {
            "event": "watchlist_startup_refresh_worker_completed",
            "processed_job_count": 0,
            "refreshed_job_count": 0,
            "skipped_job_count": 0,
            "failed_job_count": 0,
        }

    async def _scenario() -> None:
        with anyio.move_on_after(0.05):
            await run_periodic_revalidation_worker(
                _unused_session_factory,
                RevalidationWorkerConfig(interval_seconds=0.01, batch_size=7),
                processor=_processor,
            )

    with caplog.at_level(logging.INFO, logger="app.watchlist"):
        anyio.run(_scenario)

    assert calls[:2] == [7, 7]
    assert any("fare_memory_revalidation_worker_failed" in record.message for record in caplog.records)
    assert any("fare_memory_revalidation_worker_tick" in record.message for record in caplog.records)


def test_server_startup_runs_periodic_revalidation_worker_without_blocking(monkeypatch) -> None:
    started = False
    cancelled = False

    async def _worker(*_args, **_kwargs) -> None:
        nonlocal started, cancelled
        started = True
        try:
            await anyio.sleep_forever()
        except anyio.get_cancelled_exc_class():
            cancelled = True
            raise

    monkeypatch.setattr(main_module, "FARE_MEMORY_REVALIDATION_WORKER_ENABLED", True)
    monkeypatch.setattr(main_module, "enable_in_process_workers", True)
    monkeypatch.setattr(main_module, "FARE_MEMORY_REVALIDATION_WORKER_INTERVAL_SECONDS", 60)
    monkeypatch.setattr(main_module, "FARE_MEMORY_REVALIDATION_WORKER_BATCH_SIZE", 20)
    monkeypatch.setattr(main_module, "FARE_MEMORY_RETENTION_ENABLED", False)
    monkeypatch.setattr(main_module, "WATCHLIST_STARTUP_REFRESH_ENABLED", False)
    monkeypatch.setattr(main_module, "FARE_MEMORY_BOOT_WARMUP_ENABLED", False)
    monkeypatch.setattr(main_module, "run_periodic_revalidation_worker", _worker)

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert started is True
        assert hasattr(app.state, "fare_memory_revalidation_worker_task")

    deadline = time.time() + 2.0
    while time.time() < deadline and not cancelled:
        time.sleep(0.05)

    assert cancelled is True
