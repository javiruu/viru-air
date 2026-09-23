# H44 Fault Matrix and Dry-Run Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the offline hotel Mock canary with a declarative fault-profile matrix and disposable `--dry-run` evidence.

**Architecture:** Enrich the existing profile manifest with bounded expected outcomes and run every profile through isolated temporary SQLite databases. Keep normal canary mode unchanged, add a dry-run mode that owns and removes its databases, and preserve the existing redacted evidence contract.

**Tech Stack:** Python, SQLAlchemy, Alembic, pytest, SQLite, JSON fixtures.

---

### Task 1: Extend the declarative profile contract — COMPLETED

**Files:**
- Modify: `backend/app/hotels/fault_profiles.py`
- Modify: `backend/app/hotels/fixtures/hotel_fault_profiles.json`
- Test: `backend/tests/unit/test_hotels_fault_profiles.py`

**Steps:**
1. Add optional bounded fields to `HotelFaultProfile`: `expected_counts` and `expected_external_calls`.
2. Validate that expected counts are non-negative integers and external calls are non-negative integers.
3. Add profile expectations for happy, empty, typed errors, sold out, deeplink invalid, ambiguous, stale, and partial profiles.
4. Keep existing profile loading behavior compatible with old manifests by defaulting missing fields.
5. Add tests for loading the matrix fields and rejecting invalid negative/non-integer values.

### Task 2: Add matrix execution to the existing canary — COMPLETED

**Files:**
- Modify: `backend/scripts/hotel_mock_canary.py`
- Test: `backend/tests/unit/test_hotel_mock_canary.py`

**Steps:**
1. Add an allowlisted profile matrix runner using the existing isolated SQLite/migration helpers.
2. Patch the Mock profile through environment configuration; never instantiate a commercial provider.
3. Capture only bounded aggregate observations: status, error code, calls, snapshots, eligible snapshots, warnings, and review flag.
4. Compare observations to declarative expectations without exposing IDs, payloads, URLs, or secrets.
5. Keep the existing nominal and kill-switch scenarios in normal canary mode.
6. Add tests for matrix coverage, zero external calls, and redacted output.

### Task 3: Implement disposable dry-run mode — COMPLETED

**Files:**
- Modify: `backend/scripts/hotel_mock_canary.py`
- Test: `backend/tests/unit/test_hotel_mock_canary.py`

**Steps:**
1. Add `--dry-run` to the CLI.
2. In dry-run mode, create one temporary SQLite file per matrix scenario under `tempfile.gettempdir()`.
3. Run the matrix and record pre/post filesystem/database cleanup status.
4. Delete each database and SQLite sidecar file in a `finally` block.
5. Reject combining `--dry-run` with a caller-owned `--db-url` to avoid surprising mutations.
6. Add a subprocess test asserting exit code zero, matrix status passed, and no dry-run database remains.

### Task 4: Update H44 evidence and roadmap — COMPLETED

**Files:**
- Modify: `docs/reference/backend/hoteles-seed-demo-fallos-h44.md`
- Modify: `docs/plans/2026-08-10-h44-revalidation-fault-profiles-plan.md`
- Modify: `docs/plans/2026-08-10-hoteles-auditoria-checklist-completa.md`
- Modify: `docs/plans/2026-08-04-hoteles-master-roadmap.md`

**Steps:**
1. Record the approved matrix/dry-run scope and its limitations.
2. Mark deterministic advanced profiles and dry-run evidence complete only after tests pass.
3. Keep browser E2E, commercial provider canary, and persisted historical matrix explicitly pending; CI orchestration is covered by the backend workflow gate.

### Task 5: Validate and review — COMPLETED

**Commands:**
- `cd backend && python -m pytest tests/unit/test_hotels_fault_profiles.py tests/unit/test_hotel_mock_canary.py -q`
- `cd backend && python -m pytest tests/unit/test_hotels*.py tests/integration/test_hotels*.py -q`
- `cd backend && python -m ruff check app/hotels/fault_profiles.py scripts/hotel_mock_canary.py tests/unit/test_hotels_fault_profiles.py tests/unit/test_hotel_mock_canary.py`
- `cd backend && python -m compileall -q app/hotels/fault_profiles.py scripts/hotel_mock_canary.py`
- `cd .. && git diff --check`

Actual result: 39 focal tests and 320 hotel-suite tests pass; all 13 matrix profiles pass with zero external calls; dry-run reports `cleanup_verified=true` and `temporary_databases_remaining=0`; expected status/run status/error/counts are compared; Ruff, compileall, and diff check are clean. The backend CI workflow is configured to run the same redacted `python scripts/hotel_mock_canary.py --dry-run` gate after the backend suite; a GitHub Actions execution remains unobserved in this local session. Browser E2E, commercial-provider canary and optional historical persistence remain outside this plan.
