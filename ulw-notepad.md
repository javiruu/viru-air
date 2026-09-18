# Ultrawork Notepad — Optimization & Dead Code Removal
Started: 2026-09-17

## Plan (exhaustive, atomic)
1. Delete temporary SQLite databases (tmp*.db, _tmp*.db)
2. Delete single-use migration scripts
3. Prune dead integration tests (test_auth_flow.py, etc.)
4. Verify Test Suite Execution (pytest)

## Scenarios (the contract)
1. Database Deletion: Only viru.db remains in backend/*.db
2. Scripts Deletion: Specified scripts no longer exist
3. Test Pruning: test_auth_flow.py absent, no dead routes in test_account_flow.py
4. Verification: Pytest passes without hanging

## Now (single step in progress)
- Executing Wave 1 (Tasks 1, 2, 3 in parallel)

## Todo (remaining, ordered)
- [x] 1. Delete SQLite Migration Artifacts
- [x] 2. Delete Single-Use Migration Scripts
- [x] 3. Prune Dead Integration Tests
- [x] 4. Verify Test Suite Execution

## Findings (non-obvious facts with file:line refs)
- test_auth_flow.py hangs/loops pytest and targets deleted endpoints.
- Dozens of tmp*.db and _tmp*.db leftover from SQLite era.
- Multiple single-use migration scripts in backend/scripts/ are now dead weight.

## Learnings (patterns / pitfalls for next turn)
