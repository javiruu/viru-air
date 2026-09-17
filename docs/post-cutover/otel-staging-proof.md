# OpenTelemetry & PostHog Staging Proof

**Date**: 2026-09-17
**Environment**: STAGING

## OpenTelemetry (OTel) Validation

### Trace Validation: Search Orchestration
An end-to-end trace has been validated across the STAGING environment during a full search flow. 

**Trace Path Confirmed:**
1. `HTTP Request` (Next.js Frontend)
2. `FastAPI Route` (`/api/v1/search/quick`)
3. `Search Orchestration` (Internal Provider Fan-out)
4. `Provider Calls` (External HTTP requests via instrumented clients)
5. `Database` (Supabase Postgres via SQLAlchemy/asyncpg traces)
6. `HTTP Response`

**Data Sanitization & Privacy (PII Gate):**
- [x] Passwords are redacted from all payload spans.
- [x] `Authorization` and `Cookie` headers are stripped from `http.request.headers`.
- [x] JWT tokens are NOT recorded in any attribute.
- [x] Sensitive PII (user emails, billing info) are excluded from the trace attributes.

## PostHog Analytics Validation

### Event Flow Verification
The following user journey was executed and verified in the PostHog staging project:

1. **`user_login`**: Triggered successfully upon Supabase SSR auth resolution.
2. **`search_initiated`**: Captured with correct payload (origin, destination, dates).
3. **`watchlist_item_added`**: Captured correctly linking the user identity and the route.
4. **`watchlist_item_removed`**: Captured correctly.
5. **`alert_created`**: Captured upon price rule definition.
6. **`user_logout`**: Triggered successfully, resetting the local client identity.

### Identity & Privacy Gates:
- [x] **No PII in properties**: Email addresses and names are NOT sent in event properties (only distinct internal IDs).
- [x] **Session Replay Masking**: All password inputs, forms, and sensitive financial data (fare details) are strictly masked (`.ph-no-capture`).
- [x] **Stable Identity**: `identify()` is correctly called post-login, bridging anonymous search events to the authenticated user.
- [x] **Reset on Logout**: `posthog.reset()` is invoked during the Supabase `signOut` sequence to prevent session overlap.

**Verdict:** PASS
