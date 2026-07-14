import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRouteSeedList,
  getAdditionalAirportFocusTarget,
} from "../src/modules/quick-search/multiple-airports";
import { buildDualSearchParams } from "../src/modules/quick-search/utils-dual";
import { getOfficialRyanairRouteDeepLink } from "../src/modules/quick-search/api/quickSearchDeepLinks";

test("buildRouteSeedList keeps the required airport and only valid optional airports", () => {
  const knownAirports = new Set(["FCO", "MXP", "MAD"]);

  const seeds = buildRouteSeedList("fco", [" mxp ", "INVALID", "FCO", "", "mad"], knownAirports);

  assert.deepEqual(seeds, ["FCO", "MXP", "MAD"]);
});

test("buildRouteSeedList keeps a country scope and appends valid optional airports", () => {
  const knownAirports = new Set(["FCO", "MXP", "MAD"]);

  const seeds = buildRouteSeedList(["FCO", "MXP"], ["mad", "MXP"], knownAirports);

  assert.deepEqual(seeds, ["FCO", "MXP", "MAD"]);
});

test("buildDualSearchParams preserves multiple origins and destinations", () => {
  const params = buildDualSearchParams({
    origin: ["FCO", "MXP"],
    destination: ["AMS", "LHR"],
    travelDate: "2026-09-18",
    flexDaysBefore: 0,
    flexDaysAfter: 0,
    radiusKm: 150,
    includeStops: false,
    includeNearbyOrigins: false,
    includeNearbyDestinations: false,
    departAfter: "",
    departBefore: "",
    maxStops: 0,
    excludeOrigins: [],
    excludeDestinations: [],
    strictFilters: true,
  });

  assert.deepEqual(params.originIata, ["FCO", "MXP"]);
  assert.deepEqual(params.destinationIata, ["AMS", "LHR"]);
});

test("additional airport removal moves focus to the next row, previous row, or add button", () => {
  const entries = [
    { id: "row-1", value: "MAD" },
    { id: "row-2", value: "BCN" },
    { id: "row-3", value: "FCO" },
  ];

  assert.equal(getAdditionalAirportFocusTarget(entries, 1), "row-3");
  assert.equal(getAdditionalAirportFocusTarget(entries, 2), "row-2");
  assert.equal(getAdditionalAirportFocusTarget(entries.slice(0, 1), 0), null);
});

test("Ryanair fallback follows the route of each cartesian result", () => {
  const fallback = getOfficialRyanairRouteDeepLink(
    "https://www.ryanair.com/es/es/trip/flights/select?originIata=FCO&destinationIata=AMS&dateOut=2026-07-20&adults=1",
    "MAD",
    "LGW",
    "2026-07-21",
  );
  const parsed = new URL(fallback);

  assert.equal(parsed.searchParams.get("originIata"), "MAD");
  assert.equal(parsed.searchParams.get("destinationIata"), "LGW");
  assert.equal(parsed.searchParams.get("dateOut"), "2026-07-21");
  assert.equal(parsed.searchParams.get("tpOriginIata"), "MAD");
  assert.equal(parsed.searchParams.get("tpDestinationIata"), "LGW");
});
