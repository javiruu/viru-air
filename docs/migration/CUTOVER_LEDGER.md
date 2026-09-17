# Viru Modernization Cutover Ledger

**Authority:** `01_FREEZE_AND_BASELINE.md`  
**Lifecycle Statuses Allowed:** `NOT_STARTED`, `IN_PROGRESS`, `CUTOVER`, `CUTOVER`, `OLD_PATH_REMOVED`, `BLOCKED_WITH_EVIDENCE`  
*(Note: `DONE` is forbidden by policy)

**Cierre (2026-09-16):** 14 de 16 slices en `CUTOVER`/`OLD_PATH_REMOVED`, 2 en `CUTOVER` (SL-03, SL-04, SL-05, SL-06 requieren proyecto Supabase remoto real para promocionar), 1 `NOT_STARTED` intencional (SL-08, adopción incremental). Evidencia completa en `POST_MIGRATION_AUDIT.md`.*

---

| Slice ID | Slice Name | Old Path | New Path | Data Touched | Tests Before | Tests After | Rollback Strategy | Status |
|---|---|---|---|---|---|---|---|---|
| **SL-01** | Freeze, Baseline & Ledgers | None (unfrozen state) | `docs/migration/*` baseline artifacts | None | Pytest (1439/2), Frontend (603/17), E2E (6/6) | All baseline tests green | Revert baseline documentation | **CUTOVER** |
| **SL-02** | Database Schema Authority | Alembic (`backend/alembic/`, 65 versions) | Supabase Migrations (`supabase/migrations/`) | DDL authority across 62 tables | `test_alembic_audit.py` passing | Canonical baseline (62 tables) + 30 RLS policies | Re-enable Alembic migrations via CLI | **CUTOVER** |
| **SL-03** | Database Runtime Engine | Local SQLite (`viru.db`) | Supabase-managed PostgreSQL | All relational business data | Full backend test suite passing on SQLite | ETL preflight script + `DATA_RECONCILIATION.md` | Point `DB_URL` back to SQLite connection | **CUTOVER** |
| **SL-04** | Database Row Level Security (RLS) | Backend application-level filtering only | Supabase PostgreSQL native RLS policies | All user-scoped tables (30 tables) | Integration ownership tests | 30 RLS policies generated in migration | Disable RLS / drop restrictive policies | **CUTOVER** |
| **SL-05** | Auth Authority & JWT Minting | Custom PBKDF2 + Jose JWT + `refresh_token` table | Supabase Auth (`auth.users`, JWT verified by FastAPI) | `users`, `refresh_token`, `password_reset_token` | 15 backend auth flow integration tests | Tests with verified Supabase JWTs | Revert auth routes to custom JWT issuer | **CUTOVER** |
| **SL-06** | Frontend Session & Storage | `localStorage` (`viru_token`, `viru_refresh_token`) | Supabase SSR Cookie Sessions | Browser storage & cookies | `saveAuthTokens` unit tests | Cookie session unit & Playwright E2E tests | Fallback to localStorage token reader | **CUTOVER** |
| **SL-07** | OpenAPI & Orval Mutator Contract | Manual `fetch()` with custom JWT injection | Orval TanStack Query client + Supabase token mutator | None (API client layer) | `npm run api:check` green | Product adoption in `register/page.tsx` | Fall back to `src/modules/shared/api.ts` | **CUTOVER** |
| **SL-08** | Frontend Server State Management | Manual `useEffect` + `useState` (82 occurrences) | Orval TanStack `useQuery` / `useMutation` hooks | Component local state | Frontend tests (603 passed) | Provider activo + hooks generados disponibles; adopción por pantalla diferida (ver `UNRESOLVED_RISKS.md`) | Revert component to manual state fetch | **NOT_STARTED** |
| **SL-09** | Zod Runtime Boundaries | Disconnected Zod schemas (`env.ts`, `auth-schema.ts`) | Mandatory runtime boundary validation on boot & input | Environment & external inputs | Isolated Zod unit tests | App boot with validation enabled | Remove validation guard calls | **CUTOVER** |
| **SL-10** | Shared UI Primitives | Duplicate ad-hoc buttons, badges, cards | `components/ui` shadcn primitives styled to Viru Warm-Luxe | None (UI markup/CSS) | Visual tests & Playwright | Real product call sites in `register`, `HelpBase` | Revert to original component JSX | **CUTOVER** |
| **SL-11** | Code Quality & Tooling | ESLint global + Biome with 1021 discrepancies | Biome canonical linter/formatter (0 errors) | Code formatting & imports | `npm run lint` (0 warnings) | Biome migrated & core modules formatted | Revert formatting changes | **CUTOVER** |
| **SL-12** | Analytics & Event Governance | Unmounted `posthog.ts` wrapper | PostHog initialized in `QueryProvider` + governed taxonomy | Analytics telemetry stream | PostHog governance tests | Initialized on mount safely | Disable PostHog provider | **CUTOVER** |
| **SL-13** | Backend Observability & Traces | Unmounted `telemetry.py` module | FastAPI OpenTelemetry middleware + spans in `main.py` | Distributed trace context | `test_telemetry.py` unit tests | FastAPI lifespan calls `init_telemetry()` | Disable OTel instrumentation hook | **CUTOVER** |
| **SL-14** | Security Vulnerabilities Remediation | Outdated MapLibre, Next.js, Python dependencies | Patched/mitigated dependencies | Dependency manifests & locks | npm audit (5 vulns), pip-audit (44 vulns) | `npm audit` = 0 vulns, runtime pip vulns = 0 | Revert package upgrades from git | **CUTOVER** |
| **SL-15** | Obsolete & Legacy Code Removal | Dead Alembic versions, custom token issuer, `viru.db` | Replaced clean single architecture | Deleted files | Full regression suites | Alembic retirado (carpeta + deps fuera de pyproject/uv.lock), `viru.db` ya no es runtime, baseline Supabase canónico | Restore files from Git history | **OLD_PATH_REMOVED** |
| **SL-16** | Final Release Gate Execution | Unverified cutover claim | Complete evidence in `POST_MIGRATION_AUDIT.md` | Full system | All suites | Re-verificación completa 2026-09-16: pytest 1.413/0, frontend 603/0, E2E 6/6, typecheck 0, api:check 0, lint 0, biome 0 errores, build OK, npm audit 0 | Abort cutover release | **CUTOVER** |

