import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { chromium, type BrowserContext, type Page } from "playwright";

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

async function openQuickSearch(context: BrowserContext) {
  const token = await createSessionToken();
  if (!token) return null;
  await context.addInitScript((value) => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.localStorage.setItem("viru_token", value);
    window.localStorage.setItem("viru_locale", "es");
  }, token);

  const page = await context.newPage();
  try {
    await Promise.all([
      page.waitForResponse((response) => response.url().includes("/api/v1/airports/seeds") && response.status() === 200, { timeout: 30000 }),
      page.goto(`${BASE_URL}/quick-search`, { waitUntil: "networkidle", timeout: 30000 }),
    ]);
  } catch {
    await page.close();
    return null;
  }

  const originInput = page.locator('input[name="origin_iata"]');
  const destinationInput = page.locator('input[name="destination_iata"]');
  const datePicker = page.locator('[data-ui="qs-date-picker-v2"]').first();

  try {
    await originInput.waitFor({ state: "visible", timeout: 10000 });
    await destinationInput.waitFor({ state: "visible", timeout: 10000 });
    await datePicker.waitFor({ state: "visible", timeout: 10000 });
  } catch {
    await page.close();
    return null;
  }

  return { page, originInput, destinationInput, datePicker };
}

async function selectStableFutureDate(page: Page, datePickerTrigger: ReturnType<Page["locator"]>) {
  await datePickerTrigger.locator(".qs-date-trigger").click();
  await page.getByRole("button", { name: /Mes siguiente|Next month/ }).click();
  await page.locator('.qs-date-popover .qs-date-day:not(.is-disabled):not(.is-outside)', { hasText: "8" }).first().click();
  await page.keyboard.press("Escape");
}

function buildResult(overrides: Record<string, unknown> = {}) {
  return {
    result_id: "qs-result-1",
    origin: "MAD",
    destination: "CDG",
    travel_date: "2026-05-08",
    departure_time_local: "09:30",
    price: 49,
    price_total: 49,
    currency: "EUR",
    source: "ryanair",
    duration_total: 125,
    duration_total_min: 125,
    risk_label: "low",
    ranking_score: 0.91,
    stale_data: false,
    itinerary_type: "direct",
    legs: [],
    ...overrides,
  };
}

