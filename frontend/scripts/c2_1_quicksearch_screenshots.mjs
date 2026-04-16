import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const OUT_DIR = path.resolve("../docs/qa/screenshots/c2.1");
const APP_URL = "http://127.0.0.1:3101/quick-search";
fs.mkdirSync(OUT_DIR, { recursive: true });

const baseResult = {
  result_id: "res-1",
  origin: "MAD",
  destination: "DUB",
  travel_date: "2026-04-12",
  departure_time_local: "09:20",
  price_total: 49.99,
  currency: "EUR",
  ranking_score: 0.88,
  duration_total_min: 175,
  risk_label: "low",
  source: "ryanair",
  stale_data: false,
  itinerary_type: "direct",
  legs: [],
};

async function setupPage(page, scenario) {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "local-user", email: "local@example.com" }),
    });
  });
  await page.route("**/api/v1/search/quick**", async (route) => {
    if (scenario === "error") {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: { message: "backend exploded" } }),
      });
      return;
    }

    const results = scenario === "empty" ? [] : [baseResult, { ...baseResult, result_id: "res-2", destination: "LIS", risk_label: "medium" }];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        results,
        filters: { warnings: [] },
        meta: { currency: "EUR", stale_data: false },
        job_id: `job-${scenario}`,
      }),
    });
  });

  await page.route("**/api/v1/search/deeplink**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ url: "https://www.ryanair.com" }),
    });
  });

  await page.route("**/api/v1/preferences/search", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ default_radius_km: 150, include_stops_default: false, avoid_departure_before: "07:00", language: "es" }),
    });
  });

  await page.route("**/api/v1/preferences/region", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ language: "es" }),
    });
  });
}

async function unlockIfNeeded(page) {
  const tokenInput = page.locator('input[name="token"]');
  if (await tokenInput.count()) {
    await tokenInput.fill("tok_12345678901234567890123456789012345678901234567890");
    await page.getByRole("button", { name: /continue/i }).click();
    await page.waitForTimeout(600);
  }
}

async function fillAndSearch(page) {
  await page.goto(APP_URL, { waitUntil: "networkidle" });
  await unlockIfNeeded(page);
  await page.waitForSelector('input[name="origin_iata"]', { timeout: 20000 });
  await page.fill('input[name="origin_iata"]', "MAD");
  await page.fill('input[name="destination_iata"]', "DUB");
  await page.waitForSelector('[data-ui="qs-date-picker-v2"]', { timeout: 10000 });
  await page.locator('[data-ui="qs-date-picker-v2"] .qs-date-trigger').first().click();
  await page.locator(".qs-date-popover .qs-date-day:not(.is-disabled):not(.is-outside)").nth(12).click();
  await page.click('button[type="submit"]');
}

async function runScenario(browser, scenario, fileName) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 2200 } });
  await context.addInitScript(() => {
    window.localStorage.setItem("viru_token", "tok_12345678901234567890123456789012345678901234567890");
  });
  const page = await context.newPage();
  await setupPage(page, scenario);
  await fillAndSearch(page);

  if (scenario === "normal") {
    await page.waitForSelector(".qs-result-row", { timeout: 15000 });
  } else if (scenario === "empty") {
    await page.waitForSelector(".qs-empty-title", { timeout: 10000 });
  } else if (scenario === "error") {
    await page.waitForSelector(".qs-state", { timeout: 10000 });
  }

  await page.screenshot({ path: path.join(OUT_DIR, fileName), fullPage: true });
  await context.close();
}

async function runStrictSoft(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 2200 } });
  await context.addInitScript(() => {
    window.localStorage.setItem("viru_token", "tok_12345678901234567890123456789012345678901234567890");
  });
  const page = await context.newPage();
  await setupPage(page, "normal");
  await fillAndSearch(page);
  await page.waitForSelector(".qs-results-list article", { timeout: 10000 });

  await page.locator(".qs-filters-toggle").click();
  await page.waitForSelector("#qs-filters-drawer.open", { timeout: 5000 });

  await page.screenshot({ path: path.join(OUT_DIR, "04-strict-soft.png"), fullPage: true });
  await context.close();
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    await runScenario(browser, "normal", "01-busqueda-normal.png");
    await runScenario(browser, "empty", "02-sin-resultados.png");
    await runScenario(browser, "error", "03-error-backend.png");
    await runStrictSoft(browser);
    console.log(`Screenshots generated in ${OUT_DIR}`);
  } finally {
    await browser.close();
  }
})();
