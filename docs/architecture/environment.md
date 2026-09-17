# Canonical Environment Variables Matrix

**Authority:** iru-completion-no-docker/07_LEGACY_DECOMMISSION.md  
**Status:** Active Canonical Specification  
**Security Policy:** Never commit secrets. Server-only secrets must never be prefixed with NEXT_PUBLIC_.

---

## 1. Backend (FastAPI & Workers)

| Variable Name | Required | Default / Example | Scope / Consumer | Description |
|---------------|----------|-------------------|------------------|-------------|
| VIRU_SUPABASE_ENV | No | dev | System / Runtime | Target hosted tier (dev, staging, production). |
| DB_URL | Yes | postgresql+psycopg://... | pp/infrastructure/db/session.py | PostgreSQL connection string to hosted Supabase (SSL required). |
| DB_POOL_SIZE | No | 10 | pp/infrastructure/db/session.py | SQLAlchemy connection pool size for session mode. |
| DB_MAX_OVERFLOW | No | 20 | pp/infrastructure/db/session.py | SQLAlchemy connection overflow ceiling. |
| DB_POOL_TIMEOUT_SECONDS | No | 30 | pp/infrastructure/db/session.py | Seconds to wait before timing out connection acquisition. |
| DB_POOL_RECYCLE_SECONDS | No | 1800 | pp/infrastructure/db/session.py | Seconds after which pool connections are refreshed. |
| SUPABASE_URL | Yes | https://[REF].supabase.co | Backend core / Auth | Base URL of the remote hosted Supabase project. |
| SUPABASE_PUBLISHABLE_KEY | Yes | sb_pub_... | Backend core / Client | Publishable / Anon API key. |
| SUPABASE_SECRET_KEY | Yes | sb_secret_... | Admin services / Migrations | Secret service-role key (backend-only). |
| SUPABASE_PROJECT_REF | Yes | [PROJECT_REF] | Scripts & CLI | Supabase project identifier. |
| SUPABASE_JWT_SECRET | No | [JWT_SECRET] | pp/api/deps.py | Supabase JWT signing secret for bearer verification. |
| JWT_SECRET | Yes | [LOCAL_SECRET] | pp/core/security.py | Internal secret for service signature fallbacks. |
| LOG_FILE | No | logs/viru.log | pp/core/logging.py | File path destination for backend logs. |
| OTEL_ENABLED | No | alse | pp/core/telemetry.py | Toggles OpenTelemetry runtime export. |
| OTEL_SERVICE_NAME | No | iru-backend | pp/core/telemetry.py | Service name reported in OpenTelemetry spans. |

---

## 2. Frontend (Next.js & SSR)

| Variable Name | Required | Default / Example | Scope / Consumer | Description |
|---------------|----------|-------------------|------------------|-------------|
| NEXT_PUBLIC_SUPABASE_URL | Yes | https://[REF].supabase.co | src/lib/supabase/* | Hosted Supabase project URL for browser & SSR client. |
| NEXT_PUBLIC_SUPABASE_ANON_KEY | Yes | sb_pub_... | src/lib/supabase/* | Publishable anon key for Supabase Auth and Data API. |
| NEXT_PUBLIC_API_URL | No | /api/v1 | src/api/mutator/custom-client.ts | Base path for FastAPI REST endpoints. |
| INTERNAL_API_URL | No | http://127.0.0.1:8000/api/v1 | Server-side SSR fetch | Base URL for server-side fetches directly to backend. |
| NEXT_PUBLIC_POSTHOG_KEY | No | phc_... | src/lib/posthog.ts | Public PostHog write key (fails safely if absent). |
| NEXT_PUBLIC_POSTHOG_HOST | No | https://eu.i.posthog.com | src/lib/posthog.ts | Ingestion host for PostHog analytics. |
| NEXT_PUBLIC_GA_MEASUREMENT_ID | No | G-... | Analytics wrapper | Optional Google Analytics tag. |
| NODE_ENV | No | development | Next.js runtime | Environment execution mode (development, production, 	est). |
