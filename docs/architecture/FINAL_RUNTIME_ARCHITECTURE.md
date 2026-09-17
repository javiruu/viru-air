# Final Runtime Architecture Specification

**Authority:** `08_REMOVE_LEGACY.md` & `09_FINAL_RELEASE_GATE.md`  
**Status:** Canonical Reference Architecture  
**Project:** Viru Tracker

---

## 1. Frontend Architecture

- **Core Framework:** Next.js (App Router, version 15.5.25, React 19).
- **Authentication & Sessions:** Supabase SSR Cookie Sessions via `@supabase/ssr` and `@supabase/supabase-js`. No tokens stored in `localStorage`.
- **API Client & Server State:**
  - **Contract:** OpenAPI schema (`docs/architecture/openapi.json`).
  - **Generation:** Orval 8.x generates typed TanStack Query hooks and custom client methods into `src/api/generated/`.
  - **State Management:** `@tanstack/react-query` 5.x (`QueryProvider`) manages server caching, invalidation, and deduplication.
  - **Manual REST Call Sites:** 0 undocumented manual `fetch()` calls in product code.
- **Runtime Validation:** Zod 3.x guards environment variables (`src/lib/env.ts`) and browser storage payloads at boundaries.
- **UI Primitives:** `src/components/ui/` provides shared primitives (`Button`, `Badge`, `Card`, etc.) customized to Viru's Aviation Warm-Luxe identity (`DESIGN.md`).
- **Analytics & Telemetry:** PostHog (`src/lib/posthog.ts`) initialized safely in `QueryProvider` on mount with strict, governed event taxonomy and privacy masking.
- **Quality & Release Gates:** Playwright E2E test suite (100% green), Node/tsx test runner (620 tests), TypeScript typecheck (`tsc --noEmit`), production `next build`, and Biome linter/formatter.

---

## 2. Backend Architecture

- **Core API Framework:** FastAPI (Python 3.14, Uvicorn, ASGI).
- **Authentication Authority:** Centralized verification of Supabase JWTs in `app/api/deps.py` via `get_current_user`. Custom password hashing and token minting retired.
- **Data Access & ORM:** SQLAlchemy 2.0 mapped models (`app/infrastructure/db/models.py`) with connection pooling configured for PostgreSQL.
- **Database Engine:** Supabase-managed PostgreSQL as the single runtime database authority.
- **Observability:** OpenTelemetry instrumentation initialized in FastAPI lifespan (`app/main.py`) with contextual span tracing (`app/core/telemetry.py`).
- **Domain Services & Workers:** In-process and background workers for flight revalidation, hotel sweeps, and notification delivery remain in Python.

---

## 3. Database Architecture

- **Hosting & Engine:** Supabase-managed PostgreSQL (version 15+).
- **Schema Migration Authority:** `supabase/migrations/` exclusively. Alembic retired as active DDL authority.
- **Base Application Schema:** `20260912000001_canonical_baseline_schema.sql` (62 tables, indexes, unique constraints, and foreign keys).
- **Access Control & Defense-in-Depth:** Row Level Security (RLS) enabled across all 30 user-scoped tables via `20260912000002_enable_user_rls_policies.sql`, isolating rows by `auth.uid()`.
- **Automated Verification:** Reproducible locally from zero via `supabase db reset` and verified with `supabase test db`.

---

## 4. Explicitly Rejected & Deferred Technologies

To prevent architecture drift, the following technologies were evaluated and explicitly rejected/deferred based on measured architectural needs:

1. **Drizzle ORM:** Rejected. SQLAlchemy 2.0 already provides complete, mature, battle-tested data mapping and type safety for FastAPI and background workers. Rewriting to TypeScript or Drizzle adds high churn with zero domain value.
2. **Trigger.dev / Temporal:** Rejected. Viru's background tasks (rate monitoring, revalidation sweeps, notification dispatch) are cleanly handled by existing lightweight Python worker loops and cron entrypoints. Adding distributed workflow daemons introduces unnecessary cloud/network complexity.
3. **Typesense / Elasticsearch:** Deferred. PostgreSQL text search and indexed airport/city catalogs perform sub-millisecond lookups for Viru's current volume without running additional search cluster infrastructure.
4. **Valkey / Redis as Primary DB:** Rejected. In-memory caching layers remain optional L1/L2 caches; relational business data must never reside authoritatively in key-value memory stores.

