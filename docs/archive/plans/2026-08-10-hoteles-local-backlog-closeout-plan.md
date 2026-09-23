# Hoteles Local Backlog Closeout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the remaining locally verifiable hotel backlog without enabling commercial providers or claiming production readiness.

**Architecture:** Preserve the existing V1 API and database shape while enforcing invariants at service boundaries. First harden tracked-offer context and lifecycle mutations, then verify frontend request cancellation and URL/search state behavior. Generate redacted evidence and update H04/H09/H13/H23-H29/H36-H41/H46/H48/H56 only for behavior actually verified locally.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, pytest, Next.js, TypeScript, tsx tests.

---

### Task 1: Establish the tracking invariants with regression tests

**Files:**
- Modify: `backend/tests/unit/test_hotels_phase7_track_offer.py`
- Modify: `backend/tests/integration/test_hotels_api_flow.py`

**Steps:**
1. Add tests for rejecting a partial stay context when creating a tracked offer: check-in and check-out must be supplied together, checkout must be after check-in, guests must be positive, and a price must be present for an active tracking.
2. Add a test that changing identity fields (`check_in`, `check_out`, `guests`, `provider`, room/meal/cancellation context) through PATCH is rejected with a stable validation code.
3. Add a test that non-identity updates (`target_price`, `is_active`) remain supported.
4. Run the focused tracking tests and confirm the new tests fail before implementation.

### Task 2: Enforce tracking invariants in the backend service

**Files:**
- Modify: `backend/app/services/hotels_service.py`
- Modify: `backend/app/api/v1/hotels.py` only if error translation needs a stable code

**Steps:**
1. Add one private validation helper near the tracked-offer service functions.
2. Reject incomplete dates, invalid date order, non-positive guests, unsupported/empty provider, invalid currency, negative prices, and active offers without a complete price/context.
3. Keep legacy-compatible nullable fields only for inactive/pending records; do not label those records active.
4. Reject PATCH identity mutations so historical snapshots and alert baselines cannot be silently mixed.
5. Preserve target-price and active-state updates.
6. Add unit tests for every stable validation code and re-run focused tests.

### Task 3: Verify frontend cancellation and hotel URL/search state

**Files:**
- Inspect/modify: `frontend/src/modules/shared/api.ts`
- Inspect/modify: `frontend/src/modules/hotels/api.ts`
- Modify/add: focused frontend tests under `frontend/tests/`

**Steps:**
1. Add a focused test proving a caller-provided AbortSignal remains authoritative when no timeout is configured and returns `ABORTED`.
2. Add a focused test proving timeout and caller cancellation remain distinguishable when a timeout is configured.
3. Verify hotel API methods pass their signal through without replacement and URL state remains canonical.
4. Only change implementation if a focused regression exposes a real issue.

### Task 4: Update evidence and canonical status conservatively

**Files:**
- Create/update: `docs/qa/evidence/hotels-local-backlog-closeout-current/`
- Update: relevant H23/H25/H29/H36/H41/H46/H48/H56 documents

**Steps:**
1. Record only local test/evidence results and the dirty-worktree/base-commit provenance.
2. Keep provider live, production scheduler, distributed leases, external delivery, production RUM, human cross-browser, legal approval, and annual approval open.
3. Remove contradictory stale claims only where the new tests prove the local behavior.

### Task 5: Final validation and review

**Commands:**
- `cd backend && python -m pytest ... -q`
- `cd frontend && npx tsx --test ... && npx tsc --noEmit && npx eslint ...`
- `cd backend && python -m alembic upgrade head && python -m alembic check` against a temporary SQLite database
- `python scripts/hotel_mock_canary.py --dry-run`
- `APP_ENV=local_fixture python scripts/hotel_recovery_drill.py`
- `git diff --check`

**Exit criteria:** all focused suites pass, local evidence is redacted and reproducible, and remaining blockers are explicitly external or approval-dependent.
