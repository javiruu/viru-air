"""Unit tests for the per-provider circuit breaker (door-to-door fan-out).

Covers:
- Trip after `failure_threshold` consecutive failures.
- Reset on success (counter clears even if not tripped).
- Skip-while-open returns None (no exception).
- Half-open probe: success closes the breaker, failure re-trips.
- `is_open` + `snapshot` visibility for diagnostics.
- The module-level `default_circuit_breaker()` is a thread-safe singleton
  under the double-checked-locking init pattern.
"""

from __future__ import annotations

import asyncio
import threading

import pytest

from app.door_to_door.providers import circuit_breaker as cb_mod
from app.door_to_door.providers.circuit_breaker import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
    default_circuit_breaker,
)


class _BoomError(Exception):
    pass


async def _ok() -> str:
    return "ok"


async def _boom() -> str:
    raise _BoomError("provider down")


def _run(coro):  # tiny helper so tests stay linear
    return asyncio.new_event_loop().run_until_complete(coro)


def test_breaker_trips_after_threshold_consecutive_failures() -> None:
    breaker = ProviderCircuitBreaker(
        CircuitBreakerConfig(failure_threshold=3, recovery_seconds=30.0)
    )

    async def main() -> None:
        # 2 failures: still closed.
        for _ in range(2):
            with pytest.raises(_BoomError):
                await breaker.run("p1", _boom)
        assert breaker.is_open("p1") is False

        # 3rd failure trips the breaker.
        with pytest.raises(_BoomError):
            await breaker.run("p1", _boom)
        assert breaker.is_open("p1") is True

        # Subsequent calls are skipped (no exception, returns None).
        assert await breaker.run("p1", _ok) is None

    _run(main())


def test_breaker_success_resets_failure_counter() -> None:
    breaker = ProviderCircuitBreaker(
        CircuitBreakerConfig(failure_threshold=2, recovery_seconds=0.1)
    )

    async def main() -> None:
        with pytest.raises(_BoomError):
            await breaker.run("p1", _boom)
        # 1 failure is below the threshold — breaker still closed.
        assert breaker.is_open("p1") is False
        # Success clears the counter (even if not yet tripped).
        assert await breaker.run("p1", _ok) == "ok"
        # 1 more failure: still below the (now-reset) threshold.
        with pytest.raises(_BoomError):
            await breaker.run("p1", _boom)
        assert breaker.is_open("p1") is False

    _run(main())


def test_breaker_half_open_probe_closes_on_success() -> None:
    # Use 0.2s windows to stay reliable on slow CI runners — the previous
    # 0.05s/0.06s pair was reported as fragile by code-review.
    breaker = ProviderCircuitBreaker(
        CircuitBreakerConfig(failure_threshold=1, recovery_seconds=0.2)
    )

    async def main() -> None:
        with pytest.raises(_BoomError):
            await breaker.run("p1", _boom)
        assert breaker.is_open("p1") is True

        await asyncio.sleep(0.25)
        # Recovery window elapsed — next call is a half-open probe.
        assert await breaker.run("p1", _ok) == "ok"
        # Successful probe closes the breaker.
        assert breaker.is_open("p1") is False

    _run(main())


def test_breaker_half_open_probe_re_trips_on_failure() -> None:
    breaker = ProviderCircuitBreaker(
        CircuitBreakerConfig(failure_threshold=1, recovery_seconds=0.2)
    )

    async def main() -> None:
        with pytest.raises(_BoomError):
            await breaker.run("p1", _boom)
        assert breaker.is_open("p1") is True

        await asyncio.sleep(0.25)
        with pytest.raises(_BoomError):
            await breaker.run("p1", _boom)
        # Failed probe re-arms the recovery window (no thrashing) so the
        # provider stays skipped for another `recovery_seconds`.
        assert breaker.is_open("p1") is True
        # And a second call inside the new window is skipped (returns None).
        assert await breaker.run("p1", _ok) is None

    _run(main())


def test_breaker_per_provider_state_is_independent() -> None:
    breaker = ProviderCircuitBreaker(
        CircuitBreakerConfig(failure_threshold=1, recovery_seconds=30.0)
    )

    async def main() -> None:
        with pytest.raises(_BoomError):
            await breaker.run("p1", _boom)
        assert breaker.is_open("p1") is True
        # p2 is untouched by p1's failures.
        assert breaker.is_open("p2") is False
        assert await breaker.run("p2", _ok) == "ok"

    _run(main())


def test_breaker_snapshot_reports_recover_in_seconds() -> None:
    breaker = ProviderCircuitBreaker(
        CircuitBreakerConfig(failure_threshold=1, recovery_seconds=5.0)
    )

    async def main() -> None:
        with pytest.raises(_BoomError):
            await breaker.run("p1", _boom)
        snap = breaker.snapshot()
        assert "p1" in snap
        assert snap["p1"]["consecutive_failures"] == 1
        recover_in = snap["p1"]["recover_in_seconds"]
        assert isinstance(recover_in, float)
        assert 0.0 <= recover_in <= 5.0

    _run(main())


def test_breaker_snapshot_for_untripped_provider_has_none_recover_window() -> None:
    """`snapshot()` for a provider that has not tripped must report
    `recover_in_seconds=None` (no recovery window in progress).
    """
    breaker = ProviderCircuitBreaker(
        CircuitBreakerConfig(failure_threshold=3, recovery_seconds=5.0)
    )

    async def main() -> None:
        # Register p1 with a successful call only (no failures).
        assert await breaker.run("p1", _ok) == "ok"
        snap = breaker.snapshot()
        assert "p1" in snap
        assert snap["p1"]["consecutive_failures"] == 0
        assert snap["p1"]["opened_at_monotonic"] is None
        assert snap["p1"]["recover_in_seconds"] is None

    _run(main())


def test_default_circuit_breaker_is_thread_safe_singleton() -> None:
    """DCL init must return the same instance even under concurrent access
    from many threads. Reset the module-level singleton first so we
    actually exercise the init path.

    NOTE: this test mutates module state (`cb_mod._DEFAULT_BREAKER = None`)
    for a brief window. The try/finally restores the original value so
    other tests are unaffected. In a unit suite with serial test execution
    this is safe; if the suite ever moves to parallel execution, scope
    the reset via a per-test fixture.
    """
    original = cb_mod._DEFAULT_BREAKER
    cb_mod._DEFAULT_BREAKER = None
    try:
        results: list[ProviderCircuitBreaker] = []
        barrier = threading.Barrier(8)

        def worker() -> None:
            barrier.wait()
            results.append(default_circuit_breaker())

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 8
        first = results[0]
        assert all(r is first for r in results), (
            "all threads must get the same singleton instance"
        )
    finally:
        cb_mod._DEFAULT_BREAKER = original
