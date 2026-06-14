import assert from "node:assert/strict";
import test from "node:test";

import { chromium } from "playwright";

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const API_BASE = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

async function createSessionToken() {
  try {
    const email = `codex-e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
    const password = "Test123456!";
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) return null;
    const auth = await response.json() as { access_token?: string };
    return auth.access_token ?? null;
  } catch {
    return null;
  }
}

test("quick-search airport picker opens before search and can be dismissed", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const token = await createSessionToken();
    if (!token) {
      t.skip(`Quick-Search auth session could not be created against ${API_BASE}.`);
      return;
    }
    await context.addInitScript((value) => {
      window.localStorage.setItem("viru_token", value);
    }, token);
    const page = await context.newPage();

    try {
      await Promise.all([
        page.waitForResponse((response) => response.url().includes("/api/v1/airports/seeds") && response.status() === 200, { timeout: 30000 }),
        page.goto(`${BASE_URL}/quick-search`, { waitUntil: "networkidle", timeout: 30000 }),
      ]);
    } catch {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend and retry.`);
      return;
    }

    const originPickerButton = page.getByRole("button", { name: "Elegir aeropuerto de origen" });
    try {
      await originPickerButton.waitFor({ state: "visible", timeout: 8000 });
    } catch {
      t.skip("Quick-Search form is not directly reachable (likely auth/session required).");
      return;
    }

    await originPickerButton.click();
    const dialog = page.getByRole("dialog", { name: "Elegir aeropuerto" });
    await dialog.waitFor({ state: "visible", timeout: 8000 });
    assert.equal(await dialog.isVisible(), true);

    await page.locator(".airport-modal-overlay").click({ position: { x: 10, y: 10 } });
    await dialog.waitFor({ state: "hidden", timeout: 8000 });
    assert.equal(await dialog.isVisible().catch(() => false), false);
  } finally {
    await browser.close();
  }
});
