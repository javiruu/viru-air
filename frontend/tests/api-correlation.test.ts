import assert from "node:assert/strict";
import test from "node:test";

import { apiFetchWithStatus } from "@/modules/shared/api";

function assertOpaqueCorrelationId(value: string | null): asserts value is string {
  assert.ok(value, "expected x-correlation-id header");
  assert.match(value, /^[A-Za-z0-9._-]{8,64}$/);
}

test("apiFetchWithStatus sends an opaque correlation id on hotel-shaped requests", async () => {
  const originalFetch = globalThis.fetch;
  let requestHeaders: Headers | null = null;

  globalThis.fetch = async (_input, init) => {
    requestHeaders = new Headers(init?.headers);
    return new Response(JSON.stringify([]), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const result = await apiFetchWithStatus<unknown[]>("/hotels/search?city=Madrid", {
      headers: { "x-client-operation": "hotel_search" },
    });

    assert.equal(result.ok, true);
    const capturedHeaders = requestHeaders as Headers | null;
    assert.ok(capturedHeaders);
    assertOpaqueCorrelationId(capturedHeaders.get("x-correlation-id"));
    assert.equal(capturedHeaders.get("x-client-operation"), "hotel_search");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("apiFetchWithStatus sends a fresh correlation id per request", async () => {
  const originalFetch = globalThis.fetch;
  const correlationIds: string[] = [];

  globalThis.fetch = async (_input, init) => {
    const headers = new Headers(init?.headers);
    const correlationId = headers.get("x-correlation-id");
    assertOpaqueCorrelationId(correlationId);
    correlationIds.push(correlationId);
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    await apiFetchWithStatus("/hotels/MAD-1");
    await apiFetchWithStatus("/hotels/MAD-1/rates");

    assert.equal(correlationIds.length, 2);
    assert.notEqual(correlationIds[0], correlationIds[1]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
