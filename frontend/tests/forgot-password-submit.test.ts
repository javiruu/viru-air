import assert from "node:assert/strict";
import test from "node:test";

import { submitForgotPassword } from "@/modules/shared/forgot-password";

test("forgot-password submit resolves success on generic backend response", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ message: "Si el correo existe, te enviaremos instrucciones." }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });

  try {
    const result = await submitForgotPassword("qa@viru.dev");
    assert.equal(result, "success");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("forgot-password submit resolves generic error on backend failure", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ status: 500, code: "request_failed", message: "Request failed." }), {
      status: 500,
      headers: { "content-type": "application/json" },
    });

  try {
    const result = await submitForgotPassword("qa@viru.dev");
    assert.equal(result, "error");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
