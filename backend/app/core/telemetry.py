from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Status, StatusCode, Tracer

from app.core.request_context import get_correlation_id

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "viru-backend")
SERVICE_ENV = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development"))
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "false").lower() in ("1", "true", "yes")

_initialized = False


def init_telemetry() -> Tracer:
    global _initialized
    if _initialized:
        return trace.get_tracer(SERVICE_NAME)

    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "deployment.environment": SERVICE_ENV,
        }
    )

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    _initialized = True
    return trace.get_tracer(SERVICE_NAME)


def get_tracer() -> Tracer:
    return trace.get_tracer(SERVICE_NAME)


@contextmanager
def trace_operation(operation_name: str, attributes: dict[str, Any] | None = None) -> Generator[trace.Span, None, None]:
    tracer = get_tracer()
    corr_id = get_correlation_id()

    merged_attrs = {
        "service.name": SERVICE_NAME,
        "deployment.environment": SERVICE_ENV,
    }
    if corr_id:
        merged_attrs["correlation.id"] = corr_id
    if attributes:
        # Filter out high-cardinality or sensitive attributes
        for key, value in attributes.items():
            if key not in ("password", "token", "secret", "authorization"):
                merged_attrs[key] = str(value) if not isinstance(value, (int, float, bool)) else value

    with tracer.start_as_current_span(operation_name, attributes=merged_attrs) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, description=str(exc)[:200]))
            span.record_exception(exc)
            raise

