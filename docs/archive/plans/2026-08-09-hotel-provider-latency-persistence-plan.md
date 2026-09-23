# Hotel Provider Latency Persistence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persist bounded, privacy-safe hotel provider latency aggregates by run/provider/operation/outcome without overwriting multi-operation observations.

**Architecture:** Keep `ProviderLatencySample` collection in memory during a `HotelProviderRun`, aggregate by `(provider, operation, outcome, error_code)`, and persist one row per group in a new table linked to the run. Use an additive Alembic migration compatible with SQLite/PostgreSQL and expose only bounded admin summaries; do not change `tracked_outcomes`, activate live providers, or persist per-entity data.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, SQLite/PostgreSQL, pytest, Ruff.

---

## Scope and invariants

- Persist only samples emitted by effective provider I/O.
- Pre-I/O mapping, budget, circuit and window skips create no latency row.
- Each retry is one sample and contributes to `sample_count`.
- `duration_ms` is non-negative and capped by the existing helper.
- Provider, operation, outcome and error code remain allowlisted.
- No raw exceptions, URLs, secrets, payloads, user IDs, hotel IDs, offer IDs, intents or fingerprints.
- Existing callers without a sink preserve current behavior.
- Runs without samples have no synthetic zero-latency row.
- A failure in observability persistence must not turn a successful provider call into a functional failure.

## Task 1: Add the SQLAlchemy aggregate model

**Files:**
- Modify: `backend/app/infrastructure/db/models.py`
- Test: `backend/tests/unit/test_hotel_provider_latency_persistence.py`

1. Add `HotelProviderLatencyAggregate` after `HotelProviderRun`.
2. Use UUID string primary key and nullable-safe `ForeignKey("hotel_provider_run.id", ondelete="CASCADE")`.
3. Add `provider`, `operation`, `outcome`, `error_code`, `sample_count`, `total_duration_ms`, `min_duration_ms`, `max_duration_ms`, `created_at`, `updated_at`.
4. Add a unique constraint on `(provider_run_id, provider, operation, outcome, error_code)` and indexes for `(provider_run_id)`, `(provider, operation, created_at)`.
5. Add model tests for uniqueness, non-negative values, and cascade semantics where supported.

## Task 2: Create the Alembic migration

**Files:**
- Create: `backend/alembic/versions/<next>_hotel_provider_latency_aggregate.py`
- Test: `backend/tests/unit/test_hotel_provider_infrastructure_migration.py` or a focused migration test

1. Read the current Alembic head and use it as `down_revision`; do not guess the revision.
2. Create the table, unique constraint, indexes, and foreign key with `ondelete="CASCADE"`.
3. Implement downgrade by dropping indexes, constraint and table in reverse order.
4. Run `alembic upgrade head`, inspect the table/constraint/indexes, run `alembic downgrade <previous>`, then upgrade again on a temporary SQLite DB.
5. Confirm `alembic check` remains clean.
6. Do not alter historical migrations.

## Task 3: Implement the in-memory accumulator and persistence service

**Files:**
- Modify: `backend/app/services/hotel_provider_latency.py`
- Test: `backend/tests/unit/test_hotel_provider_latency_persistence.py`

1. Add an immutable aggregate key and mutable bounded accumulator internal to the service.
2. Add `HotelProviderLatencyAccumulator.add(sample)` with allowlist/bound validation.
3. Add `snapshot()` returning deterministic aggregate payloads sorted by dimensions.
4. Add `persist_hotel_provider_latency_aggregates(db, provider_run_id, accumulator)`.
5. Use SQLite/PostgreSQL upsert semantics or select/update/insert inside the caller transaction; never commit internally.
6. Enforce maximum groups per run and maximum aggregate values; reject unsafe dimensions with `ValueError`.
7. Make persistence best-effort at the run boundary: callers can catch/log a safe internal code without exposing raw errors.
8. Test duplicate groups, multiple operations/outcomes, retries, empty accumulator, bounds, deterministic ordering, no implicit commit and redaction.

## Task 4: Connect run lifecycle persistence

**Files:**
- Modify: `backend/app/services/hotels_service.py`
- Modify: `backend/app/hotels/ingestion.py` only if a direct run wrapper needs a sink
- Test: `backend/tests/unit/test_hotels_ingestion.py`
- Test: `backend/tests/unit/test_hotels_sweep_outcomes.py`

1. Create an accumulator only when `run_hotel_sweep()` has a persisted run.
2. Pass `accumulator.add` as the effective sink to ingestion and `sweep_tracked_offers`, while preserving any caller-provided sink behavior if both are needed.
3. Persist aggregates after the run reaches a terminal state and before the final run commit.
4. Ensure success, empty and provider failure produce rows; pre-I/O budget/circuit/mapping skips do not.
5. Ensure an exception in aggregate persistence is isolated according to the approved best-effort policy and does not leak raw DB text.
6. Keep direct `HotelIngestionService` and `sweep_tracked_offers` callers non-persistent unless explicitly given a run accumulator.

## Task 5: Add bounded admin read

**Files:**
- Modify: `backend/app/services/hotel_observability_metrics.py`
- Modify: `backend/app/api/v1/admin.py`
- Test: `backend/tests/integration/test_hotel_observability_admin.py`

1. Add a read function for recent run aggregates with strict `limit` and optional allowlisted provider/operation filters.
2. Return sample count, total, min, max and derived average; never return raw `provider_run_id`.
3. Return `no_sample`/empty data honestly; do not infer zero latency.
4. Keep admin-only auth and read-only/no provider calls/no implicit commits.
5. Add tests for RBAC, bounds, filters, redaction, unknown dimensions and deterministic output.

## Task 6: Update documentation and claims

**Files:**
- Modify: `docs/plans/2026-08-09-hotel-provider-latency-contract-plan.md`
- Modify: `docs/reference/backend/hoteles-observability-e2e-h41.md`
- Modify: `docs/reference/backend/hoteles-benchmark-rate-limits-locks-cost-h37.md`
- Modify: `docs/plans/2026-08-04-hoteles-master-roadmap.md`

1. Mark persistence as implemented only after migration and tests pass.
2. Keep provider live/canary real, percentiles, dashboards RED/provider and production SLOs explicitly pending.
3. Document schema version/migration, aggregate semantics, retention caveat and absence of synthetic historical samples.

## Task 7: Full validation and independent review

Run from `backend/`:

```bash
python -m pytest tests/unit/test_hotel_provider_latency_persistence.py tests/unit/test_hotel_observability_admin.py tests/unit/test_hotels_ingestion.py tests/unit/test_hotels_sweep_outcomes.py tests/unit/test_hotels_phase8_sweep_tracked.py -q
python -m ruff check app/services/hotel_provider_latency.py app/services/hotel_observability_metrics.py app/services/hotels_service.py app/infrastructure/db/models.py tests/unit/test_hotel_provider_latency_persistence.py
python -m compileall -q app
python -m alembic check
```

Also run the temporary SQLite Alembic upgrade/downgrade roundtrip and repository `git diff --check`. Review privacy, transaction boundaries, migration reversibility, bounded reads and H37/H41 claims before closing.
