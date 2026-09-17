import assert from "node:assert/strict";
import test from "node:test";
import { customClient } from "../src/api/mutator/custom-client";

test("customClient formats url and passes parameters correctly", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = "";

  globalThis.fetch = async (input: RequestInfo | URL) => {
    requestedUrl = input.toString();
    return new Response(JSON.stringify({ success: true, count: 2 }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const res = await customClient<{ success: boolean; count: number }>({
      url: "/airports/catalog",
      method: "GET",
      params: { limit: 10, search: "MAD" },
    });

    assert.equal(res.success, true);
    assert.equal(res.count, 2);
    assert.ok(requestedUrl.includes("/airports/catalog"));
    assert.ok(requestedUrl.includes("limit=10"));
    assert.ok(requestedUrl.includes("search=MAD"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("customClient handles 204 No Content safely", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    return new Response(null, { status: 204 });
  };

  try {
    const res = await customClient({
      url: "/alerts/123",
      method: "DELETE",
    });
    assert.deepEqual(res, {});
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("customClient normalizes backend error responses", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    return new Response(JSON.stringify({ detail: "Invalid search dates range" }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    await assert.rejects(async () => {
      await customClient({
        url: "/search/quick",
        method: "POST",
        data: { origin: "MAD" },
      });
    }, /Invalid search dates range/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
