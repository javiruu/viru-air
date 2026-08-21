import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const baseUrl = process.env.E2E_BASE_URL || "http://127.0.0.1:3011";
const screenshotsDir = path.join(frontendRoot, "..", "docs", "qa", "evidence", "watchlist-route-toolbar");

const communityPricing = {
  eligible: false,
  trigger_reason: null,
  response: null,
  aggregate: { sample_size: 0, minimum_sample_size: 3, is_public: false, min_price: null, max_price: null, currency: "EUR" },
};

const watches = [
  { id: "watch-svq-tsf", origin_iata: "SVQ", destination_iata: "TSF", travel_date_local: "2026-09-20", target_price: 70, status: "active", watchers_count: 2, group_id: null, community_pricing: communityPricing },
  { id: "watch-svq-dub", origin_iata: "SVQ", destination_iata: "DUB", travel_date_local: "2026-09-21", target_price: 90, status: "active", watchers_count: 1, group_id: null, community_pricing: communityPricing },
  { id: "watch-agp-tsf", origin_iata: "AGP", destination_iata: "TSF", travel_date_local: "2026-09-22", target_price: 65, status: "paused", watchers_count: 3, group_id: null, community_pricing: communityPricing },
];

const snapshots = watches.map((watch, index) => ({
  watch_id: watch.id,
  captured_at_utc: `2026-08-${20 + index}T09:00:00Z`,
  raw_price: [45, 80, 55][index],
  raw_currency: "EUR",
  departure_time_local: `${watch.travel_date_local}T10:00:00+02:00`,
  provider: "qa",
  is_stale: false,
  source_kind: "live",
}));

async function mockApi(page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const apiPath = new URL(request.url()).pathname.replace(/^.*\/api\/v1/, "");
    const fulfill = (body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    if (apiPath === "/auth/me") return fulfill({ id: "qa-user", email: "qa@viru.local", locale: "es", is_admin: false });
    if (apiPath === "/watchlist" && request.method() === "GET") return fulfill(watches);
    if (apiPath === "/prices/history/batch") return fulfill({ data: snapshots });
    if (/^\/watchlist\/[^/]+$/.test(apiPath)) {
      const watch = watches.find((candidate) => apiPath.endsWith(candidate.id));
      return fulfill({ ...watch, latest_snapshot: snapshots.find((snapshot) => snapshot.watch_id === watch?.id) ?? null, price_history: [] });
    }
    if (apiPath.startsWith("/prices/compare")) return fulfill({ currency_mode: "single", watches: [], points: [] });
    return fulfill({});
  });
}

async function openWatchlist(browser, { width, height, theme }) {
  const context = await browser.newContext({ viewport: { width, height }, reducedMotion: "reduce" });
  await context.addInitScript((selectedTheme) => {
    localStorage.setItem("viru_token", "qa_token_for_mocked_browser_session_1234567890");
    localStorage.setItem("viru-theme", selectedTheme);
    localStorage.setItem("viru-locale", "es");
    localStorage.setItem("viru-ftue-watchlist", "dismissed");
  }, theme);
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await mockApi(page);
  await page.goto(`${baseUrl}/watchlist`, { waitUntil: "networkidle", timeout: 30_000 });
  await page.locator(".watch-smart-tool-group--route-tools").waitFor({ state: "visible" });
  return { context, page, consoleErrors };
}

await mkdir(screenshotsDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const report = { baseUrl, scenarios: [], consoleErrors: [] };

try {
  const desktop = await openWatchlist(browser, { width: 1440, height: 900, theme: "dark" });
  const { page } = desktop;
  const origin = page.locator("#watch-smart-route-origin");
  const destination = page.locator("#watch-smart-route-destination");
  const rows = page.locator(".watch-row");
  assert.equal(await rows.count(), 3);
  await page.screenshot({ path: path.join(screenshotsDir, "desktop-dark-full.png"), fullPage: true });
  await page.locator(".watch-smart-tool-group--route-tools").screenshot({ path: path.join(screenshotsDir, "desktop-dark-toolbar.png") });

  await origin.selectOption("SVQ");
  assert.equal(await rows.count(), 2);
  assert.deepEqual(await destination.locator("option").evaluateAll((options) => options.map((option) => option.value)), ["", "DUB", "TSF"]);
  await destination.selectOption("TSF");
  assert.equal(await rows.count(), 1);
  assert.match(await rows.first().innerText(), /SVQ\s*→\s*TSF/);
  await page.getByRole("button", { name: "Ver todas" }).click();
  assert.equal(await rows.count(), 3);

  await page.locator("#watch-smart-sort").selectOption("price_asc");
  assert.match(await rows.first().innerText(), /SVQ\s*→\s*TSF/);
  await page.getByRole("button", { name: "Ver calendario" }).click();
  await page.locator("#watchlist-calendar-selector").waitFor({ state: "visible" });
  report.scenarios.push({ name: "desktop-dark", rows: 3, calendarOpened: true, overflow: await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth) });
  report.consoleErrors.push(...desktop.consoleErrors);
  await desktop.context.close();

  for (const scenario of [
    { name: "desktop-light", width: 1440, height: 900, theme: "light" },
    { name: "tablet-dark", width: 768, height: 1024, theme: "dark" },
    { name: "mobile-light", width: 375, height: 812, theme: "light" },
    { name: "mobile-narrow-dark", width: 320, height: 780, theme: "dark" },
  ]) {
    const run = await openWatchlist(browser, scenario);
    await run.page.screenshot({ path: path.join(screenshotsDir, `${scenario.name}.png`), fullPage: true });
    report.scenarios.push({ name: scenario.name, overflow: await run.page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth) });
    report.consoleErrors.push(...run.consoleErrors);
    await run.context.close();
  }
} finally {
  await browser.close();
}

assert.equal(report.consoleErrors.length, 0, report.consoleErrors.join("\n"));
assert.ok(report.scenarios.every((scenario) => !scenario.overflow), JSON.stringify(report.scenarios));
console.log(JSON.stringify(report, null, 2));
