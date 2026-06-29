import assert from "node:assert/strict";
import test from "node:test";

test("resolveApiBase keeps relative /api base on local browser sessions so Next rewrites stay same-origin", async () => {
  const originalWindow = (globalThis as { window?: unknown }).window;

  (globalThis as { window?: unknown }).window = {
    location: {
      hostname: "127.0.0.1",
      protocol: "http:",
    },
  };

  try {
    const { resolveApiBase } = await import("../src/modules/shared/api");
    assert.equal(resolveApiBase("/api/v1"), "/api/v1");
  } finally {
    if (typeof originalWindow === "undefined") {
      delete (globalThis as { window?: unknown }).window;
    } else {
      (globalThis as { window?: unknown }).window = originalWindow;
    }
  }
});

test("resolveLongRunningApiBase sends local long searches directly to the backend origin", async () => {
  const originalWindow = (globalThis as { window?: unknown }).window;

  (globalThis as { window?: unknown }).window = {
    location: {
      hostname: "127.0.0.1",
      protocol: "http:",
    },
  };

  try {
    const { resolveLongRunningApiBase } = await import("../src/modules/shared/api");
    assert.equal(
      resolveLongRunningApiBase("/api/v1", "http://127.0.0.1:8000"),
      "http://127.0.0.1:8000/api/v1",
    );
  } finally {
    if (typeof originalWindow === "undefined") {
      delete (globalThis as { window?: unknown }).window;
    } else {
      (globalThis as { window?: unknown }).window = originalWindow;
    }
  }
});

test("resolveLongRunningApiBase keeps same-origin proxy when direct backend would be mixed content", async () => {
  const originalWindow = (globalThis as { window?: unknown }).window;

  (globalThis as { window?: unknown }).window = {
    location: {
      hostname: "127.0.0.1",
      protocol: "https:",
    },
  };

  try {
    const { resolveLongRunningApiBase } = await import("../src/modules/shared/api");
    assert.equal(resolveLongRunningApiBase("/api/v1", "http://127.0.0.1:8000"), "/api/v1");
  } finally {
    if (typeof originalWindow === "undefined") {
      delete (globalThis as { window?: unknown }).window;
    } else {
      (globalThis as { window?: unknown }).window = originalWindow;
    }
  }
});
