import posthog from "posthog-js";

/**
 * Governed PostHog analytics and feature flag wrapper for Viru Tracker.
 * Follows viru-modernization-codex/11_POSTHOG.md:
 * - Never captures raw PII, tokens, or sensitive provider payloads.
 * - Fails safely as a no-op when unconfigured (offline / local dev / tests).
 * - Enforces a strict, limited product event taxonomy.
 */

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com";

let initialized = false;

export function initPostHog(): void {
  if (typeof window === "undefined" || initialized) return;
  if (!POSTHOG_KEY) return;

  try {
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      autocapture: false, // Explicit events only, avoid accidental capture
      capture_pageview: false, // Governed manual pageviews
      session_recording: {
        maskAllInputs: true,
        maskTextSelector: "*", // Strong masking for privacy by default
      },
    });
    initialized = true;
  } catch (error) {
    console.warn("PostHog initialization failed safely:", error);
  }
}

export type ViruProductEvent =
  | {
      name: "search_initiated";
      properties: { origin: string; destination?: string; trip_type: "one_way" | "round_trip" };
    }
  | {
      name: "search_completed";
      properties: {
        origin: string;
        destination?: string;
        results_count: number;
        duration_ms: number;
      };
    }
  | {
      name: "watchlist_item_added";
      properties: { origin: string; destination: string; target_price?: number };
    }
  | { name: "watchlist_item_removed"; properties: { watch_id: string } }
  | { name: "alert_rule_created"; properties: { rule_type: string; threshold?: number } };

export function trackEvent(event: ViruProductEvent): void {
  if (typeof window === "undefined" || !POSTHOG_KEY) return;
  try {
    posthog.capture(event.name, event.properties);
  } catch {
    // Fail silently without disrupting user experience
  }
}

export function identifyUser(userId: string): void {
  if (typeof window === "undefined" || !POSTHOG_KEY) return;
  try {
    posthog.identify(userId);
  } catch {
    // Ignore
  }
}

export function resetAnalytics(): void {
  if (typeof window === "undefined" || !POSTHOG_KEY) return;
  try {
    posthog.reset();
  } catch {
    // Ignore
  }
}

export function isFeatureFlagEnabled(flag: string, fallback = false): boolean {
  if (typeof window === "undefined" || !POSTHOG_KEY) return fallback;
  try {
    const isEnabled = posthog.isFeatureEnabled(flag);
    return typeof isEnabled === "boolean" ? isEnabled : fallback;
  } catch {
    return fallback;
  }
}
