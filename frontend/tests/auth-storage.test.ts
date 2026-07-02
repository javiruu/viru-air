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

function withMockStorage(fn: () => void): void {
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
    fn();
  } finally {
    (globalThis as { window?: unknown }).window = originalWindow;
  }
}

test("saveAuthTokens persists access and refresh token", () => {
  withMockStorage(() => {
    saveAuthTokens({ access_token: "access", refresh_token: "refresh", token_type: "bearer" });
    assert.equal(getToken(), "access");
    assert.equal(getRefreshToken(), "refresh");
    clearToken();
    assert.equal(getToken(), null);
    assert.equal(getRefreshToken(), null);
  });
});

test("dashboard access mode defaults to required login and can enable demo auto-entry", () => {
  withMockStorage(() => {
    assert.equal(isDashboardLoginRequired(), true);
    saveDashboardLoginRequired(false);
    assert.equal(isDashboardLoginRequired(), false);
    saveDashboardLoginRequired(true);
    assert.equal(isDashboardLoginRequired(), true);
    assert.equal(DASHBOARD_DEMO_ACCOUNT.email, "user@viru.local");
  });
});
