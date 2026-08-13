from __future__ import annotations

import time
import os
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from app.infrastructure.redis_client import get_redis


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
        shared_decision = self._shared_before_call(provider_id)
        if shared_decision is not None:
            return shared_decision
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
        if self._shared_record_success(provider_id):
            return
        with self._lock:
            self._states.pop(provider_id, None)

    def record_failure(self, provider_id: str) -> None:
        if self._shared_record_failure(provider_id):
            return
        with self._lock:
            state = self._states.setdefault(provider_id, _ProviderCircuitState())
            state.consecutive_failures += 1
            if state.consecutive_failures >= self._config.failure_threshold:
                state.opened_at_monotonic = self._now()

    def _shared_client(self):
        if os.getenv("PROVIDER_CIRCUIT_BACKEND", "redis").strip().lower() != "redis":
            return None
        return get_redis()

    def _shared_key(self, provider_id: str) -> str:
        return f"viru:provider:circuit:{provider_id}"

    def _shared_before_call(self, provider_id: str) -> ProviderCircuitDecision | None:
        client = self._shared_client()
        if client is None:
            return None
        try:
            opened_at = client.get(self._shared_key(provider_id))
            if opened_at is None:
                return ProviderCircuitDecision(can_call=True)
            opened_at_seconds = float(opened_at)
            remaining = self._config.recovery_seconds - (time.time() - opened_at_seconds)
            if remaining <= 0:
                client.delete(self._shared_key(provider_id))
                return ProviderCircuitDecision(can_call=True)
            return ProviderCircuitDecision(can_call=False, recover_in_seconds=remaining)
        except Exception:
            return None

    def _shared_record_success(self, provider_id: str) -> bool:
        client = self._shared_client()
        if client is None:
            return False
        try:
            client.delete(self._shared_key(provider_id))
            client.delete(f"{self._shared_key(provider_id)}:failures")
            return True
        except Exception:
            return False

    def _shared_record_failure(self, provider_id: str) -> bool:
        client = self._shared_client()
        if client is None:
            return False
        try:
            failure_key = f"{self._shared_key(provider_id)}:failures"
            failures = int(client.incr(failure_key))
            client.expire(failure_key, max(1, int(self._config.recovery_seconds)))
            if failures >= self._config.failure_threshold:
                client.set(
                    self._shared_key(provider_id),
                    str(time.time()),
                    ex=max(1, int(self._config.recovery_seconds)),
                )
            return True
        except Exception:
            return False
