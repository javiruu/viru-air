from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

# Support both ``python scripts/hotel_mock_canary.py`` and module/test imports.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.hotels.activation import resolve_hotel_activation  # noqa: E402
from app.hotels.fault_profiles import load_hotel_fault_profiles  # noqa: E402
from app.infrastructure.db.models import (  # noqa: E402
    HotelProviderLatencyAggregate,
    HotelRateSnapshot,
)
from app.services.hotels_service import run_hotel_sweep  # noqa: E402


SCHEMA_VERSION = "hotel-mock-canary-v1"
MIGRATION_REVISION = "0059_hotel_tracking_lifecycle"
ALLOWED_PROFILES = frozenset({"local_demo", "local_fixture"})
FORBIDDEN_KEY_PARTS = frozenset(
    {
        "user_id",
        "hotel_id",
        "tracked_offer_id",
        "provider_run_id",
        "correlation_id",
        "client_event_id",
        "execution_id",
        "api_key",
        "authorization",
        "cookie",
        "token",
        "secret",
        "payload",
        "fingerprint",
        "raw",
        "url",
    }
)
SAFE_REASON_CODES = frozenset(
    {
        "explicitly_enabled",
        "hotel_feature_disabled",
        "profile_prod_off",
        "hotel_sweep_disabled",
        "invalid_profile",
        "invalid_profile_configuration",
        "invalid_provider",
    }
)
SAFE_OUTCOMES = frozenset({"success", "empty", "completed", "failed", "partial", "skipped"})


class CanaryConfigurationError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_int(value: object) -> int:
    return max(0, int(value or 0))


def _assert_safe_key(key: str) -> None:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
    if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
        raise CanaryConfigurationError("hotel_canary_forbidden_evidence_key")


def validate_evidence(value: object) -> None:
    """Reject evidence that can carry identifiers, secrets, payloads, or raw data."""
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CanaryConfigurationError("hotel_canary_evidence_key_not_string")
            _assert_safe_key(key)
            validate_evidence(child)
    elif isinstance(value, list):
        for child in value:
            validate_evidence(child)
    elif isinstance(value, str):
        if len(value) > 500:
            raise CanaryConfigurationError("hotel_canary_evidence_value_too_large")
        if re.search(r"(?i)(api[_-]?key|authorization|cookie|secret|token|https?://|[\w.+-]+@[\w.-]+\.[a-z]{2,})", value):
            raise CanaryConfigurationError("hotel_canary_forbidden_evidence_value")


def _db_path(db_url: str) -> Path:
    if not db_url.startswith("sqlite:///"):
        raise CanaryConfigurationError("hotel_canary_requires_sqlite_isolated_db")
    if db_url in {"sqlite:///./viru.db", "sqlite:///viru.db", "sqlite:///:memory:"}:
        raise CanaryConfigurationError("hotel_canary_requires_explicit_file_db")
    raw_path = db_url.removeprefix("sqlite:///")
    if not raw_path or raw_path.endswith("/"):
        raise CanaryConfigurationError("hotel_canary_requires_explicit_file_db")
    path = Path(raw_path)
    if not path.is_absolute():
        raise CanaryConfigurationError("hotel_canary_requires_absolute_isolated_db")
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        path.resolve().relative_to(temp_root)
    except ValueError as exc:
        raise CanaryConfigurationError("hotel_canary_requires_temp_workspace") from exc
    return path


def _validate_db_url(db_url: str, *, require_new: bool = True) -> None:
    path = _db_path(db_url)
    if require_new and path.exists():
        raise CanaryConfigurationError("hotel_canary_requires_new_isolated_db")
    if not path.parent.exists():
        raise CanaryConfigurationError("hotel_canary_db_parent_missing")


