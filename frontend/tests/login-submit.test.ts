import assert from "node:assert/strict";
import test from "node:test";

import { submitLogin } from "@/modules/shared/login-submit";

test("submitLogin maps invalid_auth 401 to invalid credentials", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        status: 401,
        code: "invalid_auth",
        message: "Authentication failed.",
        details: [],
        correlation_id: "corr-login-401",
      }),
      {
        status: 401,
        headers: { "content-type": "application/json", "x-correlation-id": "corr-login-401" },
      },
    );

  try {
    const result = await submitLogin("qa@viru.dev", "badpass123");
    assert.deepEqual(result, { kind: "invalid_credentials" });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("submitLogin maps 500 to server_error", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        status: 500,
        code: "internal_server_error",
        message: "Internal server error.",
        details: [],
        correlation_id: "corr-login-500",
      }),
      {
        status: 500,
        headers: { "content-type": "application/json", "x-correlation-id": "corr-login-500" },
      },
    );

  try {
    const result = await submitLogin("qa@viru.dev", "goodpass123");
    assert.deepEqual(result, { kind: "server_error" });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
