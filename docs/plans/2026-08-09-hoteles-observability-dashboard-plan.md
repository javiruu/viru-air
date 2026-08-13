# Hotel Observability Dashboard Implementation Plan

**Goal:** Expose the existing low-cardinality hotel metric ledger through an admin-only, responsive operational view.

**Architecture:** The page authenticates through the existing `/auth/me` flow, then consumes `/admin/hotels/observability` through `apiFetch`. Pure helpers calculate bounded summaries and query strings; the UI uses semantic HTML, existing panel/status primitives, CSS-only proportional bars, and explicit loading/error/empty states.

**Tech Stack:** Next.js 15, React 19, TypeScript, existing global CSS, `apiFetch`, node:test.

---

### Scope

- Add `/admin/hotels-observability`.
- Support the API's 1–31 day window and allowlisted provider/metric/outcome filters.
- Display aggregate totals, providers, dates, attention state, and a responsive table.
- Add Spanish/English copy and a link from Product Health.
- Do not add dependencies, backend routes, user/hotel identifiers, dashboards for non-admin users, or SLO claims.

### Validation

- Frontend TypeScript check.
- Frontend source/helper tests.
- Frontend lint/build where the existing toolchain permits.
- Backend observability regression suite and `git diff --check`.
- Independent blocker-focused review and browser smoke check when the local app is available.
