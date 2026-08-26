# Purchased Watch Daily Tracking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep a watch marked `purchased` visible as Comprado while it continues to receive daily price checks and changed-price snapshots.

**Architecture:** `purchased` remains a community-pricing state but joins `active` as a trackable watch state. A shared backend predicate will drive the existing scheduled route checks, startup scheduling, and manual refresh. The ticket replaces pause/resume with a Comprado indicator and retains delete.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite/PostgreSQL-compatible revalidation jobs, Next.js, React, TypeScript, CSS, pytest, Node test runner, Playwright.

---

### Task 1: Make purchased watches trackable

**Files:**
- Modify: `backend/app/domain/vocabulary.py`
- Modify: `backend/app/services/watchlist_revalidation.py`
- Modify: `backend/app/api/v1/watchlist.py`
- Test: `backend/tests/unit/test_watchlist_startup_refresh_regression.py`
- Test: `backend/tests/unit/test_watchlist_manual_revalidation.py`

1. Write failing coverage that a purchased watch is selected by startup refresh and accepted by `POST /watchlist/{id}/refresh-now`.
2. Add the smallest shared trackable-status predicate for `active` and `purchased`; keep paused and deleted excluded.
3. Run both focused suites and confirm they pass.

### Task 2: Retain the existing daily route-check cadence

**Files:**
- Modify: `backend/app/services/watchlist_revalidation.py`
- Test: `backend/tests/unit/test_watchlist_startup_refresh_regression.py`

1. Cover that the existing scheduled route selection includes purchased watches.
2. Reuse the current queue, deduplication and invariant-price persistence behavior rather than adding a second scheduler.
3. Verify price-invariant refreshes still do not create duplicate snapshots.

### Task 3: Express Comprado in the existing ticket actions

**Files:**
- Modify: `frontend/src/modules/watchlist/components/WatchRow.tsx`
- Modify: `frontend/src/styles/screens.css`
- Test: `frontend/tests/watchlist-w3-contextual-actions.test.ts`

1. Write a failing source-level test for a purchased action indicator and retained `onDelete` action.
2. Render a compact non-interactive Comprado treatment in the existing action group exclusively for purchased watches; do not alter unrelated ticket geometry or introduce new global tokens.
3. Preserve pause/resume for active and paused watches, and delete for every non-deleted watch.

### Task 4: Verify and publish

**Files:**
- Modify: `docs/DOCS_INVENTORY.md`

1. Run the focused backend tests, the watchlist frontend tests, and the frontend build/type checks appropriate to the files changed.
2. In `/watchlist`, verify a purchased ticket in dark and light themes at desktop and mobile widths: Comprado replaces pause/resume, delete remains usable, no overflow occurs, and refresh succeeds.
3. Review the scoped diff, stage only these files, commit with `fix: keep purchased watches tracking daily`, and push to `main`.
