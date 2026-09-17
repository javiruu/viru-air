import pytest
from app.core.telemetry import init_telemetry, trace_operation, get_tracer
from app.core.request_context import set_correlation_id
from opentelemetry.trace import StatusCode

def test_telemetry_initialization():
    tracer = init_telemetry()
    assert tracer is not None
    assert get_tracer() is not None

def test_trace_operation_success_and_redaction():
    token = set_correlation_id("test-corr-12345678")
    try:
        with trace_operation("search.quick.test", {"provider": "ryanair", "token": "secret_123"}) as span:
            assert span is not None
            assert span.is_recording() is not None
    finally:
        set_correlation_id("")

def test_trace_operation_error_handling():
    with pytest.raises(ValueError, match="simulated failure"):
        with trace_operation("failing.operation") as span:
            raise ValueError("simulated failure")

