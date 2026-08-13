from __future__ import annotations

import pytest

from scripts.hotel_recovery_drill import run_recovery_drill


def test_recovery_drill_restores_seeded_scope_and_reports_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local_fixture")

    report = run_recovery_drill()

    assert report["result"] == "passed"
    assert report["provider_mode"] == "mock"
    assert report["external_calls_observed"] == 0
    assert report["restore"]["schema_revision"]
    assert report["restore"]["counts"] == report["backup"]["source_counts"]
    assert report["restore"]["owner_count"] == 2
    assert report["restored_seed_marker_copied"] is True
    assert report["cleanup_verified"] is True
    assert report["observed_rto_seconds"] == report["timing_seconds"]["restore"]
    assert report["source_database_removed_after_drill"] is True
    assert report["backup_database_removed_after_drill"] is True
    assert report["restored_database_removed_after_drill"] is True
    assert "production" in " ".join(report["known_limitations"])
    assert "same_process" in " ".join(report["known_limitations"])


def test_recovery_drill_rejects_non_safe_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(ValueError, match="hotel_recovery_requires_safe_app_env"):
        run_recovery_drill()
