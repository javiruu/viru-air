import assert from "node:assert/strict";
import test from "node:test";

test("resolveApiBase avoids Next rewrite proxy for local dev relative /api base", async () => {
  const originalWindow = (globalThis as { window?: unknown }).window;
  const originalNodeEnv = process.env.NODE_ENV;

  (process.env as Record<string, string | undefined>).NODE_ENV = "development";
  (globalThis as { window?: unknown }).window = {
    location: {
      hostname: "localhost",
      protocol: "http:",
    },
  };

  try {
    const { resolveApiBase } = await import("../src/modules/shared/api");
    assert.equal(resolveApiBase("/api/v1"), "http://127.0.0.1:8000/api/v1");
  } finally {
    (process.env as Record<string, string | undefined>).NODE_ENV = originalNodeEnv;
    if (typeof originalWindow === "undefined") {
      delete (globalThis as { window?: unknown }).window;
    } else {
      (globalThis as { window?: unknown }).window = originalWindow;
    }
  }
});
