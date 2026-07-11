import assert from "node:assert/strict";
import test from "node:test";

import { normalizeQuickSearchResponse } from "../src/modules/quick-search/api/normalizeQuickSearchResponse";
import type { SearchResponseRaw } from "../src/modules/quick-search/types";

test("normalizeQuickSearchResponse keeps legacy responses compatible", () => {
  const response: SearchResponseRaw = {
    results: [
      {
        origin: "MAD",
        destination: "LIS",
        travel_date: "2026-06-01",
        departure_time_local: "09:15",
        price: 39,
        currency: "EUR",
        source: "ryanair",
      },
    ],
  };

  const normalized = normalizeQuickSearchResponse(response);
  assert.equal(normalized.results[0].ai_preferred, false);
  assert.equal(normalized.results[0].ai_preferred_reason, null);
});

test("normalizeQuickSearchResponse preserves ai preferred result metadata", () => {
  const response: SearchResponseRaw = {
    meta: {
      ai_preference: {
        enabled: true,
        source: "ai",
        preferred_result_id: "res-2",
        fallback_used: false,
      },
    },
    results: [
      {
        result_id: "res-2",
        origin: "MAD",
        destination: "LIS",
        travel_date: "2026-06-01",
        departure_time_local: "09:15",
        price: 39,
        price_total: 39,
        currency: "EUR",
        source: "ryanair",
        ai_preferred: true,
        ai_preferred_reason: "Precio recomendado por equilibrio.",
      },
    ],
  };

  const normalized = normalizeQuickSearchResponse(response);
  assert.equal(normalized.meta?.ai_preference?.preferred_result_id, "res-2");
  assert.equal(normalized.meta?.ai_preference?.source, "ai");
  assert.equal(normalized.meta?.ai_preference?.fallback_used, false);
  assert.equal(normalized.results[0].ai_preferred, true);
  assert.equal(normalized.results[0].ai_preferred_reason, "Precio recomendado por equilibrio.");
});

test("normalizeQuickSearchResponse preserves heuristic ai preference fallback metadata", () => {
  const response: SearchResponseRaw = {
    meta: {
      ai_preference: {
        enabled: true,
        source: "heuristic",
        preferred_result_id: "res-1",
        fallback_used: true,
      },
    },
    results: [
      {
        result_id: "res-1",
        origin: "MAD",
        destination: "BCN",
        travel_date: "2026-06-03",
        departure_time_local: "12:10",
        price: 42,
        currency: "EUR",
        source: "ryanair",
      },
    ],
  };

  const normalized = normalizeQuickSearchResponse(response);
  assert.equal(normalized.meta?.ai_preference?.source, "heuristic");
  assert.equal(normalized.meta?.ai_preference?.fallback_used, true);
  assert.equal(normalized.meta?.ai_preference?.preferred_result_id, "res-1");
  assert.equal(normalized.results[0].ai_preferred, false);
  assert.equal(normalized.results[0].ai_preferred_reason, null);
});

test("normalizeQuickSearchResponse tolerates fare memory source metadata", () => {
  const response: SearchResponseRaw = {
    results: [
      {
        origin: "MAD",
        destination: "DUB",
        travel_date: "2026-06-04",
        departure_time_local: "08:40",
        price: 58,
        currency: "EUR",
        source: "ryanair",
        cache_source: "shared_cache",
        source_kind: "live",
        freshness: {
          status: "fresh",
          source: "provider_cache",
          requires_revalidation: false,
        },
      },
    ],
  };

  const normalized = normalizeQuickSearchResponse(response);
  assert.equal(normalized.results[0].cache_source, "shared_cache");
  assert.equal(normalized.results[0].source_kind, "live");
  assert.equal(normalized.results[0].freshness?.source, "provider_cache");
});
