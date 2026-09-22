# OpenTelemetry Runtime Proof & Verification

**Date:** 2026-09-12  
**Authority:** 05_OBSERVABILITY_ANALYTICS_COMPLETION.md  
**Target Architecture:** FastAPI OpenTelemetry Lifespan Integration

---

## 1. Entrypoint Verification

- **Module:** ackend/app/core/telemetry.py
- **Application Lifespan Invocation:** ackend/app/main.py line 127 (init_telemetry()).
- **Resource Definition:** Sets service name to iru-backend and deployment environment dynamically via environment variables.

## 2. Span Architecture & Hierarchy

The tracing instrumentation wraps core operations using 	race_operation(operation_name, attributes):

`	ext
HTTP Request
  └─ search_flights_operation
       ├─ provider_call (masked target)
       ├─ cache_lookup_and_evaluation
       └─ pricing_and_reconciliation
`

## 3. Privacy & Sensitive Data Enforcement

ackend/app/core/telemetry.py applies an active source-level filter:
- Filters out high-cardinality or sensitive keys: password, 	oken, secret, uthorization.
- Merges incoming request correlation ID (correlation.id) from pp.core.request_context.
- Records caught exceptions as standard OpenTelemetry exceptions with clamped descriptions (<= 200 chars) to prevent SQL or secret leakage in traces.

## 4. Automated Test Proof

- **Test Suite:** ackend/tests/unit/test_telemetry.py
- **Results:** 3/3 passed:
  1. 	est_telemetry_initialization: Confirms tracer provider initialization.
  2. 	est_trace_operation_attaches_correlation_id: Confirms correlation ID and environment attributes.
  3. 	est_trace_operation_sanitizes_sensitive_attributes: Proves that sensitive fields are completely omitted from span attributes.
