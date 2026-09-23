# Hotel Detail Intent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Propagate the originating hotel-search `client_event_id` through detail, rates, and parity read requests without creating artificial provider runs.

**Architecture:** Keep the intent explicit from `useHotelSearch` through `HotelRadarPage` into `useHotelDetail` and the three hotel API functions. Each HTTP request keeps its own correlation ID while sharing the originating client event ID. Backend middleware, error envelopes, and logs already accept the header; no new persistence is introduced for read-only routes.

**Tech Stack:** Next.js/React, TypeScript, shared `apiFetchWithStatus`, FastAPI, pytest, Node test runner.

---

### Task 1: Extend the API function contracts

**Files:**
- Modify: `frontend/src/modules/hotels/api.ts`
- Test: `frontend/tests/hotels-detail-intent.test.ts`

Add optional `intentId?: string` parameters to `getHotelDetail`, `getHotelRates`, and `getHotelParity`. Preserve existing signal positions and legacy calls. Build headers only when an intent exists.

Test the actual `fetch` headers for all three calls, assert one shared intent and three distinct correlation IDs, and assert legacy callers omit `x-client-event-id`.

### Task 2: Thread the intent through the selected-detail hook

**Files:**
- Modify: `frontend/src/modules/hotels/hooks/useHotelDetail.ts`
- Modify: `frontend/src/modules/hotels/HotelRadarPage.tsx`
- Test: `frontend/tests/hotels-h36-cancellation.test.ts`

Change `useHotelDetail(selectedHotelId, intentId?)` and pass the intent to all three API calls while preserving the existing shared abort controller and `Promise.allSettled` behavior. Pass `search.intentId` from the search hook through `HotelRadarPage`.

Expose the current search intent from `useHotelSearch` without placing it in global state or localStorage. Keep it stable for the current search and replace it when a new search begins.

Add static/transport regressions that verify all three calls receive the same intent and retain cancellation wiring.

### Task 3: Verify backend read-only behavior

**Files:**
- Test: `backend/tests/integration/test_hotels_api_flow.py`
- Test: `backend/tests/unit/test_unhandled_exception_contract.py`

Add a regression that sends a valid `x-client-event-id` to detail/rates/parity and verifies the response echoes the ID while no `HotelProviderRun` is created. Add an invalid-ID case to confirm it is not echoed. Reuse existing test fixtures and do not alter service signatures.

### Task 4: Run focused validation

Run:

```bash
cd viru-tracker/frontend
npx tsc --noEmit
npm run lint
npx tsx --test tests/hotels-detail-intent.test.ts tests/hotels-search-intent.test.ts tests/hotels-h36-cancellation.test.ts

cd ../backend
python -m pytest tests/integration/test_hotels_api_flow.py tests/unit/test_unhandled_exception_contract.py -q
python -m ruff check app/api/v1/hotels.py app/core tests/integration/test_hotels_api_flow.py tests/unit/test_unhandled_exception_contract.py
```

Expected: typecheck, lint, Ruff, and all focused tests pass.

### Task 5: Review and document evidence

Run a blocker-only code review over the modified API, hook, page, and tests. Update H41 and the roadmap with the exact validated scope: detail/rates/parity are grouped by intent at browser→API, remain read-only, and still do not create provider runs or persist read requests. Run `git diff --check`.
