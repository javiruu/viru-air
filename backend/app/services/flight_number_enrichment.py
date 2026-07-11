from __future__ import annotations


def normalize_explicit_flight_number(
    value: str | int | None,
    *,
    carrier_code: str | None = None,
) -> str | None:
    if value is None:
        return None

    normalized = _alnum_upper(str(value))
    if not normalized:
        return None

    carrier = _alnum_upper(carrier_code or "")
    if carrier and normalized.isdecimal():
        return f"{carrier}{normalized}"
    return normalized


def _alnum_upper(value: str) -> str:
    return "".join(character for character in value.strip().upper() if character.isalnum())
