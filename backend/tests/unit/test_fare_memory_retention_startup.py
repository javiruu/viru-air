import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.main import lifespan


@pytest.mark.asyncio
async def test_lifespan_schedules_retention_without_blocking_startup() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    app = SimpleNamespace(state=SimpleNamespace())

    async def fake_retention_job() -> None:
        started.set()
        await release.wait()

    with (
        patch("app.main.FARE_MEMORY_BOOT_WARMUP_ENABLED", False),
        patch("app.main.WATCHLIST_STARTUP_REFRESH_ENABLED", False),
        patch("app.main.FARE_MEMORY_RETENTION_ENABLED", True),
        patch("app.main.FARE_MEMORY_REVALIDATION_WORKER_ENABLED", False),
        patch("app.main._run_startup_fare_memory_retention_job", side_effect=fake_retention_job),
    ):
        async with lifespan(app):
            await asyncio.wait_for(started.wait(), timeout=1.0)
            task = app.state.fare_memory_retention_task
            assert task.done() is False
            release.set()

    assert app.state.fare_memory_retention_task.done() is True


@pytest.mark.asyncio
async def test_lifespan_skips_retention_when_flag_is_disabled() -> None:
    app = SimpleNamespace(state=SimpleNamespace())

    async def unexpected_retention_job() -> None:
        raise AssertionError("retention task should not run")

    with (
        patch("app.main.FARE_MEMORY_BOOT_WARMUP_ENABLED", False),
        patch("app.main.WATCHLIST_STARTUP_REFRESH_ENABLED", False),
        patch("app.main.FARE_MEMORY_RETENTION_ENABLED", False),
        patch("app.main.FARE_MEMORY_REVALIDATION_WORKER_ENABLED", False),
        patch("app.main._run_startup_fare_memory_retention_job", side_effect=unexpected_retention_job),
    ):
        async with lifespan(app):
            assert not hasattr(app.state, "fare_memory_retention_task")
