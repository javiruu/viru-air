import assert from "node:assert/strict";
import test from "node:test";

import { getHotelDetail, getHotelParity, getHotelRates } from "@/modules/hotels/api";


test("hotel detail reads share the originating intent and keep request correlations distinct", async () => {
  const originalFetch = globalThis.fetch;
  const captured: Array<{ path: string; intentId: string | null; correlationId: string | null }> = [];

  globalThis.fetch = async (input, init) => {
    const headers = new Headers(init?.headers);
    captured.push({
      path: String(input),
      intentId: headers.get("x-client-event-id"),
      correlationId: headers.get("x-correlation-id"),
    });
    return new Response(JSON.stringify([]), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    await getHotelDetail("hotel-1", undefined, "intent-search-01");
    await getHotelRates("hotel-1", undefined, undefined, "intent-search-01");
    await getHotelParity("hotel-1", undefined, "intent-search-01");

    assert.equal(captured.length, 3);
    assert.deepEqual(
      captured.map((request) => request.intentId),
      ["intent-search-01", "intent-search-01", "intent-search-01"],
    );
    assert.equal(new Set(captured.map((request) => request.correlationId)).size, 3);
    assert.match(captured[0].path, /\/hotels\/hotel-1$/);
    assert.match(captured[1].path, /\/hotels\/hotel-1\/rates$/);
    assert.match(captured[2].path, /\/hotels\/hotel-1\/parity$/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test("legacy detail callers remain valid without an intent header", async () => {
  const originalFetch = globalThis.fetch;
  const intents: Array<string | null> = [];

  globalThis.fetch = async (_input, init) => {
    intents.push(new Headers(init?.headers).get("x-client-event-id"));
    return new Response(JSON.stringify([]), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    await getHotelDetail("hotel-1");
    await getHotelRates("hotel-1");
    await getHotelParity("hotel-1");
    assert.deepEqual(intents, [null, null, null]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
