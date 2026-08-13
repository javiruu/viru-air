from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_PROFILE_PATH = Path(__file__).resolve().parent / "fixtures" / "hotel_fault_profiles.json"

SUPPORTED_PROFILES = frozenset(
    {
        "happy_path",
        "empty_provider",
        "rate_limited_429",
        "provider_timeout",
        "invalid_json",
        "schema_drift",
        "rate_without_currency",
        "sold_out",
        "hotel_ambiguous",
        "deeplink_invalid",
        "stale_history",
        "partial_batch",
        "ownership_cross_user",
    }
)


@dataclass(frozen=True, slots=True)
class HotelFaultProfile:
    name: str
    mode: str
    expected_status: str
    error_code: str | None = None
    scope: str = "provider"
    expected_counts: dict[str, int] = field(default_factory=dict)
    expected_external_calls: int = 0
    expected_run_status: str = "completed"


class HotelFaultProfileError(ValueError):
    """Base class for deterministic local Mock fault outcomes."""

    def __init__(self, profile: HotelFaultProfile, message: str | None = None) -> None:
        self.profile = profile
        self.error_code = profile.error_code or "provider_error"
        super().__init__(message or f"hotel_mock_fault:{self.error_code}")


class HotelRateLimitedError(HotelFaultProfileError):
    pass


class HotelProviderTimeoutError(HotelFaultProfileError):
    pass


class HotelInvalidResponseError(HotelFaultProfileError):
    pass


_PROFILE_EXCEPTION_TYPES = {
    "rate_limited_429": HotelRateLimitedError,
    "provider_timeout": HotelProviderTimeoutError,
    "invalid_json": HotelInvalidResponseError,
    "schema_drift": HotelInvalidResponseError,
    "rate_without_currency": HotelInvalidResponseError,
}


def load_hotel_fault_profiles(path: str | Path | None = None) -> dict[str, HotelFaultProfile]:
    profile_path = Path(path) if path else DEFAULT_PROFILE_PATH
    try:
        payload: Any = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("hotel_fault_profiles_invalid_manifest") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("hotel_fault_profiles_version_unsupported")
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, dict):
        raise ValueError("hotel_fault_profiles_missing_profiles")

    profiles: dict[str, HotelFaultProfile] = {}
    for name, raw in raw_profiles.items():
        if name not in SUPPORTED_PROFILES or not isinstance(raw, dict):
            raise ValueError("hotel_fault_profile_unknown")
        mode = raw.get("mode")
        expected_status = raw.get("expected_status")
        default_run_status = "failed" if expected_status in {"rate_limited", "timeout", "invalid_response", "failed"} else (
            "partial" if expected_status == "partial" else "completed"
        )
        expected_run_status = raw.get("expected_run_status", default_run_status)
        error_code = raw.get("error_code")
        scope = raw.get("scope", "provider")
        expected_counts = raw.get("expected_counts", {})
        expected_external_calls = raw.get("expected_external_calls", 0)
        if not all(isinstance(value, str) for value in (mode, expected_status, expected_run_status, scope)):
            raise ValueError("hotel_fault_profile_invalid_shape")
        if expected_run_status not in {"completed", "partial", "failed", "skipped"}:
            raise ValueError("hotel_fault_profile_invalid_run_status")
        if error_code is not None and not isinstance(error_code, str):
            raise ValueError("hotel_fault_profile_invalid_error_code")
        if not isinstance(expected_counts, dict) or any(
            not isinstance(key, str) or not isinstance(value, int) or isinstance(value, bool) or value < 0
            for key, value in expected_counts.items()
        ):
            raise ValueError("hotel_fault_profile_invalid_expected_counts")
        if not isinstance(expected_external_calls, int) or isinstance(expected_external_calls, bool) or expected_external_calls < 0:
            raise ValueError("hotel_fault_profile_invalid_external_calls")
        profiles[name] = HotelFaultProfile(
            name=name,
            mode=mode,
            expected_status=expected_status,
            expected_run_status=expected_run_status,
            error_code=error_code,
            scope=scope,
            expected_counts=dict(expected_counts),
            expected_external_calls=expected_external_calls,
        )

    missing = SUPPORTED_PROFILES.difference(profiles)
    if missing:
        raise ValueError(f"hotel_fault_profiles_missing:{','.join(sorted(missing))}")
    return profiles


def resolve_hotel_fault_profile(name: str | None, *, path: str | Path | None = None) -> HotelFaultProfile:
    profile_name = (name or "happy_path").strip().lower()
    if profile_name not in SUPPORTED_PROFILES:
        raise ValueError(f"hotel_fault_profile_unknown:{profile_name}")
    return load_hotel_fault_profiles(path)[profile_name]


def exception_for_profile(profile: HotelFaultProfile) -> HotelFaultProfileError:
    exception_type = _PROFILE_EXCEPTION_TYPES.get(profile.name, HotelFaultProfileError)
    return exception_type(profile)
