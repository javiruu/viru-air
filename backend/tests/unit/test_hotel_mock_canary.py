from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.hotel_mock_canary import (
    MIGRATION_REVISION,
    CanaryConfigurationError,
    main,
    run_canary,
    run_fault_matrix,
    validate_evidence,
)


def _db_url(tmp_path: Path, name: str = "nominal.db") -> str:
    return f"sqlite:///{(tmp_path / name).as_posix()}"


def test_mock_canary_passes_nominal_and_kill_switch_without_private_evidence(tmp_path: Path) -> None:
    report = run_canary(
        db_url=_db_url(tmp_path),
        profile="local_fixture",
        provider="mock",
    )

    assert report["status"] == "passed"
    assert report["provider_mode"] == "mock"
    assert report["migration_revision"] == "0059_hotel_tracking_lifecycle"
    assert MIGRATION_REVISION == report["migration_revision"]
    assert report["external_calls_expected"] == 0
    assert report["external_calls_observed"] == 0
    scenarios = {item["name"]: item for item in report["scenarios"]}
    assert scenarios["mock_nominal"]["status"] == "passed"
    assert scenarios["mock_nominal"]["provider_resolver_calls"] > 0
    assert scenarios["mock_nominal"]["provider_io_calls"] > 0
    assert scenarios["mock_nominal"]["outcomes"]["provider_fetch_attempted"] > 0
    assert scenarios["mock_nominal"]["external_calls_observed"] == 0
    assert scenarios["mock_nominal"]["latency_aggregate_count"] > 0
    assert scenarios["global_kill_switch"]["status"] == "passed"
    assert scenarios["global_kill_switch"]["activation_reason"] == "hotel_feature_disabled"
    assert scenarios["global_kill_switch"]["external_calls_observed"] == 0
    assert scenarios["global_kill_switch"]["provider_resolver_calls"] == 0
    assert scenarios["global_kill_switch"]["provider_io_calls"] == 0
    assert scenarios["global_kill_switch"]["outcomes"]["provider_fetch_attempted"] == 0

    serialized = json.dumps(report)
    for forbidden in ("provider_run_id", "hotel_id", "user_id", "api_key", "payload", "secret"):
        assert forbidden not in serialized


def test_mock_canary_writes_redacted_evidence_atomically(tmp_path: Path) -> None:
    output = tmp_path / "evidence" / "report.json"
    report = run_canary(db_url=_db_url(tmp_path), output=str(output))

    assert report["status"] == "passed"
    assert output.exists()
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "hotel-mock-canary-v1"
    assert not list(output.parent.glob("*.tmp"))


def test_cli_subprocess_writes_passed_evidence_in_temp_workspace(tmp_path: Path) -> None:
    db_path = tmp_path / "cli.db"
    output = tmp_path / "cli-report.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/hotel_mock_canary.py",
            "--db-url",
            f"sqlite:///{db_path}",
            "--output",
            str(output),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "passed"
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "passed"


def test_fault_matrix_covers_all_declared_profiles_without_external_calls() -> None:
    report = run_fault_matrix()

    assert report["status"] == "passed"
    assert report["mode"] == "fault_matrix"
    assert report["external_calls_expected"] == 0
    assert report["external_calls_observed"] == 0
    assert report["cleanup_verified"] is True
    assert report["temporary_databases_remaining"] == 0
    assert len(report["scenarios"]) == 13
    assert {item["status"] for item in report["scenarios"]} == {"passed"}
    assert {item["external_calls_expected"] for item in report["scenarios"]} == {0}
    assert {item["external_calls_observed"] for item in report["scenarios"]} == {0}


def test_dry_run_writes_matrix_and_rejects_caller_database(tmp_path: Path) -> None:
    output = tmp_path / "dry-run" / "report.json"
    report = run_canary(db_url=None, dry_run=True, output=str(output))

    assert report["status"] == "passed"
    assert output.exists()
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["mode"] == "fault_matrix"
    assert loaded["cleanup_verified"] is True
    assert loaded["temporary_databases_remaining"] == 0
    assert not list(output.parent.glob("*.tmp"))

    with pytest.raises(CanaryConfigurationError, match="forbids_db_url"):
        run_canary(db_url=_db_url(tmp_path, "caller-owned.db"), dry_run=True)


def test_mock_canary_rejects_live_provider_and_default_database(tmp_path: Path) -> None:
    with pytest.raises(CanaryConfigurationError, match="local_mock_profile"):
        run_canary(db_url=_db_url(tmp_path), provider="makcorps")
    with pytest.raises(CanaryConfigurationError, match="explicit_file_db"):
        run_canary(db_url="sqlite:///./viru.db")
    with pytest.raises(CanaryConfigurationError, match="isolated_db"):
        run_canary(db_url="postgresql://user:pass@localhost/db")
    with pytest.raises(CanaryConfigurationError, match="temp_workspace"):
        run_canary(db_url="sqlite:///C:/not-a-temp-workspace/hotel.db")


def test_evidence_rejects_forbidden_keys_and_large_values() -> None:
    with pytest.raises(CanaryConfigurationError, match="forbidden_evidence_key"):
        validate_evidence({"nested": {"hotel_id": "private"}})
    with pytest.raises(CanaryConfigurationError, match="value_too_large"):
        validate_evidence({"message": "x" * 501})


def test_cli_returns_nonzero_for_unsafe_provider(tmp_path: Path, capsys) -> None:
    result = main(["--db-url", _db_url(tmp_path), "--provider", "makcorps"])
    assert result == 2
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"
