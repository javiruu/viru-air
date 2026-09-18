# Final Cutover Baseline & Freeze State

**Date:** 2026-09-12  
**Authority:** Phase 1 — `01_FREEZE_AND_BASELINE.md`  
**Repository:** `C:\Users\javiru\Desktop\viru-tracker`

---

## 1. Git Repository State

- **Branch:** `main`
- **HEAD Commit SHA:** `91e6717d9bbd43d4ba148c6a114426266fabb823`
- **Working Tree Status:** Dirty (verified pre-existing work from previous session/audits)

### Modified Files (`M`):
```text
.codex/config.toml
backend/tests/integration/test_community_trending_persistence.py
backend/tests/integration/test_notification_inbox_persistent_trending.py
frontend/next-env.d.ts
frontend/package-lock.json
frontend/package.json
frontend/src/app/layout.tsx
frontend/tsconfig.json
```

### Untracked Files (`??`):
```text
POST_MIGRATION_AUDIT.md
UNRESOLVED_RISKS.md
backend/app/core/telemetry.py
backend/scripts/audit_routes.py
backend/scripts/export_openapi.py
backend/scripts/inspect_models.py
backend/scripts/inventory_frontend.js
backend/tests/unit/test_openapi_contract.py
backend/tests/unit/test_telemetry.py
docs/architecture/FINAL_ARCHITECTURE_CHECKLIST.md
docs/architecture/adr/
docs/architecture/openapi.json
docs/audit/
docs/migration/
docs/prompts/viru-ai-context-briefing.md
frontend/biome.json
frontend/orval.config.ts
frontend/playwright.config.ts
frontend/src/api/
frontend/src/app/providers/
frontend/src/components/ui/badge.tsx
frontend/src/components/ui/button.tsx
frontend/src/components/ui/card.tsx
frontend/src/lib/env.ts
frontend/src/lib/posthog.ts
frontend/src/modules/shared/auth-schema.ts
frontend/tests/e2e/
frontend/tests/orval-client.test.ts
frontend/tests/posthog-governance.test.ts
frontend/tests/runtime-validation-zod.test.ts
frontend/tests/shadcn-ui-primitives.test.tsx
logotipo.png
supabase/
viru-final-modernization-cutover/
viru-post-migration-audit/
```

---

## 2. Runtimes, Environments & Locks

- **Node.js:** `v24.13.1`
- **npm:** `11.8.0` (`frontend/package-lock.json` present)
- **Python:** `3.14.3`
- **uv:** `0.11.26` (`backend/pyproject.toml`, `backend/uv.lock`, `backend/.venv` active)
- **Environment Files Present (Names Only):**
  - `backend/.env`
  - `backend/.env.example`
  - `frontend/.env.example`
  - `infra/.env`
  - `infra/.env.prod.example`

---

## 3. Baseline Verification Gate Results

All gates executed cleanly against current HEAD:

| Verification Gate | Command | Result | Details / Evidence |
|---|---|---|---|
| **Backend Pytest** | `pytest -q` in `backend` | **1,439 passed, 2 skipped** (0 failed) | Total 1,441 collected. 2 skipped in `test_provider_smoke.py`. Duration: 653.74s. |
| **Frontend Node/tsx Tests** | `npm test` in `frontend` | **603 passed, 17 skipped** (0 failed) | Total 620 discovered across 4 suites. Duration: ~13s. |
| **Playwright E2E** | `npx playwright test` in `frontend` | **6 passed** (0 failed) | Tests: landing-navigation (3), quick-search (2), watchlist (1). Duration: 37.7s. |
| **TypeScript Typecheck** | `npm run typecheck` in `frontend` | **0 errors** (Exit: 0) | Clean compilation with `tsc --noEmit`. |
| **ESLint** | `npm run lint` in `frontend` | **0 errors, 0 warnings** (Exit: 0) | `eslint . --max-warnings 0` clean. |
| **Biome Check** | `npx @biomejs/biome check` in `frontend` | **1,021 errors, 125 warnings, 40 infos** | Across 852 frontend files globally. Formatter & linter rules to consolidate in Phase 5. |
| **OpenAPI Contract** | `npm run api:check` in `frontend` | **Clean / Exit: 0** | Orval generated output matches OpenAPI spec; `git diff --exit-code src/api/generated` clean. |
| **Next.js Production Build** | `npm run build` in `frontend` | **Clean / Exit: 0** | Production build passes with zero bundle/route errors. |
| **npm Security Audit** | `npm audit` in `frontend` | **5 vulnerabilities** | 1 low (`esbuild`), 2 high (`fast-uri`, `sharp`), 2 critical (`maplibre-gl`, `next`). Scheduled for Phase 7. |
| **Python Security Audit** | `uvx pip-audit` in `backend` | **44 known vulnerabilities** in 7 packages | `cryptography` (6), `ecdsa` (2), `httpx2` (3), `pip` (8), `pyasn1` (6), `python-multipart` (6), `starlette` (13). Scheduled for Phase 7. |

---

## 4. Scaffold vs Real Runtime Reality

Re-verified against code:

1. **Orval:**
   - Generated client present in `frontend/src/api/generated/` (24 domain subfolders, ~151 operations).
   - Real product call sites in `frontend/src/`: **0**.
2. **TanStack Query:**
   - `QueryProvider` mounted in `frontend/src/app/layout.tsx`.
   - Real product `useQuery` / `useMutation` call sites: **0** (only inside generated files and tests).
3. **shadcn/ui:**
   - Components present: `button.tsx`, `badge.tsx`, `card.tsx` under `frontend/src/components/ui/`.
   - Real screen/feature imports: **0** (only unit tests import them).
4. **PostHog:**
   - Safe client wrapper in `frontend/src/lib/posthog.ts`.
   - Initialized in `frontend/src/app/layout.tsx`: **No** (absent).
   - Event taxonomy wired to production actions: **No**.
5. **OpenTelemetry:**
   - Module in `backend/app/core/telemetry.py`.
   - Initialized in `backend/app/main.py`: **No** (absent).
   - Tracing FastAPI routes / workers: **No**.
6. **Zod:**
   - Schemas in `frontend/src/lib/env.ts` and `frontend/src/modules/shared/auth-schema.ts`.
   - Called at runtime entrypoints: **No** (only tests call `validateEnv` / `parseStoredAuth`).
7. **Supabase:**
   - Pilot migration in `supabase/migrations/20260912000001_create_flight_watch.sql`.
   - Active runtime connection in FastAPI or Next.js: **No** (SQLite `viru.db` and Alembic remain active).
8. **Alembic:**
   - Current head: `0062_prune_legacy_expiry_indexes`.
   - 65 active migration revisions; owns schema generation in SQLite.

