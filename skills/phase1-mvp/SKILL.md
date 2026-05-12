---
name: phase1-mvp
description: Execute and verify Phase 1 MVP closure in Viru Tracker (auth, quick search, watchlist, refresh/history, alerts, preferences) with contract alignment and targeted QA evidence.
---

# Phase 1 MVP

## When to use

Use this skill when the request is to execute, close, or verify Phase 1 in Viru Tracker.

## Inputs

1. Repo at canonical root (`viru-tracker`).
2. Canonical docs available in `/docs`.

## Workflow

1. Read `AGENTS.md`, `docs/README.md`, `docs/INDICE_UNICO.md`, `docs/DOCS_INVENTORY.md`.
2. Read `docs/specs/phase1-codex.md`.
3. Validate quick-search contract alignment against:
   - `docs/reference/backend/quick-search-contract.md`
   - `frontend/src/modules/quick-search/api/buildQuickSearchRequest.ts`
   - `backend/app/api/v1/search.py`
4. Validate operational core:
   - auth (`backend/app/api/v1/auth.py`)
   - watchlist (`backend/app/api/v1/watchlist.py`)
   - prices (`backend/app/api/v1/prices.py`)
   - alerts (`backend/app/api/v1/alerts.py`)
   - preferences (`backend/app/api/v1/preferences.py`)
5. Run target tests from `docs/specs/phase1-codex.md`.
6. Report evidence with exact test command outputs and unresolved gaps.

## Constraints

1. Do not expand scope to post-Phase-1 flags.
2. Do not treat archive docs as canonical unless needed for traceability.
3. Keep changes surgical and tied to Fase 1 Definition of Done.

## Done when

1. Fase 1 scope is explicitly aligned with canonical docs.
2. Target tests pass or failures are documented with concrete blockers.
3. Any contract-risk mismatch is documented with file references.