def _session_factory(db_url: str):
    _validate_db_url(db_url)
    backend_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["DB_URL"] = db_url
    environment["RUN_DB_INIT"] = "false"
    environment["RUN_SEED_USERS"] = "false"
    environment["WATCHLIST_STARTUP_REFRESH_ENABLED"] = "false"
    environment["FARE_MEMORY_BOOT_WARMUP_ENABLED"] = "false"
    environment["FARE_MEMORY_REVALIDATION_WORKER_ENABLED"] = "false"
    migration = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", MIGRATION_REVISION],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if migration.returncode != 0:
        raise CanaryConfigurationError("hotel_canary_migration_failed")
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _scenario_summary(
    *,
    name: str,
    status: str,
    activation_reason: str,
    external_calls_expected: int,
    external_calls_observed: int,
    run_status: str,
    snapshots: int,
    eligible_snapshots: int,
    latency_aggregates: int,
    outcomes: dict[str, int],
    provider_resolver_calls: int,
    provider_io_calls: int,
    warnings: int = 0,
    needs_review: bool = False,
    expected_counts: dict[str, int] | None = None,
    profile: str | None = None,
    expected_status: str | None = None,
    expected_run_status: str | None = None,
    expected_error_code: str | None = None,
    observed_outcome: str | None = None,
    error_code: str | None = None,
) -> dict[str, object]:
    if activation_reason not in SAFE_REASON_CODES:
        raise CanaryConfigurationError("hotel_canary_reason_not_allowlisted")
    if run_status not in SAFE_OUTCOMES:
        run_status = "unknown"
    return {
        "name": name,
        "profile": profile or name,
        "status": status,
        "activation_reason": activation_reason,
        "external_calls_expected": external_calls_expected,
        "external_calls_observed": external_calls_observed,
        "provider_resolver_calls": _safe_int(provider_resolver_calls),
        "provider_io_calls": _safe_int(provider_io_calls),
        "run_status": run_status,
        "snapshot_count": snapshots,
        "eligible_snapshot_count": eligible_snapshots,
        "latency_aggregate_count": latency_aggregates,
        "warning_count": _safe_int(warnings),
        "needs_review": bool(needs_review),
        "expected_status": expected_status,
        "expected_run_status": expected_run_status,
        "expected_error_code": expected_error_code,
        "observed_outcome": observed_outcome,
        "error_code": error_code,
        "expected_counts": {key: _safe_int(value) for key, value in sorted((expected_counts or {}).items())},
        "outcomes": {
            key: _safe_int(value)
            for key, value in sorted(outcomes.items())
            if key in {"success", "empty", "failed", "partial", "skipped", "provider_fetch_attempted"}
        },
    }


