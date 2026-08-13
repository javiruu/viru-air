from __future__ import annotations

from scripts.hotel_activation_audit import audit_activation_matrix, audit_case


def test_activation_matrix_is_consistent_and_redacted() -> None:
    report = audit_activation_matrix()

    assert report["status"] == "passed"
    assert len(report["cases"]) == 5
    for case in report["cases"]:
        assert case["resolver_decision_consistent"] is True
        assert case["worker_sweep_resolver"]["reason_code"]
        serialized = str(case)
        assert "MAKCORPS_API_KEY" not in serialized
        assert "user_id" not in serialized
        assert "secret" not in serialized.lower()


def test_local_fixture_sweep_off_blocks_worker_and_direct_job() -> None:
    case = audit_case(
        "test",
        {
            "HOTEL_PROFILE": "local_fixture",
            "HOTEL_PROVIDER": "mock",
            "HOTEL_FEATURE_ENABLED": "true",
            "HOTEL_SWEEP_ENABLED": "false",
            "HOTEL_GEOCODER_ENABLED": "false",
        },
    )

    assert case["worker_sweep_resolver"]["enabled"] is False
    assert case["direct_job_sweep_resolver"]["enabled"] is False
    assert case["worker_sweep_resolver"]["reason_code"] == "hotel_sweep_disabled"
    assert case["api_provider_ingestion"]["enabled"] is True


def test_production_off_blocks_external_and_keeps_read_available() -> None:
    case = audit_case(
        "test",
        {
            "HOTEL_PROFILE": "prod_off",
            "HOTEL_PROVIDER": "mock",
            "HOTEL_FEATURE_ENABLED": "true",
            "HOTEL_SWEEP_ENABLED": "true",
            "HOTEL_GEOCODER_ENABLED": "true",
        },
    )

    assert case["api_read"]["enabled"] is False
    assert case["worker_sweep_resolver"]["enabled"] is False
    assert case["worker_sweep_resolver"]["external_calls_allowed"] is False
