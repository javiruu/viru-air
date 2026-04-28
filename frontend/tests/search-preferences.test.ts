import assert from "node:assert/strict";
import test from "node:test";

import { buildSearchPreferenceSummary, validateSearchPreferences } from "../src/modules/preferences/searchPreferences";

const copy: Record<string, string> = {
  "preferences.search.rangeError": "range {min}-{max}",
  "preferences.search.timeError": "bad time",
  "preferences.search.summaryCoverageRegional": "regional coverage",
  "preferences.search.summaryCoverageDirect": "direct coverage",
  "preferences.search.summaryTimingWindow": "time window",
  "preferences.search.summaryTimingOpen": "time open",
  "preferences.search.summaryStrictTight": "strict",
  "preferences.search.summaryStrictFlexible": "flexible",
  "preferences.search.summaryTitleRegional": "regional title",
  "preferences.search.summaryTitleDirect": "direct title",
  "preferences.search.summaryStopsOn": "stops on",
  "preferences.search.summaryStopsOff": "stops off",
};

function t(key: string, params?: Record<string, string | number>) {
  if (key === "preferences.search.rangeError") {
    return `range ${params?.min}-${params?.max}`;
  }
  return copy[key] || key;
}

test("validateSearchPreferences catches invalid radius and late-departure time", () => {
  const errors = validateSearchPreferences(
    {
      default_radius_km: 700,
      include_stops_default: false,
      include_nearby_origins_default: false,
      include_nearby_destinations_default: false,
      avoid_departure_before: "07:00",
      depart_before_default: "25:00",
      strict_filters_default: true,
      preferred_currency: "EUR",
      language: "es",
    },
    t,
  );

  assert.equal(errors.default_radius_km, "range 0-500");
  assert.equal(errors.depart_before_default, "bad time");
});

test("buildSearchPreferenceSummary describes regional flexible defaults", () => {
  const summary = buildSearchPreferenceSummary(
    {
      default_radius_km: 150,
      include_stops_default: true,
      include_nearby_origins_default: true,
      include_nearby_destinations_default: false,
      avoid_departure_before: "07:00",
      depart_before_default: "22:00",
      strict_filters_default: false,
      preferred_currency: "EUR",
      language: "es",
    },
    (key) => t(key),
  );

  assert.equal(summary.title, "regional title");
  assert.match(summary.body, /regional coverage/);
  assert.match(summary.body, /flexible/);
  assert.deepEqual(summary.chips, ["stops on", "flexible", "150 km"]);
});
