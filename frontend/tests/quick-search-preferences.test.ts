import assert from "node:assert/strict";
import test from "node:test";

import { resolveQuickSearchPreferenceDefaults } from "../src/modules/quick-search/preferences";

test("resolveQuickSearchPreferenceDefaults maps stored search preferences into quick-search defaults", () => {
  const defaults = resolveQuickSearchPreferenceDefaults({
    default_radius_km: 180,
    include_stops_default: true,
    include_nearby_origins_default: true,
    include_nearby_destinations_default: false,
    avoid_departure_before: "07:00",
    depart_before_default: "22:00",
    strict_filters_default: false,
    preferred_currency: "EUR",
    language: "es",
  });

  assert.deepEqual(defaults, {
    radiusKm: 180,
    includeStops: true,
    departAfter: "07:00",
    departBefore: "22:00",
    includeNearbyOrigins: true,
    includeNearbyDestinations: false,
    strictFilters: false,
  });
});
