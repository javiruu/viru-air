import assert from "node:assert/strict";
import test from "node:test";

import {
  HOTEL_RUM_CONSENT_GRANTED,
  HOTEL_RUM_CONSENT_KEY,
  HOTEL_RUM_SCHEMA_VERSION,
  buildHotelRumMetadata,
  bucketHotelRumValue,
  classifyHotelRumDevice,
  hasHotelRumConsent,
  rateHotelRumMetric,
  shouldFlushHotelRumVisibility,
} from "@/modules/hotels/hotelRum";

test("hotel RUM consent is opt-in and uses a dedicated storage key", () => {
  const storage = new Map<string, string>();
  const adapter = {
    getItem: (key: string) => storage.get(key) ?? null,
  };

  assert.equal(hasHotelRumConsent(adapter), false);
  storage.set(HOTEL_RUM_CONSENT_KEY, HOTEL_RUM_CONSENT_GRANTED);
  assert.equal(hasHotelRumConsent(adapter), true);
});

test("hotel RUM buckets timings and CLS without preserving exact values", () => {
  assert.equal(bucketHotelRumValue("lcp", 1200), "1000-2000ms");
  assert.equal(bucketHotelRumValue("inp", 210), "0-250ms");
  assert.equal(bucketHotelRumValue("ttfb", 4200), "4000-8000ms");
  assert.equal(bucketHotelRumValue("cls", 0.12), "0.1-0.25");
  assert.equal(bucketHotelRumValue("lcp", Number.NaN), "unknown");
});

test("hotel RUM uses the documented Web Vitals ratings", () => {
  assert.equal(rateHotelRumMetric("lcp", 2500), "good");
  assert.equal(rateHotelRumMetric("lcp", 2501), "needs_improvement");
  assert.equal(rateHotelRumMetric("inp", 501), "poor");
  assert.equal(rateHotelRumMetric("cls", 0.25), "needs_improvement");
  assert.equal(rateHotelRumMetric("ttfb", 1801), "poor");
});

test("hotel RUM flushes on hidden visibility, not when returning to foreground", () => {
  assert.equal(shouldFlushHotelRumVisibility("hidden"), true);
  assert.equal(shouldFlushHotelRumVisibility("visible"), false);
  assert.equal(shouldFlushHotelRumVisibility("prerender"), false);
});

test("hotel RUM metadata is allowlisted, bucketed, and classified", () => {
  assert.equal(classifyHotelRumDevice(390), "mobile");
  assert.equal(classifyHotelRumDevice(900), "tablet");
  assert.equal(classifyHotelRumDevice(1440), "desktop");

  const metadata = buildHotelRumMetadata("lcp", 1200, {
    navigationType: "reload",
    viewportWidth: 390,
  });

  assert.deepEqual(metadata, {
    schema_version: HOTEL_RUM_SCHEMA_VERSION,
    surface: "hoteles",
    metric: "lcp",
    value_bucket: "1000-2000ms",
    rating: "good",
    navigation_type: "reload",
    device_class: "mobile",
  });
  assert.equal("value" in (metadata ?? {}), false);
  assert.equal(buildHotelRumMetadata("cls", -1), null);
});
