# H36 Performance Baseline Implementation Plan

**Goal:** Extend the existing Playwright performance profiler so it can measure selected routes and reproducible desktop/mobile/Fast 3G profiles, especially `/hoteles`, without adding production telemetry.

**Architecture:** Preserve the current all-routes/default behavior. Add environment-driven route and profile selection to `perf_profile_playwright.cjs`, apply viewport/touch/network settings per browser context, and emit a machine-readable JSON report alongside the existing Markdown report. Keep generated evidence outside application runtime and document the exact command and limitations in H36 QA documentation.

**Tech Stack:** Node.js CommonJS, Playwright, Chromium CDP network emulation, Node test runner.

---

### Task 1: Add explicit profiler configuration helpers

**Files:**
- Modify: `frontend/scripts/perf_profile_playwright.cjs`
- Test: `frontend/tests/perf-profile-runner.test.mjs`

Add parsing for `PERF_ROUTES`, `PERF_PROFILES`, `PERF_OUTPUT_DIR`, and `PERF_JSON`. Keep all-routes and desktop behavior as defaults. Expose pure helpers for route/profile selection so configuration can be tested without starting a server.

### Task 2: Add profile-aware browser setup

**Files:**
- Modify: `frontend/scripts/perf_profile_playwright.cjs`

Support `desktop`, `mobile`, and `fast3g` profiles. Apply viewport/touch settings to the context and use Chromium CDP `Network.emulateNetworkConditions` for Fast 3G. Record the selected profile in every result row.

### Task 3: Add JSON evidence output

**Files:**
- Modify: `frontend/scripts/perf_profile_playwright.cjs`

Preserve the existing Markdown report and add a JSON report when enabled (or whenever an explicit output directory is provided). Include configuration, timestamp, per-profile/per-route metrics, final URL/status, hotel API request counts, and errors. Do not include auth tokens, query payloads, or user identifiers.

### Task 4: Document the reproducible hotel baseline command

**Files:**
- Modify: `docs/reference/frontend/hoteles-performance-web-vitals-h36.md`
- Modify: `docs/qa/qa-command-matrix.md`

Document the command using `PERF_ROUTES=/hoteles PERF_PROFILES=desktop,mobile,fast3g`, authentication prerequisites, output location, and the fact that results are lab evidence—not production Web Vitals compliance.

### Task 5: Validate

Run:

- `cd frontend && npm test -- tests/perf-profile-runner.test.mjs`
- `cd frontend && npx tsc --noEmit`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd viru-tracker && git diff --check`

If a local authenticated frontend/backend is available, run the profiler with `SKIP_SERVER=1` and inspect the generated JSON/Markdown; otherwise report that browser measurement remains environment-blocked.
