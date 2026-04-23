import assert from "node:assert/strict";
import test from "node:test";

import {
  clampQuickSearchRadius,
  mergeQuickSearchIataTokens,
  parseQuickSearchIataTokens,
  QUICK_SEARCH_RADIUS_DEFAULT,
} from "../src/modules/quick-search/filterUtils";

test("clampQuickSearchRadius keeps radius inside the canonical quick-search range", () => {
  assert.equal(clampQuickSearchRadius(0), 10);
  assert.equal(clampQuickSearchRadius(9), 10);
  assert.equal(clampQuickSearchRadius(150), 150);
  assert.equal(clampQuickSearchRadius(999), 500);
  assert.equal(clampQuickSearchRadius(Number.NaN), QUICK_SEARCH_RADIUS_DEFAULT);
});

test("parseQuickSearchIataTokens accepts valid IATA tokens only and removes duplicates", () => {
  assert.deepEqual(parseQuickSearchIataTokens("mad, BCN invalid B1B mad AGP"), ["MAD", "BCN", "AGP"]);
  assert.deepEqual(parseQuickSearchIataTokens("  dub\nlis\topo  "), ["DUB", "LIS", "OPO"]);
  assert.deepEqual(parseQuickSearchIataTokens("M A D, 12, LONG"), []);
});

test("mergeQuickSearchIataTokens preserves existing chips and appends valid new values", () => {
  assert.deepEqual(mergeQuickSearchIataTokens(["MAD"], "mad, bcn, xx, LIS"), ["MAD", "BCN", "LIS"]);
});