test("quick-search keeps loading exclusive until empty state is final", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const setup = await openQuickSearch(context);
    if (!setup) {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend/backend and retry.`);
      return;
    }

    const { page, originInput, destinationInput, datePicker } = setup;
    const screenshotDir = fs.mkdtempSync(path.join(os.tmpdir(), "viru-qs-loading-transition-"));
    const capturedBodies: string[] = [];

    await page.route("**/api/v1/search/quick", async (route) => {
      capturedBodies.push(route.request().postData() || "");
      await page.waitForTimeout(450);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          job_id: "qs_test_empty",
          results: [],
          filters: { warnings: ["ryanair_unavailable_parcial"] },
          meta: {
            query_trace_id: "qs_dc9840ae144d",
            truncated: false,
            stale_data: false,
            freshness_ts: null,
          },
        }),
      });
    });

    await originInput.fill("AGP");
    await destinationInput.fill("DUB");
    await selectStableFutureDate(page, datePicker);
    await page.getByRole("button", { name: "Buscar" }).click();

    const loadingState = page.locator(".qs-state-loading");
    const emptyState = page.locator(".qs-state-empty");
    const zeroResultsText = page.getByText(/0 resultados/i).first();
    const readyText = page.getByText(/Listo para buscar|Listo para explorar/i).first();

    await loadingState.waitFor({ state: "visible", timeout: 10000 });
    assert.equal(capturedBodies.length, 1);

    let observedLoading = true;
    for (let tick = 0; tick < 5; tick += 1) {
      await page.waitForTimeout(120);
      const loadingVisible = await loadingState.isVisible().catch(() => false);
      observedLoading = observedLoading || loadingVisible;
      if (!loadingVisible) {
        continue;
      }
      assert.equal(await emptyState.isVisible().catch(() => false), false);
      assert.equal(await zeroResultsText.isVisible().catch(() => false), false);
      assert.equal(await readyText.isVisible().catch(() => false), false);
    }
    assert.equal(observedLoading, true);

    await loadingState.waitFor({ state: "hidden", timeout: 10000 });
    await emptyState.waitFor({ state: "visible", timeout: 10000 });
    assert.equal(await emptyState.isVisible(), true);
    assert.equal(await loadingState.isVisible().catch(() => false), false);

    await page.screenshot({ path: path.join(screenshotDir, "quick-search-empty-final.png"), fullPage: true });
  } finally {
    await browser.close();
  }
});

test("quick-search shows a visible loading state before a fast final empty response and never falls back to ready copy", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const setup = await openQuickSearch(context);
    if (!setup) {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend/backend and retry.`);
      return;
    }

    const { page, originInput, destinationInput, datePicker } = setup;

    await page.route("**/api/v1/search/quick", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          job_id: "qs_fast_empty",
          results: [],
          filters: { warnings: ["ryanair_unavailable_parcial"] },
          meta: {
            query_trace_id: "qs_fast_empty_trace",
            truncated: false,
            stale_data: false,
            freshness_ts: null,
          },
        }),
      });
    });

    await originInput.fill("AGP");
    await destinationInput.fill("DUB");
    await selectStableFutureDate(page, datePicker);
    await page.getByRole("button", { name: "Buscar" }).click();

    const loadingState = page.locator(".qs-state-loading");
    const emptyState = page.locator(".qs-state-empty");
    const readyPanel = page.locator(".qs-ready");
    const statusTitle = page.locator(".qs-command-stage__status-copy strong").first();

    await loadingState.waitFor({ state: "visible", timeout: 10000 });
    assert.equal(await readyPanel.isVisible().catch(() => false), false);

    await loadingState.waitFor({ state: "hidden", timeout: 10000 });
    await emptyState.waitFor({ state: "visible", timeout: 10000 });

    assert.equal(await emptyState.isVisible(), true);
    assert.equal(await readyPanel.isVisible().catch(() => false), false);
    assert.notEqual(await statusTitle.textContent(), "Listo para explorar");
    assert.notEqual(await statusTitle.textContent(), "Listo para buscar");
  } finally {
    await browser.close();
  }
});

test("quick-search final success state does not surface ready copy after a fast 200 response", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const setup = await openQuickSearch(context);
    if (!setup) {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend/backend and retry.`);
      return;
    }

    const { page, originInput, destinationInput, datePicker } = setup;

    await page.route("**/api/v1/search/quick", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          job_id: "qs_fast_success",
          results: [buildResult()],
          filters: { warnings: [] },
          meta: {
            query_trace_id: "qs_fast_success_trace",
            truncated: false,
            stale_data: false,
            freshness_ts: null,
          },
        }),
      });
    });

    await originInput.fill("AGP");
    await destinationInput.fill("DUB");
    await selectStableFutureDate(page, datePicker);
    await page.getByRole("button", { name: "Buscar" }).click();

    const loadingState = page.locator(".qs-state-loading");
    const resultsToolbar = page.locator(".qs-results-toolbar");
    const readyPanel = page.locator(".qs-ready");
    const statusBadge = page.locator(".qs-command-stage__status-badge").first();

    await loadingState.waitFor({ state: "visible", timeout: 10000 });
    await loadingState.waitFor({ state: "hidden", timeout: 10000 });
    await resultsToolbar.waitFor({ state: "visible", timeout: 10000 });

    assert.equal(await resultsToolbar.isVisible(), true);
    assert.equal(await readyPanel.isVisible().catch(() => false), false);
    assert.notEqual(await statusBadge.textContent(), "Listo para buscar");
    assert.notEqual(await statusBadge.textContent(), "Listo para explorar");
  } finally {
    await browser.close();
  }
});
