import assert from "node:assert/strict";
import test from "node:test";

import {
  DASHBOARD_DEMO_ACCOUNT,
  isDashboardLoginRequired,
  saveDashboardLoginRequired,
} from "@/modules/shared/auth";
import {
  isDashboardDemoAccessEnabled,
} from "@/modules/shared/dashboard-demo-session";

async function withMockStorage(fn: () => void | Promise<void>): Promise<void> {
  const originalWindow = (globalThis as { window?: unknown }).window;
  const store = new Map<string, string>();
  const localStorage = {
    getItem: (key: string) => {
      const value = store.get(key);
      return typeof value === "string" ? value : null;
    },
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
  };
  (globalThis as { window?: unknown }).window = { localStorage };
  try {
    await fn();
  } finally {
    (globalThis as { window?: unknown }).window = originalWindow;
  }
}

test("dashboard access mode defaults to required login and can enable demo auto-entry", async () => {
  await withMockStorage(() => {
    assert.equal(isDashboardLoginRequired(), true);
    assert.equal(isDashboardDemoAccessEnabled(), false);
    saveDashboardLoginRequired(false);
    assert.equal(isDashboardLoginRequired(), false);
    assert.equal(isDashboardDemoAccessEnabled(), true);
    saveDashboardLoginRequired(true);
    assert.equal(isDashboardLoginRequired(), true);
    assert.equal(DASHBOARD_DEMO_ACCOUNT.email, "user@viru.local");
  });
});