def run_nominal_scenario(
    db_url: str,
    *,
    profile: str,
    provider: str,
    fault_profile: str = "happy_path",
) -> dict[str, object]:
    if profile not in ALLOWED_PROFILES or provider != "mock":
        raise CanaryConfigurationError("hotel_canary_requires_local_mock_profile")
    engine, factory = _session_factory(db_url)
    provider_resolver_calls = 0
    provider_io_calls = 0
    external_calls_observed = 0
    from app.hotels.ingestion import resolve_hotel_provider as real_resolver

    class CountingAdapter:
        provider_id = "mock"

        def __init__(self, adapter: object) -> None:
            self._adapter = adapter

        @property
        def fault_profile(self) -> str:
            return str(getattr(self._adapter, "fault_profile", "happy_path"))

        def is_enabled(self) -> bool:
            return bool(self._adapter.is_enabled())

        def fetch_hotels(self, *args: object, **kwargs: object):
            nonlocal provider_io_calls
            provider_io_calls += 1
            return self._adapter.fetch_hotels(*args, **kwargs)

        def fetch_hotel_rates(self, **kwargs: object):
            nonlocal provider_io_calls
            provider_io_calls += 1
            return self._adapter.fetch_hotel_rates(**kwargs)

    def counting_resolver(*args: object, **kwargs: object):
        nonlocal provider_resolver_calls
        provider_resolver_calls += 1
        return CountingAdapter(real_resolver(*args, **kwargs))

    try:
        def block_external_call(*args: object, **kwargs: object) -> None:
            nonlocal external_calls_observed
            external_calls_observed += 1
            raise CanaryConfigurationError("hotel_canary_external_call_blocked")

        with patch.object(socket.socket, "connect", side_effect=block_external_call), patch.object(
            socket.socket, "connect_ex", side_effect=block_external_call
        ), patch.object(socket, "create_connection", side_effect=block_external_call), patch.dict(
            os.environ,
            {
                "HOTEL_PROFILE": profile,
                "HOTEL_PROVIDER": "mock",
                "HOTEL_FEATURE_ENABLED": "true",
                "HOTEL_SWEEP_ENABLED": "true",
                "HOTEL_GEOCODER_ENABLED": "false",
                "HOTEL_MOCK_FAULT_PROFILE": fault_profile,
            },
            clear=False,
        ), patch("app.hotels.ingestion.resolve_hotel_provider", side_effect=counting_resolver):
            activation = resolve_hotel_activation(operation="sweep", provider="mock")
            if not activation.enabled or activation.reason != "explicitly_enabled":
                raise CanaryConfigurationError("hotel_canary_nominal_activation_failed")
            with factory() as db:
                provider_run = run_hotel_sweep(db, provider="mock")
                aggregate_count = _safe_int(
                    db.scalar(
                        select(func.count(HotelProviderLatencyAggregate.id)).where(
                            HotelProviderLatencyAggregate.provider_run_id == provider_run.id
                        )
                    )
                )
                snapshot_count = _safe_int(
                    db.scalar(
                        select(func.count(HotelRateSnapshot.id)).where(
                            HotelRateSnapshot.provider_run_id == provider_run.id
                        )
                    )
                )
                outcomes = {
                    # The production outcome map intentionally omits the
                    # mock ingestion budget counter; the wrapped local fetch
                    # is the authoritative offline attempt signal here.
                    "provider_fetch_attempted": max(
                        _safe_int((provider_run.tracked_outcomes or {}).get("provider_fetch_attempted")),
                        provider_io_calls,
                    ),
                    "success": _safe_int((provider_run.tracked_outcomes or {}).get("provider_fetch_completed")),
                }
                profile_spec = load_hotel_fault_profiles()[fault_profile]
                ingestion_aggregate = db.scalar(
                    select(HotelProviderLatencyAggregate).where(
                        HotelProviderLatencyAggregate.provider_run_id == provider_run.id,
                        HotelProviderLatencyAggregate.operation == "ingestion",
                    )
                )
                observed_outcome = ingestion_aggregate.outcome if ingestion_aggregate else "unknown"
                tracked = provider_run.tracked_outcomes or {}
                observed_counts = {
                    "hotels_processed": _safe_int(provider_run.items_processed),
                    "snapshots_created": snapshot_count,
                    "warning_count": _safe_int(tracked.get("warning_count")),
                }
                counts_match = all(
                    observed_counts.get(key) == expected
                    for key, expected in profile_spec.expected_counts.items()
                )
                expected_error_code = profile_spec.error_code
                observed_error_code = ingestion_aggregate.error_code if ingestion_aggregate else None
                if observed_error_code in {"", "none", "None"}:
                    observed_error_code = None
                error_code_match = observed_error_code == expected_error_code
                run_status_match = provider_run.status == profile_spec.expected_run_status
                external_calls_match = external_calls_observed == profile_spec.expected_external_calls
                status = (
                    "passed"
                    if (
                        observed_outcome == profile_spec.expected_status
                        and provider_resolver_calls > 0
                        and provider_io_calls > 0
                        and counts_match
                        and error_code_match
                        and run_status_match
                        and external_calls_match
                    )
                    else "failed"
                )
                return _scenario_summary(
                    name="mock_nominal",
                    status=status,
                    activation_reason=activation.reason,
                    external_calls_expected=profile_spec.expected_external_calls,
                    external_calls_observed=external_calls_observed,
                    run_status=provider_run.status,
                    snapshots=snapshot_count,
                    eligible_snapshots=_safe_int(
                        db.scalar(
                            select(func.count(HotelRateSnapshot.id)).where(
                                HotelRateSnapshot.provider_run_id == provider_run.id,
                                HotelRateSnapshot.availability_status == "available",
                            )
                        )
                    ),
                    latency_aggregates=aggregate_count,
                    outcomes=outcomes,
                    provider_resolver_calls=provider_resolver_calls,
                    provider_io_calls=provider_io_calls,
                    warnings=_safe_int((provider_run.tracked_outcomes or {}).get("warning_count")),
                    needs_review=bool((provider_run.tracked_outcomes or {}).get("needs_review")),
                    expected_counts=profile_spec.expected_counts,
                    profile=fault_profile,
                    expected_status=profile_spec.expected_status,
                    expected_run_status=profile_spec.expected_run_status,
                    expected_error_code=expected_error_code,
                    observed_outcome=observed_outcome,
                    error_code=observed_error_code,
                )
    finally:
        engine.dispose()


