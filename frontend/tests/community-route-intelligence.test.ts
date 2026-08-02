import assert from "node:assert/strict";
import test from "node:test";

import {
  fetchCommunityRouteInsights,
  normalizePopularRoutesResponse,
  normalizeRelatedRoutesResponse,
  normalizeRouteInsightsResponse,
} from "../src/modules/community-routes/communityRoutesApi";

test("community route responses normalize public aggregate data at the boundary", () => {
  const popular = normalizePopularRoutesResponse({
    window_days: 7,
    routes: [{ origin_iata: " mad ", destination_iata: "bcn", searches_count: 12.9, is_trending: true }],
  });
  const insights = normalizeRouteInsightsResponse({
    routes: [{
      origin_iata: "MAD",
      destination_iata: "BCN",
      searches_count: 12,
      is_trending: true,
      sample_size: 3,
      min_price: 45,
      max_price: 78,
    }],
  });

  assert.deepEqual(popular, {
    window_days: 7,
    routes: [{ origin_iata: "MAD", destination_iata: "BCN", searches_count: 12, is_trending: true }],
  });
  assert.deepEqual(
    normalizePopularRoutesResponse({
      window_days: 99,
      routes: [{ origin_iata: "MAD", destination_iata: "BCN", searches_count: 12 }],
    }).routes,
    [],
  );
  assert.equal(insights.routes[0]?.currency, "EUR");
  assert.equal(insights.routes[0]?.min_price, 45);
});

test("community route normalizers reject malformed and private related rows", () => {
  assert.deepEqual(normalizePopularRoutesResponse({ routes: [{ origin_iata: "M", destination_iata: "BCN" }] }).routes, []);
  assert.deepEqual(normalizeRouteInsightsResponse(null).routes, []);
  assert.deepEqual(
    normalizeRouteInsightsResponse({
      routes: [{
        origin_iata: "MAD",
        destination_iata: "BCN",
        searches_count: 2,
        sample_size: 2,
        min_price: null,
        max_price: null,
      }],
    }).routes[0],
    {
      origin_iata: "MAD",
      destination_iata: "BCN",
      searches_count: 2,
      is_trending: false,
      sample_size: 0,
      min_price: null,
      max_price: null,
      currency: "EUR",
    },
  );
  assert.deepEqual(
    normalizeRelatedRoutesResponse({
      routes: [
        { origin_iata: "MAD", destination_iata: "LIS", travelers_count: 2 },
        { origin_iata: "MAD", destination_iata: "OPO", travelers_count: 3 },
      ],
    }).routes,
    [{ origin_iata: "MAD", destination_iata: "OPO", travelers_count: 3 }],
  );
});

test("community route insights batch requests at the backend limit", async () => {
  const originalFetch = globalThis.fetch;
  const batchSizes: number[] = [];
  globalThis.fetch = async (_input, init) => {
    const body = JSON.parse(String(init?.body)) as {
      routes: Array<{ origin_iata: string; destination_iata: string }>;
    };
    batchSizes.push(body.routes.length);
    return new Response(JSON.stringify({
      routes: body.routes.map((route) => ({
        ...route,
        searches_count: 1,
        is_trending: false,
        sample_size: 0,
        min_price: null,
        max_price: null,
      })),
    }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const routes = Array.from({ length: 101 }, () => ({
      origin_iata: "MAD",
      destination_iata: "BCN",
    }));
    const response = await fetchCommunityRouteInsights(routes);

    assert.deepEqual(batchSizes, [100, 1]);
    assert.equal(response.routes.length, 101);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
