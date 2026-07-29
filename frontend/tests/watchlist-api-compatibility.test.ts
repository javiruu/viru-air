import assert from "node:assert/strict";
import test from "node:test";

import {
  createEmptyCommunityPricing,
  normalizeWatchApiResponse,
  normalizeWatchDetailApiResponse,
} from "@/modules/watchlist/watchlistApiCompatibility";

test("watchlist responses without community pricing receive the safe default", () => {
  const watch = normalizeWatchApiResponse({
    id: "watch-legacy",
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date_local: "2026-08-20",
    status: "active",
  });

  assert.deepEqual(watch.community_pricing, createEmptyCommunityPricing());
});

test("watchlist responses with null community pricing receive the safe default", () => {
  const watch = normalizeWatchApiResponse({
    id: "watch-null",
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date_local: "2026-08-20",
    status: "active",
    community_pricing: null,
  });

  assert.deepEqual(watch.community_pricing, createEmptyCommunityPricing());
});

test("legacy watchlist responses receive independent community pricing values", () => {
  const first = normalizeWatchApiResponse({
    id: "watch-first",
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date_local: "2026-08-20",
    status: "active",
  });
  const second = normalizeWatchApiResponse({
    id: "watch-second",
    origin_iata: "AGP",
    destination_iata: "DUB",
    travel_date_local: "2026-08-21",
    status: "active",
  });

  first.community_pricing.aggregate.sample_size = 7;

  assert.notEqual(first.community_pricing, second.community_pricing);
  assert.equal(second.community_pricing.aggregate.sample_size, 0);
});

test("watch detail responses preserve community pricing supplied by the backend", () => {
  const communityPricing = {
    ...createEmptyCommunityPricing(),
    eligible: true,
    trigger_reason: "purchased",
  } as const;
  const detail = normalizeWatchDetailApiResponse({
    id: "watch-current",
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date_local: "2026-08-20",
    status: "purchased",
    latest_snapshot: null,
    community_pricing: communityPricing,
  });

  assert.deepEqual(detail.community_pricing, communityPricing);
});
