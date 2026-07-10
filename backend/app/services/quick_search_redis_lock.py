from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal, Protocol

from app.infrastructure.redis_client import get_redis

RedisSetResult = bool | int | str | bytes | None

_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
end
return 0
"""


class RedisLockClient(Protocol):
    def set(self, name: str, value: str, nx: bool, ex: int) -> RedisSetResult: ...

    def eval(self, script: str, numkeys: int, *args: str) -> RedisSetResult: ...


@dataclass(frozen=True, slots=True)
class RedisLockAttempt:
    status: Literal["acquired", "busy", "unavailable"]
    lock_token: str | None = None


def acquire_redis_provider_lock(
    *,
    lock_key: str,
    ttl_seconds: int,
    redis_client: RedisLockClient | None = None,
) -> RedisLockAttempt:
    client = _resolve_client(redis_client)
    if client is None:
        return RedisLockAttempt(status="unavailable")
    raw_token = uuid.uuid4().hex
    try:
        acquired = client.set(_redis_lock_key(lock_key), raw_token, nx=True, ex=max(1, int(ttl_seconds)))
    except _redis_error_types():
        return RedisLockAttempt(status="unavailable")
    if not acquired:
        return RedisLockAttempt(status="busy")
    return RedisLockAttempt(status="acquired", lock_token=_encode_lock_token(lock_key, raw_token))


def release_redis_provider_lock(
    *,
    lock_token: str,
    redis_client: RedisLockClient | None = None,
) -> bool | None:
    parsed = _decode_lock_token(lock_token)
    if parsed is None:
        return None
    lock_key, raw_token = parsed
    client = _resolve_client(redis_client)
    if client is None:
        return False
    try:
        released = client.eval(_RELEASE_SCRIPT, 1, _redis_lock_key(lock_key), raw_token)
    except _redis_error_types():
        return False
    return bool(released)


def _resolve_client(redis_client: RedisLockClient | None) -> RedisLockClient | None:
    return redis_client if redis_client is not None else get_redis()


def _redis_lock_key(lock_key: str) -> str:
    return f"qs:lock:{lock_key}"


def _encode_lock_token(lock_key: str, raw_token: str) -> str:
    return f"redis:{lock_key}:{raw_token}"


def _decode_lock_token(lock_token: str) -> tuple[str, str] | None:
    parts = lock_token.split(":", 2)
    if len(parts) != 3 or parts[0] != "redis":
        return None
    return parts[1], parts[2]


def _redis_error_types() -> tuple[type[BaseException], ...]:
    try:
        from redis.exceptions import RedisError
    except ImportError:
        return (ConnectionError, TimeoutError, OSError)
    return (RedisError, ConnectionError, TimeoutError, OSError)