def run_kill_switch_scenario(db_url: str, *, profile: str, provider: str) -> dict[str, object]:
    if profile not in ALLOWED_PROFILES or provider != "mock":
        raise CanaryConfigurationError("hotel_canary_requires_local_mock_profile")
    engine, factory = _session_factory(db_url)
    provider_resolver_calls = 0
    provider_io_calls = 0
    from app.hotels.ingestion import resolve_hotel_provider as real_resolver

    class CountingAdapter:
        provider_id = "mock"

        def __init__(self, adapter: object) -> None:
            self._adapter = adapter

        def is_enabled(self) -> bool:
            return bool(self._adapter.is_enabled())

        def fetch_hotels(self):
            nonlocal provider_io_calls
            provider_io_calls += 1
            return self._adapter.fetch_hotels()

        def fetch_hotel_rates(self, **kwargs: object):
            nonlocal provider_io_calls
            provider_io_calls += 1
            return self._adapter.fetch_hotel_rates(**kwargs)

    def counting_resolver(*args: object, **kwargs: object):
        nonlocal provider_resolver_calls
        provider_resolver_calls += 1
        return CountingAdapter(real_resolver(*args, **kwargs))

    try:
        with patch.dict(
            os.environ,
            {
                "HOTEL_PROFILE": profile,
                "HOTEL_PROVIDER": "mock",
                "HOTEL_FEATURE_ENABLED": "false",
                "HOTEL_SWEEP_ENABLED": "false",
                "HOTEL_GEOCODER_ENABLED": "false",
            },
            clear=False,
        ), patch("app.hotels.ingestion.resolve_hotel_provider", side_effect=counting_resolver):
            activation = resolve_hotel_activation(operation="sweep", provider="mock")
            with factory() as db:
                provider_run = run_hotel_sweep(db, provider="mock")
                snapshot_count = _safe_int(db.scalar(select(func.count(HotelRateSnapshot.id))))
                aggregate_count = _safe_int(
                    db.scalar(select(func.count(HotelProviderLatencyAggregate.id)))
                )
            passed = (
                provider_run.status == "failed"
                and activation.reason == "hotel_feature_disabled"
                and provider_resolver_calls == 0
                and provider_io_calls == 0
                and snapshot_count == 0
                and aggregate_count == 0
            )
            return _scenario_summary(
                name="global_kill_switch",
                status="passed" if passed else "failed",
                activation_reason=activation.reason,
                external_calls_expected=0,
                external_calls_observed=provider_io_calls,
                run_status=provider_run.status,
                snapshots=snapshot_count,
                eligible_snapshots=0,
                latency_aggregates=aggregate_count,
                outcomes={
                    "failed": 1 if provider_run.status == "failed" else 0,
                    "provider_fetch_attempted": 0,
                },
                provider_resolver_calls=provider_resolver_calls,
                provider_io_calls=provider_io_calls,
            )
    finally:
        engine.dispose()


