import assert from "node:assert/strict";
import test from "node:test";

import { areaSearch, searchHotels } from "@/modules/hotels/api";
import { createHotelSearchIntentId } from "@/modules/hotels/searchIntent";

function assertIntentId(value: string | null, expected: string) {
  assert.equal(value, expected);
  assert.match(value, /^[A-Za-z0-9._-]{8,64}$/);
}

test("hotel search intent ids are opaque and unique per operation", () => {
  const first = createHotelSearchIntentId();
  const second = createHotelSearchIntentId();

  assert.match(first, /^[A-Za-z0-9._-]{8,64}$/);
  assert.match(second, /^[A-Za-z0-9._-]{8,64}$/);
  assert.notEqual(first, second);
});

test("hotel result requests propagate the explicit search intent beside per-request correlation", async () => {
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
    await searchHotels({ city: "Madrid" }, undefined, "intent-search-01");
    await areaSearch({
      latitude: 40.4168,
      longitude: -3.7038,
      check_in: "2026-09-12",
      check_out: "2026-09-15",
    }, undefined, "intent-search-01");

    assert.equal(captured.length, 2);
    assertIntentId(captured[0].intentId, "intent-search-01");
    assertIntentId(captured[1].intentId, "intent-search-01");
    assert.notEqual(captured[0].correlationId, captured[1].correlationId);
    assert.match(captured[0].path, /\/hotels\/search\?city=Madrid$/);
    assert.match(captured[1].path, /\/hotels\/area-search\?/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("concurrent hotel searches keep their explicit intents isolated", async () => {
  const originalFetch = globalThis.fetch;
  const captured: string[] = [];

  globalThis.fetch = async (_input, init) => {
    const headers = new Headers(init?.headers);
    const intentId = headers.get("x-client-event-id");
    assert.ok(intentId);
    captured.push(intentId);
    await new Promise((resolve) => setTimeout(resolve, intentId === "intent-search-a" ? 5 : 0));
    return new Response(JSON.stringify([]), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    await Promise.all([
      searchHotels({ q: "A" }, undefined, "intent-search-a"),
      searchHotels({ q: "B" }, undefined, "intent-search-b"),
    ]);

    assert.deepEqual(new Set(captured), new Set(["intent-search-a", "intent-search-b"]));
    assert.equal(captured.length, 2);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("hotel request errors retain the server-returned search intent", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => new Response(JSON.stringify({
    status: 503,
    code: "provider_unavailable",
    message: "Provider unavailable.",
    details: [],
    correlation_id: "corr-search-error",
    client_event_id: "intent-search-error",
  }), {
    status: 503,
    headers: {
      "content-type": "application/json",
      "x-correlation-id": "corr-search-error",
      "x-client-event-id": "intent-search-error",
    },
  });

  try {
    await assert.rejects(
      searchHotels({ city: "Madrid" }, undefined, "intent-search-error"),
      (error: unknown) => {
        assert.equal((error as { status: number }).status, 503);
        assert.equal((error as { correlation_id?: string }).correlation_id, "corr-search-error");
        assert.equal((error as { client_event_id?: string }).client_event_id, "intent-search-error");
        return true;
      },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("legacy hotel search callers remain valid without an intent header", async () => {
  const originalFetch = globalThis.fetch;
  let intentHeader: string | null = "unexpected";

  globalThis.fetch = async (_input, init) => {
    intentHeader = new Headers(init?.headers).get("x-client-event-id");
    return new Response(JSON.stringify([]), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    await searchHotels({ q: "Madrid" });
    assert.equal(intentHeader, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
