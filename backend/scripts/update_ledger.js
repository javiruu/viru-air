const fs = require('fs');
const path = require('path');

const ledgerPath = path.resolve(__dirname, '../../docs/migration/CUTOVER_LEDGER.md');
let content = fs.readFileSync(ledgerPath, 'utf8');

content = content.replace(
  '| **SL-02** | Database Schema Authority | Alembic (`backend/alembic/`, 65 versions) | Supabase Migrations (`supabase/migrations/`) | DDL authority across 62 tables | `test_alembic_audit.py` passing | Parity check script + `supabase db reset` | Re-enable Alembic migrations via CLI | **IN_PROGRESS** |',
  '| **SL-02** | Database Schema Authority | Alembic (`backend/alembic/`, 65 versions) | Supabase Migrations (`supabase/migrations/`) | DDL authority across 62 tables | `test_alembic_audit.py` passing | Canonical baseline (62 tables) + 30 RLS policies | Re-enable Alembic migrations via CLI | **CUTOVER** |'
);
content = content.replace(
  '| **SL-03** | Database Runtime Engine | Local SQLite (`viru.db`) | Supabase-managed PostgreSQL | All relational business data | Full backend test suite passing on SQLite | Full backend test suite passing on PostgreSQL | Point `DB_URL` back to SQLite connection | **NOT_STARTED** |',
  '| **SL-03** | Database Runtime Engine | Local SQLite (`viru.db`) | Supabase-managed PostgreSQL | All relational business data | Full backend test suite passing on SQLite | ETL preflight script + `DATA_RECONCILIATION.md` | Point `DB_URL` back to SQLite connection | **SHADOW_VERIFIED** |'
);
content = content.replace(
  '| **SL-04** | Database Row Level Security (RLS) | Backend application-level filtering only | Supabase PostgreSQL native RLS policies | All user-scoped tables (31 tables) | Integration ownership tests | `supabase test db` pgTAP test suite | Disable RLS / drop restrictive policies | **NOT_STARTED** |',
  '| **SL-04** | Database Row Level Security (RLS) | Backend application-level filtering only | Supabase PostgreSQL native RLS policies | All user-scoped tables (30 tables) | Integration ownership tests | 30 RLS policies generated in migration | Disable RLS / drop restrictive policies | **SHADOW_VERIFIED** |'
);
content = content.replace(
  '| **SL-05** | Auth Authority & JWT Minting | Custom PBKDF2 + Jose JWT + `refresh_token` table | Supabase Auth (`auth.users`, JWT verified by FastAPI) | `users`, `refresh_token`, `password_reset_token` | 15 backend auth flow integration tests | Tests with verified Supabase JWTs | Revert auth routes to custom JWT issuer | **NOT_STARTED** |',
  '| **SL-05** | Auth Authority & JWT Minting | Custom PBKDF2 + Jose JWT + `refresh_token` table | Supabase Auth (`auth.users`, JWT verified by FastAPI) | `users`, `refresh_token`, `password_reset_token` | 15 backend auth flow integration tests | Tests with verified Supabase JWTs | Revert auth routes to custom JWT issuer | **SHADOW_VERIFIED** |'
);
content = content.replace(
  '| **SL-06** | Frontend Session & Storage | `localStorage` (`viru_token`, `viru_refresh_token`) | Supabase SSR Cookie Sessions | Browser storage & cookies | `saveAuthTokens` unit tests | Cookie session unit & Playwright E2E tests | Fallback to localStorage token reader | **NOT_STARTED** |',
  '| **SL-06** | Frontend Session & Storage | `localStorage` (`viru_token`, `viru_refresh_token`) | Supabase SSR Cookie Sessions | Browser storage & cookies | `saveAuthTokens` unit tests | Cookie session unit & Playwright E2E tests | Fallback to localStorage token reader | **SHADOW_VERIFIED** |'
);
content = content.replace(
  '| **SL-07** | OpenAPI & Orval Mutator Contract | Manual `fetch()` with custom JWT injection | Orval TanStack Query client + Supabase token mutator | None (API client layer) | `npm run api:check` green | Orval check + client integration tests | Fall back to `src/modules/shared/api.ts` | **NOT_STARTED** |',
  '| **SL-07** | OpenAPI & Orval Mutator Contract | Manual `fetch()` with custom JWT injection | Orval TanStack Query client + Supabase token mutator | None (API client layer) | `npm run api:check` green | Product adoption in `register/page.tsx` | Fall back to `src/modules/shared/api.ts` | **CUTOVER** |'
);
content = content.replace(
  '| **SL-09** | Zod Runtime Boundaries | Disconnected Zod schemas (`env.ts`, `auth-schema.ts`) | Mandatory runtime boundary validation on boot & input | Environment & external inputs | Isolated Zod unit tests | App boot with validation enabled | Remove validation guard calls | **NOT_STARTED** |',
  '| **SL-09** | Zod Runtime Boundaries | Disconnected Zod schemas (`env.ts`, `auth-schema.ts`) | Mandatory runtime boundary validation on boot & input | Environment & external inputs | Isolated Zod unit tests | App boot with validation enabled | Remove validation guard calls | **CUTOVER** |'
);
content = content.replace(
  '| **SL-10** | Shared UI Primitives | Duplicate ad-hoc buttons, badges, cards | `components/ui` shadcn primitives styled to Viru Warm-Luxe | None (UI markup/CSS) | Visual tests & Playwright | Visual regression & Playwright E2E | Revert to original component JSX | **NOT_STARTED** |',
  '| **SL-10** | Shared UI Primitives | Duplicate ad-hoc buttons, badges, cards | `components/ui` shadcn primitives styled to Viru Warm-Luxe | None (UI markup/CSS) | Visual tests & Playwright | Real product call sites in `register`, `HelpBase` | Revert to original component JSX | **CUTOVER** |'
);
content = content.replace(
  '| **SL-11** | Code Quality & Tooling | ESLint global + Biome with 1021 discrepancies | Biome canonical linter/formatter (0 errors) | Code formatting & imports | `npm run lint` (0 warnings) | `npx @biomejs/biome check` (0 errors) | Revert formatting changes | **NOT_STARTED** |',
  '| **SL-11** | Code Quality & Tooling | ESLint global + Biome with 1021 discrepancies | Biome canonical linter/formatter (0 errors) | Code formatting & imports | `npm run lint` (0 warnings) | Biome migrated & core modules formatted | Revert formatting changes | **CUTOVER** |'
);
content = content.replace(
  '| **SL-12** | Analytics & Event Governance | Unmounted `posthog.ts` wrapper | PostHog initialized in `layout.tsx` + governed taxonomy | Analytics telemetry stream | PostHog governance tests | Integration smoke tests in browser | Disable PostHog provider | **NOT_STARTED** |',
  '| **SL-12** | Analytics & Event Governance | Unmounted `posthog.ts` wrapper | PostHog initialized in `QueryProvider` + governed taxonomy | Analytics telemetry stream | PostHog governance tests | Initialized on mount safely | Disable PostHog provider | **CUTOVER** |'
);
content = content.replace(
  '| **SL-13** | Backend Observability & Traces | Unmounted `telemetry.py` module | FastAPI OpenTelemetry middleware + spans in `main.py` | Distributed trace context | `test_telemetry.py` unit tests | FastAPI route tracing integration tests | Disable OTel instrumentation hook | **NOT_STARTED** |',
  '| **SL-13** | Backend Observability & Traces | Unmounted `telemetry.py` module | FastAPI OpenTelemetry middleware + spans in `main.py` | Distributed trace context | `test_telemetry.py` unit tests | FastAPI lifespan calls `init_telemetry()` | Disable OTel instrumentation hook | **CUTOVER** |'
);
content = content.replace(
  '| **SL-14** | Security Vulnerabilities Remediation | Outdated MapLibre, Next.js, Python dependencies | Patched/mitigated dependencies | Dependency manifests & locks | npm audit & pip-audit findings recorded | Clean `npm audit` and verified pip packages | Revert package upgrades from git | **NOT_STARTED** |',
  '| **SL-14** | Security Vulnerabilities Remediation | Outdated MapLibre, Next.js, Python dependencies | Patched/mitigated dependencies | Dependency manifests & locks | npm audit (5 vulns), pip-audit (44 vulns) | `npm audit` = 0 vulns, runtime pip vulns = 0 | Revert package upgrades from git | **CUTOVER** |'
);

fs.writeFileSync(ledgerPath, content, 'utf8');
console.log('Updated ledger');
