import assert from "node:assert/strict";
import test from "node:test";

import { deriveQuickSearchVisibleResults } from "../src/modules/quick-search/state/quickSearchVisibleResults";
import type { SearchResult } from "../src/modules/quick-search/types";

function buildResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return {
    result_id: "result",
    origin: "MAD",
    destination: "DUB",
    travel_date: "2026-06-01",
    departure_time_local: "09:30",
    price: 49,
    price_total: 49,
    currency: "EUR",
    source: "ryanair",
    duration_total: 120,
    duration_total_min: 120,
    freshness_ts: "2026-06-01T09:00:00Z",
    ranking_score: 0.9,
    stale_data: false,
    itinerary_type: "direct",
    legs: [],
    ...overrides,
  };
}

test("deriveQuickSearchVisibleResults filters and sorts by price", () => {
  const results = deriveQuickSearchVisibleResults({
    results: [
      buildResult({ result_id: "expensive", price_total: 180 }),
      buildResult({ result_id: "fit-2", price_total: 75 }),
      buildResult({ result_id: "fit-1", price_total: 55 }),
    ],
    priceMin: "",
    priceMax: "100",
    durationMax: "",
    sortBy: "price",
  });

  assert.deepEqual(results.map((item) => item.result_id), ["fit-1", "fit-2"]);
});

test("deriveQuickSearchVisibleResults supports freshness sorting", () => {
  const results = deriveQuickSearchVisibleResults({
    results: [
      buildResult({ result_id: "older", freshness_ts: "2026-06-01T08:00:00Z" }),
      buildResult({ result_id: "newer", freshness_ts: "2026-06-01T10:00:00Z" }),
    ],
    priceMin: "",
    priceMax: "",
    durationMax: "",
    sortBy: "freshness",
  });

  assert.deepEqual(results.map((item) => item.result_id), ["newer", "older"]);
});
