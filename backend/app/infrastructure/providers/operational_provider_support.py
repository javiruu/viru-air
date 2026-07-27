from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping

from app.infrastructure.providers.operational_flight_provider import (
    OperationalRateLimited,
    OperationalUnavailable,
)


def normalize_identifier(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def clean_text(value: object, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned[:max_length] or None


def parse_datetime(value: object) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(dt.UTC).replace(tzinfo=None)
    return parsed


def parse_timestamp(value: object) -> dt.datetime | None:
    if not isinstance(value, int | float):
        return None
    try:
        return dt.datetime.fromtimestamp(value, tz=dt.UTC).replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        return None


def safe_observed_at(value: dt.datetime | None, now: dt.datetime) -> dt.datetime | None:
    observed_at = value or now
    if observed_at > now + dt.timedelta(minutes=5):
        return None
    return observed_at


def retry_after(headers: Mapping[str, str], default: int = 300) -> int:
    raw = headers.get("X-Rate-Limit-Retry-After-Seconds") or headers.get("Retry-After")
    try:
        return max(1, min(86_400, int(raw or default)))
    except ValueError:
        return default


def remote_failure(
    status_code: int,
    headers: Mapping[str, str],
) -> OperationalRateLimited | OperationalUnavailable | None:
    if status_code == 429:
        return OperationalRateLimited(retry_after(headers))
    if status_code == 402:
        return OperationalUnavailable(reason="payment_required")
    if status_code in {401, 403}:
        return OperationalUnavailable(reason="authentication")
    if status_code >= 500:
        return OperationalUnavailable(reason="provider")
    if status_code >= 400:
        return OperationalUnavailable(reason="request_rejected")
    return None


def delay_minutes(scheduled: dt.datetime | None, revised: dt.datetime | None) -> int | None:
    if scheduled is None or revised is None:
        return None
    return round((revised - scheduled).total_seconds() / 60)


def bounded(value: object, minimum: float, maximum: float) -> float | None:
    if not isinstance(value, int | float):
        return None
    parsed = float(value)
    return parsed if minimum <= parsed <= maximum else None


def feet_to_metres(value: object) -> float | None:
    feet = bounded(value, -2_000, 100_000)
    return feet * 0.3048 if feet is not None else None


def knots_to_metres_per_second(value: object) -> float | None:
    knots = bounded(value, 0, 1_200)
    return knots * 0.514444 if knots is not None else None
