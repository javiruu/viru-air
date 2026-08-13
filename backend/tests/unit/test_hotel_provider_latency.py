from __future__ import annotations

import math

import pytest

from app.services.hotel_provider_latency import (
    measure_provider_call,
)


class Clock:
    def __init__(self, *values: float) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


def test_measures_effective_call_with_monotonic_duration_and_classified_result() -> None:
    calls = 0

    def provider_call() -> list[str]:
        nonlocal calls
        calls += 1
        return ["rate"]

    result = measure_provider_call(
        provider_call,
        provider="LOCAL",
        operation="RATES",
        classify_result=lambda value: ("empty" if not value else "success", None),
        clock=Clock(10.0, 10.125),
    )

    assert result is not None
    assert calls == 1
    assert result.value == ["rate"]
    assert result.raised is False
    assert result.sample.provider == "local"
    assert result.sample.operation == "rates"
    assert result.sample.outcome == "success"
    assert result.sample.duration_ms == 125
    assert result.sample.attempt == 1
    assert result.sample.error_code is None


def test_clock_regression_is_clamped_to_zero() -> None:
    result = measure_provider_call(
        lambda: "ok",
        provider="mock",
        operation="search",
        clock=Clock(20.0, 19.0),
    )

    assert result is not None
    assert result.sample.duration_ms == 0


def test_exception_has_terminal_safe_outcome_without_exception_text() -> None:
    def provider_call() -> None:
        raise TimeoutError('GET https://provider.test?api_key="secret"')

    result = measure_provider_call(
        provider_call,
        provider="makcorps",
        operation="revalidation",
        clock=Clock(1.0, 1.5),
    )

    assert result is not None
    assert result.value is None
    assert result.raised is True
    assert result.sample.outcome == "timeout"
    assert result.sample.error_code == "timeout"
    assert result.sample.duration_ms == 500
    assert "secret" not in repr(result)
    assert "provider.test" not in repr(result)


def test_unknown_dimensions_and_classifier_values_are_allowlisted() -> None:
    result = measure_provider_call(
        lambda: "provider-value",
        provider="user@example.com",
        operation="private-operation",
        classify_result=lambda _: ("unexpected-outcome", "raw-secret-error"),
        clock=Clock(1.0, 1.001),
    )

    assert result is not None
    assert result.sample.provider == "unknown"
    assert result.sample.operation == "unknown"
    assert result.sample.outcome == "unknown"
    assert result.sample.error_code == "unknown"


def test_overpass_provider_dimension_is_retained() -> None:
    result = measure_provider_call(
        lambda: [],
        provider="osm_overpass",
        operation="ingestion",
        clock=Clock(1.0, 1.001),
    )

    assert result is not None
    assert result.sample.provider == "osm_overpass"


def test_sample_sink_receives_safe_sample_and_sink_failure_is_ignored() -> None:
    samples = []

    result = measure_provider_call(
        lambda: ["rate"],
        provider="mock",
        operation="search",
        on_sample=samples.append,
        clock=Clock(1.0, 1.01),
    )
    assert result is not None
    assert len(samples) == 1
    assert samples[0] == result.sample

    failing_sink_result = measure_provider_call(
        lambda: "ok",
        provider="mock",
        operation="search",
        on_sample=lambda _: (_ for _ in ()).throw(RuntimeError("sink failure")),
        clock=Clock(1.0, 1.01),
    )
    assert failing_sink_result is not None
    assert failing_sink_result.value == "ok"


def test_propagated_provider_exception_still_emits_sample_and_preserves_error() -> None:
    samples = []

    def provider_call() -> None:
        raise RuntimeError("provider secret payload")

    with pytest.raises(RuntimeError, match="provider secret payload"):
        measure_provider_call(
            provider_call,
            provider="mock",
            operation="search",
            on_sample=samples.append,
            propagate_exception=True,
            clock=Clock(1.0, 1.01),
        )

    assert len(samples) == 1
    assert samples[0].outcome == "failed"
    assert samples[0].error_code == "provider_error"


def test_custom_exception_classifier_preserves_only_allowlisted_code() -> None:
    def provider_call() -> None:
        raise RuntimeError('https://provider.test?token="secret"')

    result = measure_provider_call(
        provider_call,
        provider="makcorps",
        operation="rates",
        classify_exception=lambda _: ("rate_limited", "rate_limited"),
        clock=Clock(1.0, 1.25),
    )

    assert result is not None
    assert result.sample.outcome == "rate_limited"
    assert result.sample.error_code == "rate_limited"
    assert "secret" not in repr(result)
    assert "provider.test" not in repr(result)


def test_bad_exception_classifier_falls_back_to_safe_failure() -> None:
    result = measure_provider_call(
        lambda: (_ for _ in ()).throw(RuntimeError("private exception text")),
        provider="mock",
        operation="search",
        classify_exception=lambda _: (_ for _ in ()).throw(ValueError("classifier detail")),
        clock=Clock(1.0, 1.1),
    )

    assert result is not None
    assert result.sample.outcome == "failed"
    assert result.sample.error_code == "provider_error"
    assert "private exception text" not in repr(result)
    assert "classifier detail" not in repr(result)


def test_duration_is_capped_and_non_finite_values_are_safe() -> None:
    capped = measure_provider_call(
        lambda: None,
        provider="mock",
        operation="ingestion",
        clock=Clock(0.0, 100.0),
        max_duration_ms=10,
    )
    infinite = measure_provider_call(
        lambda: None,
        provider="mock",
        operation="ingestion",
        clock=Clock(0.0, math.inf),
        max_duration_ms=10,
    )

    assert capped is not None and capped.sample.duration_ms == 10
    assert infinite is not None and infinite.sample.duration_ms == 10


def test_pre_io_skip_does_not_invoke_callback_or_create_sample() -> None:
    invoked = False

    def provider_call() -> None:
        nonlocal invoked
        invoked = True

    result = measure_provider_call(
        provider_call,
        provider="makcorps",
        operation="revalidation",
        skip_reason="skipped_budget",
    )

    assert result is None
    assert invoked is False


@pytest.mark.parametrize("skip_reason", ["skipped_mapping", "skipped_circuit", "skipped_window"])
def test_all_pre_io_skip_reasons_are_excluded(skip_reason: str) -> None:
    result = measure_provider_call(
        lambda: pytest.fail("pre-I/O skip must not invoke provider callback"),
        provider="mock",
        operation="search",
        skip_reason=skip_reason,
    )

    assert result is None


def test_invalid_bounds_and_skip_reason_fail_closed() -> None:
    with pytest.raises(ValueError, match="max_duration"):
        measure_provider_call(lambda: None, provider="mock", operation="search", max_duration_ms=0)
    with pytest.raises(ValueError, match="attempt"):
        measure_provider_call(lambda: None, provider="mock", operation="search", attempt=0)
    with pytest.raises(ValueError, match="skip_outcome"):
        measure_provider_call(
            lambda: None,
            provider="mock",
            operation="search",
            skip_reason="skipped_unknown",
        )
