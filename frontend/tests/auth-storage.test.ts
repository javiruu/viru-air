import assert from "node:assert/strict";
import test from "node:test";

import {
  DASHBOARD_DEMO_ACCOUNT,
  clearToken,
  getRefreshToken,
  getToken,
  isDashboardLoginRequired,
  saveAuthTokens,
  saveDashboardLoginRequired,
} from "@/modules/shared/auth";
import { isDashboardDemoAccessEnabled, signInDashboardDemoAccount } from "@/modules/shared/dashboard-demo-session";

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

test("saveAuthTokens persists access and refresh token", async () => {
  await withMockStorage(() => {
    saveAuthTokens({ access_token: "access", refresh_token: "refresh", token_type: "bearer" });
    assert.equal(getToken(), "access");
    assert.equal(getRefreshToken(), "refresh");
    clearToken();
    assert.equal(getToken(), null);
    assert.equal(getRefreshToken(), null);
  });
});

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

test("signInDashboardDemoAccount persists demo auth tokens when demo access is enabled", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ access_token: "demo-access", refresh_token: "demo-refresh", token_type: "bearer" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });

  try {
    await withMockStorage(async () => {
      saveDashboardLoginRequired(false);
      assert.equal(await signInDashboardDemoAccount(), true);
      assert.equal(getToken(), "demo-access");
      assert.equal(getRefreshToken(), "demo-refresh");
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
