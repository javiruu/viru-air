import assert from "node:assert/strict";
import test from "node:test";

import { buildQuickSearchCanonicalPayload, toQuickSearchQuery } from "../src/modules/quick-search/requestBuilder";
import { normalizeQuickSearchResults } from "../src/modules/quick-search/responseNormalizer";

test("toQuickSearchQuery keeps quick-search API contract shape", () => {
  const query = toQuickSearchQuery({
    origin_iata: ["MAD", "BCN"],
    destination_iata: "DUB",
    travel_date: "2026-03-20",
    date: "2026-03-20",
    flex_days_before: 1,
    flex_days_after: 2,
    radius_km: 150,
    include_stops: true,
    include_nearby_origins: true,
    include_nearby_destinations: false,
    depart_after: "07:00",
    depart_before: "22:00",
    max_stops: 1,
    exclude_origins: ["OPO"],
    exclude_destinations: ["STN"],
    strict_filters: false,
    soft_filters_weight: 0.6,
  });

  const params = new URLSearchParams(query);
  assert.equal(params.get("origin_iata"), "MAD,BCN");
  assert.equal(params.get("destination_iata"), "DUB");
  assert.equal(params.get("travel_date"), "2026-03-20");
  assert.equal(params.get("flex_days_before"), "1");
  assert.equal(params.get("flex_days_after"), "2");
  assert.equal(params.get("radius_km"), "150");
  assert.equal(params.get("include_stops"), "true");
  assert.equal(params.get("include_nearby_origins"), "true");
  assert.equal(params.get("include_nearby_destinations"), "false");
  assert.equal(params.get("exclude_origins"), "OPO");
  assert.equal(params.get("exclude_destinations"), "STN");
  assert.equal(params.get("strict_filters"), "false");
  assert.equal(params.get("soft_filters_weight"), "0.6");
});

test("normalizeQuickSearchResults fills fallback fields (edge case: missing ids/legs)", () => {
  const normalized = normalizeQuickSearchResults([
    {
      origin: "MAD",
      destination: "DUB",
      travel_date: "2026-03-20",
      departure_time_local: null,
      price: 42,
      currency: "EUR",
      source: "ryanair",
      stop_count: 1,
      segments: {
        legs: [
          {
            origin_iata: "MAD",
            destination_iata: "DUB",
            dep_ts: "2026-03-20T09:00:00Z",
            arr_ts: "2026-03-20T11:00:00Z",
          },
        ],
      },
    },
  ]);

  assert.equal(normalized.length, 1);
  assert.equal(normalized[0]?.result_id, "MAD-DUB-2026-03-20-0");
  assert.equal(normalized[0]?.price_total, 42);
  assert.equal(normalized[0]?.itinerary_type, "self_connect");
  assert.equal(normalized[0]?.legs?.length, 1);
});

test("buildQuickSearchCanonicalPayload maps frontend request into contract v2 body", () => {
  const payload = buildQuickSearchCanonicalPayload({
    origin_iata: ["MAD", "BCN"],
    destination_iata: "DUB",
    travel_date: "2026-03-20",
    date: "2026-03-20",
    flex_days_before: 1,
    flex_days_after: 2,
    radius_km: 150,
    include_stops: true,
    include_nearby_origins: true,
    include_nearby_destinations: false,
    depart_after: "07:00",
    depart_before: "22:00",
    max_stops: 1,
    exclude_origins: ["OPO"],
    exclude_destinations: ["STN"],
    strict_filters: false,
    soft_filters_weight: 0.6,
  });

  assert.equal(payload.origin.seed_iata, "MAD");
  assert.equal(payload.origin.include_nearby, true);
  assert.equal(payload.destination.seed_iata, "DUB");
  assert.equal(payload.travel.date, "2026-03-20");
  assert.equal(payload.travel.flex_before, 1);
  assert.equal(payload.constraints.departure_window.after, "07:00");
  assert.deepEqual(payload.constraints.exclude_origins, ["OPO"]);
  assert.equal(payload.constraints.strict_filters, false);
});

test("smoke flow: request builder + normalizer interop", () => {
  const query = toQuickSearchQuery({
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date: "2026-03-20",
    date: "2026-03-20",
    flex_days_before: 0,
    flex_days_after: 0,
    radius_km: 0,
    include_stops: false,
    include_nearby_origins: false,
    include_nearby_destinations: false,
    max_stops: 0,
    exclude_origins: [],
    exclude_destinations: [],
    strict_filters: true,
    soft_filters_weight: 0.6,
  });

  const normalized = normalizeQuickSearchResults([
    {
      origin: "MAD",
      destination: "DUB",
      travel_date: "2026-03-20",
      departure_time_local: "09:00",
      price: 59,
      currency: "EUR",
      source: "ryanair",
      itinerary_type: "direct",
      legs: [],
    },
  ]);

  assert.ok(query.includes("origin_iata=MAD"));
  assert.equal(normalized[0]?.itinerary_type, "direct");
  assert.equal(normalized[0]?.stale_data, false);
});
