# PostHog Analytics Runtime Proof & Governance

**Date:** 2026-09-12  
**Authority:** iru-completion-no-docker/05_OBSERVABILITY_ANALYTICS_COMPLETION.md  
**Target Architecture:** Privacy-First Client-Side PostHog Integration

---

## 1. Lifecycle & Fail-Safe Initialization

- **Module:** rontend/src/lib/posthog.ts
- **Execution Lifecycle:** Client-side only (	ypeof window !== "undefined"), guarded by initialized singleton latch.
- **Fail-Safe Mode:** If NEXT_PUBLIC_POSTHOG_KEY is absent (local development, unit tests, staging without telemetry), all functions silently no-op without error.

## 2. Strict Event Taxonomy

Only explicitly typed product events are allowed:
1. search_initiated: origin, destination, trip_type.
2. search_completed: origin, destination, results_count, duration_ms.
3. watchlist_item_added: origin, destination, target_price.
4. watchlist_item_removed: watch_id.
5. lert_rule_created: rule_type, threshold.

## 3. Privacy & Session Replay Controls

- utocapture: false (disables uncontrolled DOM click/form capture)
- capture_pageview: false (disables unmanaged URL param tracking)
- session_recording.maskAllInputs: true (all input fields masked)
- session_recording.maskTextSelector: "*" (full text masking)
- Identity: identifyUser(userId) accepts only the anonymous/stable Supabase UUID; no raw emails or personal details are set as user properties.
- Logout: 
esetAnalytics() calls posthog.reset() to erase session identity.

## 4. Automated Test Proof

- **Test Suite:** rontend/tests/posthog-governance.test.ts
- **Results:** 2/2 passed:
  1. PostHog module executes safely in unconfigured / test environment: Confirms no-op safety.
  2. isFeatureFlagEnabled returns fallback value when unconfigured: Confirms resilient feature flagging.
