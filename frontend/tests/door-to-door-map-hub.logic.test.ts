import assert from "node:assert/strict";
import test from "node:test";

import { buildMapCapabilities, filterSavedPlacesForWatch } from "../src/modules/door-to-door/mapHub";
import type { DoorToDoorProviderStatus, DoorToDoorResponse, DoorToDoorSavedPlace } from "../src/modules/door-to-door/types";

function makeProvider(overrides: Partial<DoorToDoorProviderStatus>): DoorToDoorProviderStatus {
  return {
    name: "provider",
    enabled: false,
    status: "disabled",
    source_type: "api",
    production_ready: false,
    supports_search: false,
    supports_booking_url: false,
    has_tests: false,
    ...overrides,
  };
}

function makeResponse(overrides: Partial<DoorToDoorResponse>): DoorToDoorResponse {
  return {
    flight: {
      origin_airport: "AGP",
      destination_airport: "TSF",
      departure_at: "2026-06-14T14:20:00+02:00",
      arrival_at: "2026-06-14T16:55:00+02:00",
      flight_time_confidence: "estimated",
    },
    summary: {},
    options: [],
    warnings: [],
    ...overrides,
  };
}

test("buildMapCapabilities keeps traffic/incidents partial on degraded warnings", () => {
  const response = makeResponse({
    warnings: [{ code: "GOOGLE_ROUTES_UNAVAILABLE", message: "routes disabled" }, { code: "NO_COVERAGE", message: "no coverage" }],
  });
  const providers = [makeProvider({ name: "google_routes", enabled: true, status: "functional_maps", source_type: "maps", production_ready: true, supports_search: true })];
  const result = buildMapCapabilities(response, providers);

  const traffic = result.find((item) => item.key === "traffic");
  const incidents = result.find((item) => item.key === "incidents");
  assert.ok(traffic);
  assert.ok(incidents);
  assert.equal(traffic.state, "partial");
  assert.equal(traffic.confidence, "cached");
  assert.equal(incidents.state, "partial");
  assert.equal(incidents.confidence, "cached");
});

test("buildMapCapabilities respects backend map_capabilities as source of truth", () => {
  const response = makeResponse({
    warnings: [{ code: "GOOGLE_ROUTES_UNAVAILABLE", message: "routes disabled" }],
    map_capabilities: {
      incidents: {
        state: "available",
        source_type: "maps",
        confidence: "live",
        last_checked_at: "2026-05-27T20:00:00+02:00",
        why_missing: null,
      },
    },
  });
  const providers = [makeProvider({ name: "google_routes", enabled: true, status: "functional_maps", source_type: "maps", production_ready: true, supports_search: true })];
  const result = buildMapCapabilities(response, providers);

  const incidents = result.find((item) => item.key === "incidents");
  assert.ok(incidents);
  assert.equal(incidents.state, "available");
  assert.equal(incidents.confidence, "live");
});

test("filterSavedPlacesForWatch returns only selected watch and global items", () => {
  const savedPlaces: DoorToDoorSavedPlace[] = [
    { id: "a", label: "A", note: "", created_at: "2026-05-27T18:00:00+02:00", watch_id: "watch-a" },
    { id: "b", label: "B", note: "", created_at: "2026-05-27T18:10:00+02:00", watch_id: "watch-b" },
    { id: "g", label: "Global", note: "", created_at: "2026-05-27T18:20:00+02:00", watch_id: null },
  ];

  assert.deepEqual(
    filterSavedPlacesForWatch(savedPlaces, "watch-a").map((item) => item.id),
    ["a", "g"],
  );
  assert.deepEqual(
    filterSavedPlacesForWatch(savedPlaces, "watch-b").map((item) => item.id),
    ["b", "g"],
  );
});

test("filterSavedPlacesForWatch with empty watch shows global items only", () => {
  const savedPlaces: DoorToDoorSavedPlace[] = [
    { id: "a", label: "A", note: "", created_at: "2026-05-27T18:00:00+02:00", watch_id: "watch-a" },
    { id: "g", label: "Global", note: "", created_at: "2026-05-27T18:20:00+02:00", watch_id: null },
  ];

  assert.deepEqual(
    filterSavedPlacesForWatch(savedPlaces, "").map((item) => item.id),
    ["g"],
  );
});
