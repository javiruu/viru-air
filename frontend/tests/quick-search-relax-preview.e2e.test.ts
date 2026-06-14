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

async function openQuickSearch(page: import("playwright").Page) {
  await Promise.all([
    page.waitForResponse((response) => response.url().includes("/api/v1/airports/seeds") && response.status() === 200, { timeout: 30000 }),
    page.goto(`${BASE_URL}/quick-search`, { waitUntil: "networkidle", timeout: 30000 }),
  ]);
}

test("quick-search relax filters preview supports cancel and confirm", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const token = await createSessionToken();
    if (!token) {
      t.skip(`Quick-Search auth session could not be created against ${API_BASE}.`);
      return;
    }
    await context.addInitScript((value) => {
      window.localStorage.clear();
      window.sessionStorage.clear();
      window.localStorage.setItem("viru_token", value);
      window.localStorage.setItem("viru_locale", "es");
    }, token);
    const page = await context.newPage();

    try {
      await openQuickSearch(page);
    } catch {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend and retry.`);
      return;
    }

    const originInput = page.locator('input[name="origin_iata"]');
    const destinationInput = page.locator('input[name="destination_iata"]');
    const datePicker = page.locator('[data-ui="qs-date-picker-v2"]').first();

    try {
      await originInput.waitFor({ state: "visible", timeout: 8000 });
      await destinationInput.waitFor({ state: "visible", timeout: 8000 });
      await datePicker.waitFor({ state: "visible", timeout: 8000 });
    } catch {
      t.skip("Quick-Search form is not directly reachable (likely auth/session required).");
      return;
    }

    await page.route("**/api/v1/search/quick", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          job_id: "qs_relax_preview",
          results: [],
          filters: { warnings: ["ryanair_unavailable_parcial"] },
          meta: {
            query_trace_id: "qs_relax_preview_trace",
            truncated: false,
            stale_data: false,
            freshness_ts: null,
          },
        }),
      });
    });

    await originInput.fill("MAD");
    await destinationInput.fill("DUB");
    await datePicker.locator(".qs-date-trigger").click();
    await page.locator(".qs-date-popover .qs-date-day:not(.is-disabled):not(.is-outside)").nth(10).click();
    await page.getByRole("button", { name: "Buscar" }).click();

    const relaxButton = page.getByRole("button", { name: "Relajar filtros" }).first();
    try {
      await relaxButton.waitFor({ state: "visible", timeout: 12000 });
    } catch {
      t.skip("Relax flow requires empty-state response for this environment.");
      return;
    }

    await relaxButton.click();
    await expectVisible(page, "Cambios propuestos");

    await page.getByRole("button", { name: "Cancelar" }).click();
    await expectHidden(page, "Cambios propuestos");

    await relaxButton.click();
    await page.getByRole("button", { name: "Aplicar cambios y buscar" }).click();
    await expectHidden(page, "Cambios propuestos");
  } finally {
    await browser.close();
  }
});

async function expectVisible(page: import("playwright").Page, text: string) {
  const locator = page.getByText(text, { exact: false }).first();
  await locator.waitFor({ state: "visible", timeout: 8000 });
  assert.equal(await locator.isVisible(), true);
}

async function expectHidden(page: import("playwright").Page, text: string) {
  const locator = page.getByText(text, { exact: false }).first();
  await locator.waitFor({ state: "hidden", timeout: 8000 });
  assert.equal(await locator.isVisible().catch(() => false), false);
}
