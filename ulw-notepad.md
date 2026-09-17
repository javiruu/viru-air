# Ultrawork Notepad � Viru Final Modernization Sweep
Started: 2026-09-17

## Plan (exhaustive, atomic)
1. Frontend: Migrate Private Routes (4 files)
2. Frontend: Migrate Public Routes (4 files)
3. Frontend: Migrate Components/Hooks (3 files)
4. Backend: API Cleanup (delete auth.py, remove from api.py)
5. Backend: Scripts Cleanup (remove JWT refs from baseline scripts)
6. Docs: Update CURRENT_STATE.md (staging is complete)
7. Frontend: Delete Legacy API Utility (api.ts) - depends on 1, 2, 3

## Scenarios (the contract)
1. Frontend Migration: tsc --noEmit passes without any apiFetch references.
2. Backend API Cleanup: pytest passes successfully, api.py router works.
3. Backend Scripts Cleanup: scripts execute without errors.
4. Docs: CURRENT_STATE.md reflects staging accurately.

## Now (single step in progress)
- Executing Wave 1 (Parallel)

## Todo (remaining, ordered)
- [x] Task 1: Migrate Frontend Private Routes (app/(private)/layout.tsx, admin/page.tsx, admin/hotels-observability/page.tsx, admin/product-health/page.tsx)
- [x] Task 2: Migrate Frontend Public Routes (app/(public)/page.tsx, login/page.tsx, prueba/page.tsx, register/page.tsx)
- [x] Task 3: Migrate Frontend Components/Hooks (SoporteContactoClient.tsx, useDoorToDoorSearch.ts, AlertRulesWorkspace.tsx)
- [x] Task 5: Backend API Cleanup (delete auth.py, remove from api.py)
- [x] Task 6: Backend Scripts Cleanup (remove jwt_issuer_occurrences)
- [x] Task 7: Update Documentation (CURRENT_STATE.md)
- [ ] Task 4: Delete Legacy API Utility (src/modules/shared/api.ts) - AFTER tasks 1, 2, 3

## Findings (non-obvious facts with file:line refs)
- Staging environment is already linked to Supabase (ref: ttwvoliuqaqhxkkyhdvf).
- Supabase auth client is at \@/lib/supabase/client\.
- Backend \uth.py\ currently returns 410 GONE and should be deleted entirely.

## Learnings (patterns / pitfalls for next turn)
