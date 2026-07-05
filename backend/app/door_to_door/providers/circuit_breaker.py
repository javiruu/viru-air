"""Per-provider circuit breaker for door-to-door fan-out search.

Keeps a tiny in-memory state per provider so a flaky source can be short-circuited
for a recovery window instead of blocking or repeatedly failing the whole search.

This stage (1) is infrastructure: it makes the existing registry safer to grow.
Once we land heavier, network-bound open engines (Valhalla, OSRM, MOTIS), the
breaker prevents a single hung provider from degrading the whole fan-out.

Behavior:
- Closed on startup. Tracks consecutive failures per provider.
- Trips after `failure_threshold` consecutive failures: subsequent calls are
  skipped for `recovery_seconds`. A skip emits a structured log and a
  `PROVIDER_CIRCUIT_OPEN` warning with no provider options.
- Half-open after `recovery_seconds`. The next call attempts a probe; success
  resets the breaker, failure re-trips.
- In-memory only — process restart resets the state. Future step: persist to
  Redis if we want the breaker to survive deploys.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger("app.door_to_door.circuit_breaker")

T = TypeVar("T")

# Process-wide singleton. The breaker is most useful when its state survives
# between request fan-outs: a flapping provider that trips now should stay
# skipped across subsequent requests until the cool-down elapses.
_DEFAULT_LOCK = threading.Lock()
_DEFAULT_BREAKER: "ProviderCircuitBreaker | None" = None


def default_circuit_breaker() -> "ProviderCircuitBreaker":
    """Lazy accessor for the process-wide singleton breaker.

    Thread-safe init. Tests should NOT call this; they construct their own
    ProviderCircuitBreaker and inject it via the constructor.
    """
    global _DEFAULT_BREAKER
    if _DEFAULT_BREAKER is None:
        with _DEFAULT_LOCK:
            if _DEFAULT_BREAKER is None:
                _DEFAULT_BREAKER = ProviderCircuitBreaker()
    return _DEFAULT_BREAKER


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Tunables. Conservative defaults — wire-up can override via constructor."""

    failure_threshold: int = 3
    recovery_seconds: float = 30.0


@dataclass
class _CircuitState:
    """Per-provider runtime state."""

    consecutive_failures: int = 0
    opened_at_monotonic: float | None = None

    def trip(self, *, now_monotonic: float, threshold: int) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= threshold:
            # Re-arm the recovery window on EVERY trip. This handles two
            # cases uniformly: (a) the first trip from closed state, and
            # (b) a failed half-open probe — otherwise a persistently
            # failing provider would be probed every recovery_seconds
            # forever (thrashing). The success path still resets the
            # counter + opened_at via `reset()`.
            self.opened_at_monotonic = now_monotonic

    def half_open(self, *, now_monotonic: float, recovery_seconds: float) -> bool:
        if self.opened_at_monotonic is None:
            return False
        return (now_monotonic - self.opened_at_monotonic) >= recovery_seconds

    def reset(self) -> None:
        self.consecutive_failures = 0
        self.opened_at_monotonic = None


class ProviderCircuitBreaker:
    """In-memory breaker that wraps each provider call during fan-out."""

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._states: dict[str, _CircuitState] = {}

    def snapshot(self) -> dict[str, dict[str, float | int | None]]:
        """Return shallow visibility for diagnostics / tests."""
        return {
            name: {
                "consecutive_failures": state.consecutive_failures,
                "opened_at_monotonic": state.opened_at_monotonic,
                "recover_in_seconds": (
                    None
                    if state.opened_at_monotonic is None
                    else max(0.0, self._config.recovery_seconds - (time.monotonic() - state.opened_at_monotonic))
                ),
            }
            for name, state in self._states.items()
        }

    def is_open(self, provider_name: str) -> bool:
        state = self._states.get(provider_name)
        if state is None or state.opened_at_monotonic is None:
            return False
        # If recovery has elapsed we treat the breaker as half-open (probe allowed).
        return not state.half_open(
            now_monotonic=time.monotonic(),
            recovery_seconds=self._config.recovery_seconds,
        )

    async def run(
        self,
        provider_name: str,
        fn: Callable[[], Awaitable[T]],
    ) -> T | None:
        """Run the provider call under the breaker.

        Returns None when the breaker is open (treat as a soft skip).
        Raises the original exception when the call fails — the caller is
        responsible for surfacing it as a structured warning / partial result.
        """
        state = self._states.setdefault(provider_name, _CircuitState())
        if state.opened_at_monotonic is not None and not state.half_open(
            now_monotonic=time.monotonic(),
            recovery_seconds=self._config.recovery_seconds,
        ):
            logger.info(
                "d2d_provider_circuit_open_skip",
                extra={"provider": provider_name},
            )
            return None
        try:
            result = await fn()
        except asyncio.CancelledError:
            raise
        except Exception:
            state.trip(now_monotonic=time.monotonic(), threshold=self._config.failure_threshold)
            logger.warning(
                "d2d_provider_circuit_failure",
                extra={
                    "provider": provider_name,
                    "consecutive_failures": state.consecutive_failures,
                    "opened_at_monotonic": state.opened_at_monotonic,
                },
            )
            raise
        # Success path: any open breaker closes.
        state.reset()
        return result
