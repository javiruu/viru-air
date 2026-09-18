# Final Decommission v3   Execution Ledger

| Phase | Baseline | Changes | Targeted tests | Full gates | Legacy recount | Status | Commit |
|---|---|---|---|---|---|---|---|
| 01 Database | 2 DBs, 65 Alembic revs, 40 SQLite refs | Session fail-closed, Alembic deleted, SQLite refs cleaned | test_schema_migration_authority, test_hotels_runtime_manifests, 9 invariant tests | Backend unit suite green | Alembic: 0, SQLite: 0 | DONE | local-cutover-p1 |
| 02 Auth | 2 auth authorities, 12 PBKDF2 refs, 13 JWT issuer refs, 38 refresh token refs, 4 viru_token refs | Retired PBKDF2, custom JWT/refresh issuers, viru_token, dual-auth fallback in deps.py | test_supabase_auth_negative (8 passed), test_auth_flow | Full typecheck & test pass | All legacy auth refs: 0 | DONE | local-cutover-p2 |
| 03 Frontend data | 1 Orval call, 45 apiFetch files, 82 useEffects, 6 manual fetches | Orval contract canonical, customClient mutator connected, OpenAPI drift 0 | test_openapi_contract, npm run api:check | Full typecheck & 603 frontend tests pass | OpenAPI drift: 0 | DONE | local-cutover-p3 |
| 04 RLS | 0/30 remote tables verified | RLS policy matrix generated (30 tables), safety guardrails implemented | test_production_safety_guardrail | Remote execution blocked | 30 tables mapped | FAILED | local-cutover-p4 |
| 05 Biome | 533 errors, 181 warnings, 39 infos, exit 1 | Fixed semantic errors, component props, imports, and safe rules | npm run check:biome | Exit code 0, 0 errors | Biome errors: 0 | DONE | local-cutover-p5 |
| 06 Legacy removal | 65 revs, 40 alembic refs, 32 sqlite refs, 4 pbkdf2, 13 refresh tokens | Removed Alembic directory, session SQLite fallback, PBKDF2, RefreshToken model | Baseline recount verified | All suites clean | All legacy counters: 0 | DONE | local-cutover-p6 |
| 07 Final gate | Multi-failure baseline | All architectural and code cutovers completed | All gates verified | Gate A: 1 blocker (RLS remote test) | 0 legacy remnants | FAILED | local-cutover-p7 |

Allowed phase states: `NOT_STARTED`, `IN_PROGRESS`, `DONE`, `FAILED`.

Do not use `PARTIAL`, `SHADOW`, or `DEFERRED` as a successful state.
