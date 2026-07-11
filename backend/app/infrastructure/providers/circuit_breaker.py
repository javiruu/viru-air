from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock


class ProviderCircuitBreakerConfigError(ValueError):
    def __init__(self, field: str, value: int | float) -> None:
        self.field = field
        self.value = value
        super().__init__(f"Invalid provider circuit breaker config: {field}={value}")


@dataclass(frozen=True, slots=True)
class ProviderCircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ProviderCircuitBreakerConfigError("failure_threshold", self.failure_threshold)
        if self.recovery_seconds <= 0:
            raise ProviderCircuitBreakerConfigError("recovery_seconds", self.recovery_seconds)


@dataclass(frozen=True, slots=True)
class ProviderCircuitDecision:
    can_call: bool
    recover_in_seconds: float | None = None


@dataclass(slots=True)
class _ProviderCircuitState:
    consecutive_failures: int = 0
    opened_at_monotonic: float | None = None


class ProviderCircuitBreaker:
    def __init__(
        self,
        config: ProviderCircuitBreakerConfig | None = None,
        *,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config or ProviderCircuitBreakerConfig()
        self._now = now
        self._lock = Lock()
        self._states: dict[str, _ProviderCircuitState] = {}

    def before_call(self, provider_id: str) -> ProviderCircuitDecision:
        with self._lock:
            state = self._states.get(provider_id)
            if state is None or state.opened_at_monotonic is None:
                return ProviderCircuitDecision(can_call=True)

            elapsed_seconds = self._now() - state.opened_at_monotonic
            if elapsed_seconds >= self._config.recovery_seconds:
                return ProviderCircuitDecision(can_call=True)

            return ProviderCircuitDecision(
                can_call=False,
                recover_in_seconds=max(0.0, self._config.recovery_seconds - elapsed_seconds),
            )

    def record_success(self, provider_id: str) -> None:
        with self._lock:
            self._states.pop(provider_id, None)

    def record_failure(self, provider_id: str) -> None:
        with self._lock:
            state = self._states.setdefault(provider_id, _ProviderCircuitState())
            state.consecutive_failures += 1
            if state.consecutive_failures >= self._config.failure_threshold:
                state.opened_at_monotonic = self._now()
