import assert from "node:assert/strict";
import test from "node:test";
import {
  identifyUser,
  initPostHog,
  isFeatureFlagEnabled,
  resetAnalytics,
  trackEvent,
} from "../src/lib/posthog";

test("PostHog module executes safely in unconfigured / test environment", () => {
  // Should never throw when NEXT_PUBLIC_POSTHOG_KEY is not set
  assert.doesNotThrow(() => initPostHog());
  assert.doesNotThrow(() =>
    trackEvent({
      name: "search_initiated",
      properties: { origin: "MAD", destination: "BCN", trip_type: "round_trip" },
    }),
  );
  assert.doesNotThrow(() => identifyUser("user-123"));
  assert.doesNotThrow(() => resetAnalytics());
});

test("isFeatureFlagEnabled returns fallback value when unconfigured", () => {
  assert.equal(isFeatureFlagEnabled("new_search_algorithm", false), false);
  assert.equal(isFeatureFlagEnabled("new_search_algorithm", true), true);
  assert.equal(isFeatureFlagEnabled("unknown_flag"), false);
});