def run_fault_matrix(
    *,
    profile: str = "local_fixture",
    provider: str = "mock",
) -> dict[str, object]:
    if profile not in ALLOWED_PROFILES or provider != "mock":
        raise CanaryConfigurationError("hotel_canary_requires_local_mock_profile")
    scenarios: list[dict[str, object]] = []
    cleanup_remaining = 0
    for fault_profile in sorted(load_hotel_fault_profiles()):
        with tempfile.TemporaryDirectory(prefix=f"hotel-h44-{fault_profile}-") as workspace:
            db_path = Path(workspace) / "matrix.db"
            db_url = f"sqlite:///{db_path.as_posix()}"
            scenarios.append(
                run_nominal_scenario(
                    db_url,
                    profile=profile,
                    provider=provider,
                    fault_profile=fault_profile,
                )
            )
            temporary_artifacts = (
                db_path,
                Path(f"{db_path}-wal"),
                Path(f"{db_path}-shm"),
                Path(f"{db_path}-journal"),
            )
        cleanup_remaining += sum(path.exists() for path in temporary_artifacts)
        cleanup_remaining += int(Path(workspace).exists())
    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "runner": "hotel_mock_canary",
        "mode": "fault_matrix",
        "profile": profile,
        "provider_mode": provider,
        "status": "passed" if all(item["status"] == "passed" for item in scenarios) and cleanup_remaining == 0 else "failed",
        "external_calls_expected": 0,
        "external_calls_observed": sum(_safe_int(item["external_calls_observed"]) for item in scenarios),
        "temporary_databases_remaining": cleanup_remaining,
        "cleanup_verified": cleanup_remaining == 0,
        "scenarios": scenarios,
        "known_limitations": ["fixture_only", "mock_provider_only", "no_live_provider", "sqlite_disposable_db"],
    }
    validate_evidence(report)
    return report


def run_canary(
    *,
    db_url: str | None,
    profile: str = "local_fixture",
    provider: str = "mock",
    output: str | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    if dry_run:
        if db_url is not None:
            raise CanaryConfigurationError("hotel_canary_dry_run_forbids_db_url")
        report = run_fault_matrix(profile=profile, provider=provider)
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = output_path.with_suffix(output_path.suffix + ".tmp")
            temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            temporary.replace(output_path)
        return report
    if db_url is None:
        raise CanaryConfigurationError("hotel_canary_requires_db_url")
    _validate_db_url(db_url)
    nominal_db = db_url
    kill_db = db_url.replace(".db", "-kill-switch.db") if db_url.endswith(".db") else f"{db_url}-kill-switch"
    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "runner": "hotel_mock_canary",
        "profile": profile,
        "provider_mode": provider,
        "migration_revision": MIGRATION_REVISION,
        "status": "blocked",
        "scenarios": [],
        "external_calls_expected": 0,
        "external_calls_observed": 0,
        "known_limitations": [
            "fixture_only",
            "mock_provider_only",
            "no_live_provider",
            "no_field_slo_evidence",
            "sqlite_isolated_db",
        ],
    }
    if profile not in ALLOWED_PROFILES or provider != "mock":
        raise CanaryConfigurationError("hotel_canary_requires_local_mock_profile")
    scenarios = [
        run_nominal_scenario(nominal_db, profile=profile, provider=provider),
        run_kill_switch_scenario(kill_db, profile=profile, provider=provider),
    ]
    report["scenarios"] = scenarios
    report["status"] = "passed" if all(item["status"] == "passed" for item in scenarios) else "failed"
    report["external_calls_observed"] = sum(_safe_int(item["external_calls_observed"]) for item in scenarios)
    validate_evidence(report)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output_path)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an offline, redacted hotel Mock canary")
    parser.add_argument("--db-url", help="Explicit isolated SQLite URL, e.g. sqlite:////tmp/hotel-canary.db")
    parser.add_argument("--dry-run", action="store_true", help="Run the disposable fault matrix without a caller-owned database")
    parser.add_argument("--output", help="Optional JSON evidence output path")
    parser.add_argument("--profile", default="local_fixture", choices=sorted(ALLOWED_PROFILES))
    parser.add_argument("--provider", default="mock")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = run_canary(
            db_url=args.db_url,
            profile=args.profile,
            provider=args.provider,
            output=args.output,
            dry_run=args.dry_run,
        )
    except (CanaryConfigurationError, OSError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "reason": type(exc).__name__}, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
