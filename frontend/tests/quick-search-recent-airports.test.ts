import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRecentAirportSuggestions,
  dedupeRecentAirports,
  forgetRecentAirport,
  readRecentAirports,
  rememberRecentAirport,
  writeRecentAirports,
} from "../src/modules/quick-search/recentAirports";
import type { AirportIataEntry } from "../src/modules/quick-search/types";

function buildAirport(iata: string, municipality: string, name = municipality): AirportIataEntry {
  return {
    iata,
    name,
    municipality,
    country_code: "ES",
    iso_region: "ES-MD",
    type: "large_airport",
  };
}

test("dedupeRecentAirports normalizes order, casing, and limit", () => {
  assert.deepEqual(
    dedupeRecentAirports(["mad", "BCN", "MAD", " lis ", "OPO", "AGP", "SVQ", "BIO"]),
    ["MAD", "BCN", "LIS", "OPO", "AGP", "SVQ"],
  );
});

test("readRecentAirports is safe against invalid storage payloads", () => {
  const invalidStorage = {
    getItem: () => "{not-json",
    setItem: () => undefined,
  };

  assert.deepEqual(readRecentAirports(invalidStorage), []);
});

test("rememberRecentAirport moves latest selection to the front", () => {
  assert.deepEqual(
    rememberRecentAirport(["MAD", "BCN", "LIS"], "bcn"),
    ["BCN", "MAD", "LIS"],
  );
});

test("forgetRecentAirport removes one normalized recent without disturbing the rest", () => {
  assert.deepEqual(
    forgetRecentAirport(["MAD", "bcn", "LIS", "MAD"], "BCN"),
    ["MAD", "LIS"],
  );
});

test("writeRecentAirports persists normalized recents", () => {
  let stored = "";
  const storage = {
    getItem: () => stored,
    setItem: (_key: string, value: string) => {
      stored = value;
    },
  };

  const next = writeRecentAirports(["mad", "BCN", "MAD"], storage);
  assert.deepEqual(next, ["MAD", "BCN"]);
  assert.equal(stored, JSON.stringify(["MAD", "BCN"]));
});

test("buildRecentAirportSuggestions returns enriched recents and matches by city", () => {
  const airportsByIata = new Map<string, AirportIataEntry>([
    ["MAD", buildAirport("MAD", "Madrid", "Adolfo Suarez Madrid-Barajas")],
    ["BCN", buildAirport("BCN", "Barcelona", "Barcelona El Prat")],
  ]);

  const suggestions = buildRecentAirportSuggestions(["MAD", "BCN", "LIS"], airportsByIata, "barce");
  assert.deepEqual(suggestions, [{ iata: "BCN", name: "Barcelona" }]);
});

test("buildRecentAirportSuggestions falls back to IATA when airport metadata is missing", () => {
  const suggestions = buildRecentAirportSuggestions(["LIS"], new Map(), "");
  assert.deepEqual(suggestions, [{ iata: "LIS", name: "LIS" }]);
});
