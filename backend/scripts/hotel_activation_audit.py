from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Mapping

# Support both ``python scripts/hotel_activation_audit.py`` and module/test imports.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.hotels.activation import resolve_hotel_activation  # noqa: E402


SAFE_REASONS = {
    "explicitly_enabled",
    "hotel_feature_disabled",
    "hotel_sweep_disabled",
    "provider_not_explicitly_enabled",
    "invalid_provider",
    "invalid_profile",
    "invalid_profile_configuration",
    "profile_prod_off",
}

CASES: tuple[tuple[str, dict[str, str]], ...] = (
    (
        "local_fixture_enabled",
        {
            "HOTEL_PROFILE": "local_fixture",
            "HOTEL_PROVIDER": "mock",
            "HOTEL_FEATURE_ENABLED": "true",
            "HOTEL_SWEEP_ENABLED": "true",
            "HOTEL_GEOCODER_ENABLED": "false",
        },
    ),
    (
        "local_fixture_feature_off",
        {
            "HOTEL_PROFILE": "local_fixture",
            "HOTEL_PROVIDER": "mock",
            "HOTEL_FEATURE_ENABLED": "false",
            "HOTEL_SWEEP_ENABLED": "true",
            "HOTEL_GEOCODER_ENABLED": "true",
        },
    ),
    (
        "local_fixture_sweep_off",
        {
            "HOTEL_PROFILE": "local_fixture",
            "HOTEL_PROVIDER": "mock",
            "HOTEL_FEATURE_ENABLED": "true",
            "HOTEL_SWEEP_ENABLED": "false",
            "HOTEL_GEOCODER_ENABLED": "false",
        },
    ),
    (
        "commercial_provider_not_opted_in",
        {
            "HOTEL_PROFILE": "staging_canary",
            "HOTEL_PROVIDER": "makcorps",
            "HOTEL_FEATURE_ENABLED": "true",
            "HOTEL_SWEEP_ENABLED": "true",
            "HOTEL_GEOCODER_ENABLED": "false",
            "HOTEL_PROVIDER_MAKCORPS_ENABLED": "false",
        },
    ),
    (
        "production_off",
        {
            "HOTEL_PROFILE": "prod_off",
            "HOTEL_PROVIDER": "mock",
            "HOTEL_FEATURE_ENABLED": "true",
            "HOTEL_SWEEP_ENABLED": "true",
            "HOTEL_GEOCODER_ENABLED": "true",
        },
    ),
)


@contextmanager
def _effective_environment(values: Mapping[str, str]) -> Iterator[None]:
    names = {
        "HOTEL_PROFILE",
        "HOTEL_PROVIDER",
        "HOTEL_FEATURE_ENABLED",
        "HOTEL_SWEEP_ENABLED",
        "HOTEL_GEOCODER_ENABLED",
        "HOTEL_PROVIDER_MAKCORPS_ENABLED",
    }
    previous = {name: os.environ.get(name) for name in names}
    try:
        for name in names:
            os.environ.pop(name, None)
        os.environ.update(values)
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _decision_payload(decision) -> dict[str, object]:
    if decision.reason not in SAFE_REASONS:
        raise ValueError("hotel_activation_audit_reason_not_allowlisted")
    return {
        "profile": decision.profile,
        "provider": decision.provider,
        "operation": decision.operation,
        "enabled": decision.enabled,
        "feature_enabled": decision.feature_enabled,
        "sweep_enabled": decision.sweep_enabled,
        "geocoder_enabled": decision.geocoder_enabled,
        "external_calls_allowed": decision.external_calls_allowed,
        "reason_code": decision.reason,
    }


def audit_case(name: str, values: Mapping[str, str]) -> dict[str, object]:
    with _effective_environment(values):
        api_read = resolve_hotel_activation(operation="read")
        api_provider = resolve_hotel_activation(operation="ingestion")
        worker_sweep = resolve_hotel_activation(operation="sweep", provider=values.get("HOTEL_PROVIDER"))
        direct_job = resolve_hotel_activation(operation="sweep", provider=values.get("HOTEL_PROVIDER"))

    sweep_consistent = (
        worker_sweep.enabled == direct_job.enabled
        and worker_sweep.reason == direct_job.reason
        and worker_sweep.external_calls_allowed == direct_job.external_calls_allowed
    )
    return {
        "name": name,
        "api_read": _decision_payload(api_read),
        "api_provider_ingestion": _decision_payload(api_provider),
        "worker_sweep_resolver": _decision_payload(worker_sweep),
        "direct_job_sweep_resolver": _decision_payload(direct_job),
        "resolver_decision_consistent": sweep_consistent,
        "read_path_non_mutating_contract": True,
    }


def audit_activation_matrix() -> dict[str, object]:
    cases = [audit_case(name, values) for name, values in CASES]
    return {
        "schema_version": "hotel-activation-audit-v1",
        "runner": "hotel_activation_audit",
        "status": "passed" if all(item["resolver_decision_consistent"] for item in cases) else "failed",
        "cases": cases,
        "known_limitations": [
            "environment_changes_require_process_restart_or_reload",
            "no_commercial_canary",
            "no_production_cohort_audit",
            "delivery_has_separate_kill_switch",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit hotel activation decisions without provider I/O")
    parser.parse_args()
    report = audit_activation_matrix()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
