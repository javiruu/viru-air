# Canonical Environment Variables Matrix

**Authority:** LEGACY_DECOMMISSION.md + `docs/runbooks/runbook-supabase-native.md`  
**Status:** Active Canonical Specification  
**Security Policy:** Never commit secrets. Server-only secrets must never be prefixed with NEXT_PUBLIC_.

---

## 1. Backend (FastAPI & Workers)

| Variable Name | Required | Default / Example | Scope / Consumer | Description |
|---------------|----------|-------------------|------------------|-------------|
| VIRU_SUPABASE_ENV | No | dev | System / Runtime | Target hosted tier (dev, staging, production). |
| DB_URL | Yes | postgresql+psycopg://... | app/infrastructure/db/session.py | PostgreSQL connection string. Production/remote: session pooler `viru_app.<REF>@aws-0-<region>.pooler.supabase.com:5432/postgres` (see runbook-supabase-native). Local quick-start: sqlite:///./viru.db. |
| DB_POOL_SIZE | No | 10 | app/infrastructure/db/session.py | SQLAlchemy connection pool size for session mode. |
| DB_MAX_OVERFLOW | No | 20 | app/infrastructure/db/session.py | SQLAlchemy connection overflow ceiling. |
| DB_POOL_TIMEOUT_SECONDS | No | 30 | app/infrastructure/db/session.py | Seconds to wait before timing out connection acquisition. |
| DB_POOL_RECYCLE_SECONDS | No | 1800 | app/infrastructure/db/session.py | Seconds after which pool connections are refreshed. |
| SUPABASE_URL | Yes (remoto) | https://[REF].supabase.co | app/api/deps.py | Base URL of the hosted Supabase project. **Presence activates ES256/JWKS verification mode**: access tokens are checked against the project public JWKS (`/auth/v1/.well-known/jwks.json`, cached 1h). No shared JWT secret exists in this mode. |
| SUPABASE_PUBLISHABLE_KEY | No | sb_publishable_... | Scripts & admin tasks | Publishable API key for non-backend scripts that call Supabase REST/Admin surfaces. |
| SUPABASE_SECRET_KEY | No | sb_secret_... | Admin services / Migrations | Secret service-role key (backend-only), for Admin API calls from scripts. |
| SUPABASE_PROJECT_REF | No | [PROJECT_REF] | Scripts & CLI | Supabase project identifier (pooler URL, Management API). |
| SUPABASE_JWT_SECRET | No | [JWT_SECRET] | app/api/deps.py | Legacy HS256 shared secret. Only used when SUPABASE_URL is unset. Current hosted project signs ES256 — leave empty. |
| JWT_SECRET | Cond. | [LOCAL_SECRET] | app/api/deps.py | HS256 fallback for local development/tests (token minting in pytest). Required only in HS256 mode; ignored (empty secret allowed) when SUPABASE_URL is set. |
| LOG_FILE | No | logs/viru.log | app/core/logging.py | File path destination for backend logs. |
| OTEL_ENABLED | No | false | app/core/telemetry.py | Toggles OpenTelemetry runtime export. |
| OTEL_SERVICE_NAME | No | viru-backend | app/core/telemetry.py | Service name reported in OpenTelemetry spans. |

---

## 2. Frontend (Next.js & SSR)

| Variable Name | Required | Default / Example | Scope / Consumer | Description |
|---------------|----------|-------------------|------------------|-------------|
| NEXT_PUBLIC_SUPABASE_URL | Yes | https://[REF].supabase.co | src/lib/supabase/* | Hosted Supabase project URL for browser & SSR client. Must equal backend SUPABASE_URL (tokens only verify against the same project). |
| NEXT_PUBLIC_SUPABASE_ANON_KEY | Yes | sb_publishable_... | src/lib/supabase/* | Publishable anon key for Supabase Auth (login, session refresh). |
| NEXT_PUBLIC_LOCAL_API_ORIGIN | No | http://127.0.0.1:8000 | next.config.js rewrites | Origin the Next.js dev server rewrites `/api/*` to. Override when the backend runs on another port (e.g. 8001 when 8000 is taken). |
| NEXT_PUBLIC_API_URL | No | /api/v1 | src/api/mutator/custom-client.ts | Base path for FastAPI REST endpoints. |
| INTERNAL_API_URL | No | http://127.0.0.1:8000/api/v1 | Server-side SSR fetch | Base URL for server-side fetches directly to backend. Match NEXT_PUBLIC_LOCAL_API_ORIGIN when overriding the port. |
| NEXT_PUBLIC_POSTHOG_KEY | No | phc_... | src/lib/posthog.ts | Public PostHog write key (fails safely if absent). |
| NEXT_PUBLIC_POSTHOG_HOST | No | https://eu.i.posthog.com | src/lib/posthog.ts | Ingestion host for PostHog analytics. |
| NEXT_PUBLIC_GA_MEASUREMENT_ID | No | G-... | Analytics wrapper | Optional Google Analytics tag. |
| NODE_ENV | No | development | Next.js runtime | Environment execution mode (development, production, test). |
