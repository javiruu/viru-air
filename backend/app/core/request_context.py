from __future__ import annotations

import re
import uuid
from contextvars import ContextVar, Token

CORRELATION_ID_CTX: ContextVar[str] = ContextVar("correlation_id", default="")
CLIENT_EVENT_ID_CTX: ContextVar[str | None] = ContextVar("client_event_id", default=None)
_CORRELATION_RE = re.compile(r"^[A-Za-z0-9._\-]{8,64}$")


def normalize_correlation_id(raw_value: str | None) -> str:
    if raw_value:
        candidate = raw_value.strip()
        if _CORRELATION_RE.fullmatch(candidate):
            return candidate
    return str(uuid.uuid4())


def set_correlation_id(value: str) -> Token[str]:
    return CORRELATION_ID_CTX.set(value)


def reset_correlation_id(token: Token[str]) -> None:
    CORRELATION_ID_CTX.reset(token)


def get_correlation_id() -> str:
    return CORRELATION_ID_CTX.get("")


def normalize_client_event_id(raw_value: str | None) -> str | None:
    if raw_value:
        candidate = raw_value.strip()
        if _CORRELATION_RE.fullmatch(candidate):
            return candidate
    return None


def set_client_event_id(value: str | None) -> Token[str | None]:
    return CLIENT_EVENT_ID_CTX.set(value)


def reset_client_event_id(token: Token[str | None]) -> None:
    CLIENT_EVENT_ID_CTX.reset(token)


def get_client_event_id() -> str | None:
    return CLIENT_EVENT_ID_CTX.get()
