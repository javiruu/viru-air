import assert from "node:assert/strict";
import test from "node:test";

import { buildQuickSearchSaveResultPayload } from "../src/modules/quick-search/api/buildSaveResultPayload";
import type { SearchResult } from "../src/modules/quick-search/types";

test("quick search save-result payload carries freshness and revalidation metadata", () => {
  const result: SearchResult = {
    result_id: "result-1",
    origin: "LEI",
    destination: "DUB",
    travel_date: "2026-06-14",
    departure_time_local: "08:25",
    price: 52,
    price_total: 49,
    currency: "EUR",
    source: "quick-search",
    duration_total_min: 180,
    stop_count: 0,
    minutes_buffer: 75,
    distance_km_ground: 1880,
    ranking_score: 91,
    freshness_ts: "2026-06-14T08:00:00Z",
    stale_data: false,
    freshness: {
      status: "warm",
      requires_revalidation: true,
      validation_status: "seen",
    },
    itinerary_type: "one_way",
  };

  const payload = buildQuickSearchSaveResultPayload(result, {
    jobId: "job-1",
    fallbackDeepLinkUrl: "https://example.test/fallback",
    groupId: "group-1",
  });

  assert.deepEqual(payload, {
    job_id: "job-1",
    result_id: "result-1",
    origin_iata: "LEI",
    destination_iata: "DUB",
    travel_date: "2026-06-14",
    price_total: 49,
    currency: "EUR",
    freshness_status: "warm",
    requires_revalidation: true,
    validation_status: "seen",
    duration_total: 180,
    stop_count: 0,
    minutes_buffer: 75,
    distance_km_ground: 1880,
    ranking_score: 91,
    freshness_ts: "2026-06-14T08:00:00Z",
    deeplink_url: "https://example.test/fallback",
    itinerary_type: "one_way",
    group_id: "group-1",
  });
});
