import assert from "node:assert/strict";
import test from "node:test";

import {
  buildQuickSearchSaveCombinationPayloads,
  buildQuickSearchSaveResultPayload,
} from "../src/modules/quick-search/api/buildSaveResultPayload";
import type { FareComparisonProfile } from "../src/modules/shared/fareComparison";
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

test("quick search save-result payload preserves exact flight legs for live tracking", () => {
  const result: SearchResult = {
    result_id: "result-live-1",
    origin: "MAD",
    destination: "FCO",
    travel_date: "2026-07-22",
    departure_time_local: "08:30",
    price: 72.5,
    currency: "EUR",
    source: "quick-search",
    legs: [
      {
        flight_num: "FR9602",
        carrier_code: "FR",
        origin_iata: "MAD",
        destination_iata: "FCO",
        dep_ts: "2026-07-22T08:30:00Z",
        arr_ts: "2026-07-22T10:55:00Z",
      },
    ],
  };

  const payload = buildQuickSearchSaveResultPayload(result);

  assert.deepEqual(payload.legs, [
    {
      flight_number: "FR9602",
      carrier_code: "FR",
      origin_iata: "MAD",
      destination_iata: "FCO",
      departure_at: "2026-07-22T08:30:00Z",
      arrival_at: "2026-07-22T10:55:00Z",
    },
  ]);
});

test("quick search save-result payload carries the comparable fare basket into watchlist", () => {
  const result: SearchResult = {
    origin: "AGP",
    destination: "DUB",
    travel_date: "2026-09-10",
    departure_time_local: "08:30",
    price: 39.99,
    currency: "EUR",
    source: "quick-search",
  };
  const fareProfile: FareComparisonProfile = {
    travelers: 1,
    extras: [
      { kind: "checked_bag_20kg", selected: true, amount_per_person: 31 },
      { kind: "insurance", selected: true, amount_per_person: 8 },
    ],
  };

  const payload = buildQuickSearchSaveResultPayload(result, { fareProfile });

  assert.deepEqual(payload.fare_profile, fareProfile);
});

test("round-trip combination keeps the fare basket for each saved leg", () => {
  const outbound: SearchResult = {
    origin: "MAD",
    destination: "FCO",
    travel_date: "2026-09-10",
    departure_time_local: "08:30",
    price: 40,
    currency: "EUR",
    source: "quick-search",
  };
  const returnResult: SearchResult = {
    ...outbound,
    origin: "FCO",
    destination: "MAD",
    travel_date: "2026-09-14",
    price: 55,
  };
  const outboundFareProfile: FareComparisonProfile = {
    travelers: 2,
    extras: [{ kind: "cabin_bag_10kg", selected: true, amount_per_person: 18 }],
  };
  const returnFareProfile: FareComparisonProfile = {
    travelers: 2,
    extras: [{ kind: "fast_track", selected: true, amount_per_person: 4 }],
  };

  const [outboundPayload, returnPayload] = buildQuickSearchSaveCombinationPayloads({
    outbound,
    returnResult,
    groupId: "round-trip-1",
    outboundFareProfile,
    returnFareProfile,
  });

  assert.deepEqual(outboundPayload.fare_profile, outboundFareProfile);
  assert.deepEqual(returnPayload.fare_profile, returnFareProfile);
  assert.equal(outboundPayload.group_id, "round-trip-1");
  assert.equal(returnPayload.group_id, "round-trip-1");
});
