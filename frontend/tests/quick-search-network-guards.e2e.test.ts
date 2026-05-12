import assert from "node:assert/strict";
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
    window.localStorage.setItem("viru_token", value);
  }, token);

  const page = await context.newPage();
  const trackedRequests: string[] = [];
  const trackedResponses: Array<{ url: string; status: number }> = [];

  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/v1/search/deeplink") || url.includes("/api/v1/search/quick")) {
      trackedRequests.push(url);
    }
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/v1/search/deeplink") || url.includes("/api/v1/search/quick")) {
      trackedResponses.push({ url, status: response.status() });
    }
  });

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

  return { page, originInput, destinationInput, datePicker, trackedRequests, trackedResponses };
}

async function selectFirstAvailableDate(page: Page, datePickerTrigger: ReturnType<Page["locator"]>) {
  await datePickerTrigger.locator(".qs-date-trigger").click();
  await page.locator(".qs-date-popover .qs-date-day:not(.is-disabled):not(.is-outside)").first().click();
  await page.keyboard.press("Escape");
}

async function waitForAutocomplete(page: Page, selector: string, state: "visible" | "hidden") {
  await page.locator(selector).waitFor({ state, timeout: 10000 });
}

async function clearRoute(originInput: ReturnType<Page["locator"]>, destinationInput: ReturnType<Page["locator"]>) {
  await originInput.fill("");
  await destinationInput.fill("");
}

test("quick-search blocks partial and unsupported IATAs before network search requests", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const setup = await openQuickSearch(context);
    if (!setup) {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend/backend and retry.`);
      return;
    }

    const { page, originInput, destinationInput, datePicker, trackedRequests, trackedResponses } = setup;
    await originInput.fill("");
    await destinationInput.fill("");
    trackedRequests.length = 0;
    trackedResponses.length = 0;

    await originInput.type("AG", { delay: 120 });
    await destinationInput.type("TS", { delay: 120 });
    await page.waitForTimeout(500);
    assert.equal(trackedRequests.length, 0);

    await originInput.type("P", { delay: 120 });
    await destinationInput.type("F", { delay: 120 });
    await page.waitForTimeout(700);

    await selectFirstAvailableDate(page, datePicker);
    await page.waitForTimeout(1000);

    assert.equal(trackedResponses.filter((item) => item.url.includes("/search/deeplink")).length, 0);

    const searchButton = page.getByRole("button", { name: "Buscar" });
    await searchButton.waitFor({ state: "visible", timeout: 10000 });
    assert.equal(await searchButton.isDisabled(), true);
    await page.waitForTimeout(900);

    assert.equal(trackedResponses.filter((item) => item.url.includes("/search/quick")).length, 0);
    assert.equal(await destinationInput.getAttribute("aria-invalid"), "true");
  } finally {
    await browser.close();
  }
});

test("quick-search keeps supported AGP to DUB requests below 400", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const setup = await openQuickSearch(context);
    if (!setup) {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend/backend and retry.`);
      return;
    }

    const { page, originInput, destinationInput, datePicker, trackedResponses } = setup;
    await originInput.fill("AGP");
    await destinationInput.fill("DUB");
    await selectFirstAvailableDate(page, datePicker);
    await page.waitForTimeout(1200);

    const deeplinkResponses = trackedResponses.filter((item) => item.url.includes("/search/deeplink"));
    assert.ok(deeplinkResponses.length >= 1);
    assert.equal(deeplinkResponses.every((item) => item.status < 400), true);

    await page.getByRole("button", { name: "Buscar" }).click();
    await page.waitForTimeout(2500);

    const quickResponses = trackedResponses.filter((item) => item.url.includes("/search/quick"));
    assert.ok(quickResponses.length >= 1);
    assert.equal(quickResponses.every((item) => item.status < 400), true);
  } finally {
    await browser.close();
  }
});

test("quick-search selects an origin suggestion with the mouse and closes the dropdown", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const setup = await openQuickSearch(context);
    if (!setup) {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend/backend and retry.`);
      return;
    }

    const { page, originInput, destinationInput } = setup;
    await clearRoute(originInput, destinationInput);
    await originInput.type("par", { delay: 100 });
    await waitForAutocomplete(page, "#origin-suggestions", "visible");

    const firstSuggestion = page.locator("#origin-suggestions button").first();
    const selectedIata = (await firstSuggestion.locator("strong").textContent())?.trim() || "";
    assert.match(selectedIata, /^[A-Z]{3}$/);

    await firstSuggestion.click();

    assert.equal(await originInput.inputValue(), selectedIata);
    await waitForAutocomplete(page, "#origin-suggestions", "hidden");
  } finally {
    await browser.close();
  }
});

test("quick-search hides origin suggestions when the origin input is cleared", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const setup = await openQuickSearch(context);
    if (!setup) {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend/backend and retry.`);
      return;
    }

    const { page, originInput, destinationInput } = setup;
    await clearRoute(originInput, destinationInput);
    await originInput.type("par", { delay: 100 });
    await waitForAutocomplete(page, "#origin-suggestions", "visible");

    await originInput.fill("");

    await waitForAutocomplete(page, "#origin-suggestions", "hidden");
  } finally {
    await browser.close();
  }
});

test("quick-search blocks empty route submission with validation feedback", async (t) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  try {
    const setup = await openQuickSearch(context);
    if (!setup) {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend/backend and retry.`);
      return;
    }

    const { page, originInput, destinationInput } = setup;
    await clearRoute(originInput, destinationInput);

    await originInput.press("Enter");

    await page.getByText(/Please enter a search/i).first().waitFor({ state: "visible", timeout: 10000 });
    assert.equal(await originInput.getAttribute("aria-invalid"), "true");
    assert.equal(await destinationInput.getAttribute("aria-invalid"), "true");
    assert.match(page.url(), /\/quick-search$/);
  } finally {
    await browser.close();
  }
});
