import assert from "node:assert/strict";
import test from "node:test";

import {
  adaptAreaSearchV2ToV1,
  areaSearchV2,
  HotelsRequestError,
  parseAreaSearchV2Response,
} from "@/modules/hotels/api";

const responseFixture = {
  data: [{
    hotel_id: "hotel-1",
    canonical_name: "Hotel Sol",
    city: "Madrid",
    country_code: "ES",
    stars: 4,
    distance_km: 0.2,
    price: {
      amount: 189.5,
      currency: "EUR",
      basis: "unknown",
      status: "observed",
      observed_at: null,
    },
    stay_context: {
      check_in: "2026-07-10",
      check_out: "2026-07-12",
      guests: 2,
      rooms: null,
    },
    provider: "mock",
    has_tracking: false,
    explanation: {
      primary_reason: "lowest_observed_price",
      codes: ["price_context_match"],
    },
  }],
  meta: {
    contract_version: "hotels.results.v2",
    request_id: "hotels-v2-client-001",
    generated_at: "2026-08-11T12:00:00Z",
    result_state: "success",
    query: {},
    pagination: {
      mode: "none",
      returned: 1,
      total: 1,
      has_next: false,
      next_cursor: null,
      previous_cursor: null,
      sort: "price",
    },
    freshness: {
      state: "unknown",
      observed_at: null,
      age_seconds: null,
      expires_at: null,
      mixed: false,
      requires_revalidation: false,
    },
    providers: [],
    capabilities: {},
    warnings: [],
  },
};

test("V2 area-search accepts only the declared contract and adapts it to V1", () => {
  const parsed = parseAreaSearchV2Response(responseFixture);

  assert.deepEqual(adaptAreaSearchV2ToV1(parsed), [{
    hotel_id: "hotel-1",
    canonical_name: "Hotel Sol",
    city: "Madrid",
    country_code: "ES",
    stars: 4,
    distance_km: 0.2,
    lowest_price: 189.5,
    price_basis: "unknown",
    currency: "EUR",
    provider: "mock",
    check_in: "2026-07-10",
    check_out: "2026-07-12",
    guests: 2,
    has_tracking: false,
  }]);
  assert.throws(
    () => parseAreaSearchV2Response({ data: [], meta: { contract_version: "wrong", request_id: "x" } }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
});

test("V2 area-search retains the explicit search intent", async () => {
  const originalFetch = globalThis.fetch;
  let path = "";
  let intentId: string | null = null;

  globalThis.fetch = async (input, init) => {
    path = String(input);
    intentId = new Headers(init?.headers).get("x-client-event-id");
    return new Response(JSON.stringify(responseFixture), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const payload = await areaSearchV2({
      latitude: 40.4168,
      longitude: -3.7038,
      check_in: "2026-07-10",
      check_out: "2026-07-12",
    }, undefined, "hotels-v2-intent-001");

    assert.equal(payload.meta.contract_version, "hotels.results.v2");
    assert.equal(intentId, "hotels-v2-intent-001");
    assert.match(path, /\/hotels\/v2\/area-search\?/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
