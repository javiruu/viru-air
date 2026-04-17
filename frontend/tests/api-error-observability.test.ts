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
