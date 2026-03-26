import assert from "node:assert/strict";
import test from "node:test";

import { buildDateRange, getAirportSuggestions } from "../src/modules/quick-search/utils";

test("buildDateRange returns ordered inclusive range", () => {
  assert.deepEqual(buildDateRange("2026-02-03", "2026-02-05"), ["2026-02-03", "2026-02-04", "2026-02-05"]);
});

test("buildDateRange supports reversed dates", () => {
  assert.deepEqual(buildDateRange("2026-02-05", "2026-02-03"), ["2026-02-03", "2026-02-04", "2026-02-05"]);
});

test("getAirportSuggestions ranks code matches first", () => {
  const results = getAirportSuggestions("mad", 3);
  assert.ok(results.length > 0);
  assert.equal(results[0]?.iata, "MAD");
});
