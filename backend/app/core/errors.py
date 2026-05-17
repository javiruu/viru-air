from __future__ import annotations

from dataclasses import dataclass

from app.core.request_context import get_correlation_id


@dataclass
class ApiError(Exception):
    status: int
    code: str
    message: str
    details: list[dict] | dict | None = None
    retry_after_sec: int | None = None


def error_envelope(
    *,
    status: int,
    code: str,
    message: str,
    details: list[dict] | dict | None = None,
    retry_after_sec: int | None = None,
) -> dict:
    correlation_id = get_correlation_id() or None
    payload = {
        "status": status,
        "code": code,
        "message": message,
        "details": details or [],
    }
    if correlation_id:
        payload["correlation_id"] = correlation_id
    if retry_after_sec is not None:
        payload["retry_after_sec"] = retry_after_sec
    return payload


ERROR_MESSAGES: dict[str, str] = {
    "invalid_auth": "Authentication failed.",
    "admin_required": "Admin privileges are required.",
    "validation_error": "Request validation failed.",
    "email_exists": "Email already registered.",
    "origin_equals_destination": "Origin and destination must be different.",
    "watch_already_exists": "This watch already exists for the same route and date.",
    "watch_not_found": "Watch not found.",
    "rule_not_found": "Rule not found.",
    "not_allowed": "Operation is not allowed.",
    "iata_invalido": "Invalid IATA code.",
    "adultos_invalidos": "Adults count is invalid.",
    "fecha_vuelta_invalida": "Return date is invalid.",
    "no_flights_found": "No flights found.",
    "ryanair_unavailable": "Provider unavailable. Try again later.",
    "idempotency_mismatch": "Idempotency key reused with a different payload.",
    "travel_date_in_past": "Travel date cannot be in the past.",
}


def message_for_code(code: str, fallback: str = "Request failed.") -> str:
    return ERROR_MESSAGES.get(code, fallback)
