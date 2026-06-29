import assert from "node:assert/strict";
import test from "node:test";

import { apiFetchWithStatus } from "@/modules/shared/api";

test("apiFetchWithStatus parses top-level error envelope and correlation id", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        status: 400,
        code: "quick_search_invalid_request",
        message: "Quick-search request rejected by backend validation.",
        details: [{ reason: "unknown_seed_iata:TSF", query_trace_id: "qs_debug_123" }],
        correlation_id: "corr-debug-123",
      }),
      {
        status: 400,
        headers: {
          "content-type": "application/json",
          "x-correlation-id": "corr-debug-123",
        },
      },
    );

  try {
    const result = await apiFetchWithStatus("/search/quick", {
      method: "POST",
      body: JSON.stringify({ destination_iata: "TSF" }),
    });

    assert.equal(result.ok, false);
    if (result.ok) {
      throw new Error("expected_error_result");
    }

    assert.equal(result.error.code, "quick_search_invalid_request");
    assert.equal(result.error.message, "Quick-search request rejected by backend validation.");
    assert.equal(result.error.correlation_id, "corr-debug-123");
    assert.deepEqual(result.error.details, [{ reason: "unknown_seed_iata:TSF", query_trace_id: "qs_debug_123" }]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("apiFetchWithStatus can bypass the same-origin proxy for long-running requests", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = "";

  globalThis.fetch = async (input) => {
    requestedUrl = String(input);
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const result = await apiFetchWithStatus<{ ok: boolean }>(
      "/search/quick",
      {
        method: "POST",
        body: JSON.stringify({}),
      },
      { apiBase: "http://127.0.0.1:8000/api/v1" },
    );

    assert.equal(result.ok, true);
    assert.equal(requestedUrl, "http://127.0.0.1:8000/api/v1/search/quick");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
