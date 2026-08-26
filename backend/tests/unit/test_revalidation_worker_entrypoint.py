import asyncio

import pytest

from app.services import revalidation_worker_entrypoint


def test_daily_watchlist_scheduler_runs_again_after_one_day(monkeypatch) -> None:
    scheduled = []
    sleep_calls = 0

    async def fake_sleep(seconds: int) -> None:
        nonlocal sleep_calls
        assert seconds == 86400
        sleep_calls += 1
        if sleep_calls > 1:
            raise asyncio.CancelledError()

    async def fake_to_thread(callback) -> None:
        callback()

    monkeypatch.setattr(revalidation_worker_entrypoint, "WATCHLIST_DAILY_REFRESH_INTERVAL_SECONDS", 86400)
    monkeypatch.setattr(revalidation_worker_entrypoint.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(revalidation_worker_entrypoint.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(revalidation_worker_entrypoint, "_schedule_jobs", lambda: scheduled.append("daily"))

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(revalidation_worker_entrypoint._schedule_watchlist_daily())

    assert scheduled == ["daily"]
