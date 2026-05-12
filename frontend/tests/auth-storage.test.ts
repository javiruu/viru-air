import assert from "node:assert/strict";
import test from "node:test";

import { clearToken, getRefreshToken, getToken, saveAuthTokens } from "@/modules/shared/auth";

function withMockStorage(fn: () => void): void {
  const originalWindow = (globalThis as { window?: unknown }).window;
  const store = new Map<string, string>();
  const localStorage = {
    getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
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
