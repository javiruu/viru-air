import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { chromium, type BrowserContext, type Page, type Route } from "playwright";

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const API_BASE = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const TMP_DIR = path.resolve(process.cwd(), "..", "testsprite_tests", "tmp");

type QuickResponseShape = {
  query?: {
    origin?: { seed_iata?: string; seed_iata_list?: string[] };
    destination?: { seed_iata?: string; seed_iata_list?: string[] };
    travel?: { date?: string; flex_before?: number; flex_after?: number; travel_dates?: string[] };
  };
  meta?: {
    rescue?: {
      attempted?: boolean;
      winning_step?: string | null;
      pass_summaries?: Array<{ step?: string; result_count?: number; warnings?: string[] }>;
    };
  };
  filters?: {
    warnings?: string[];
    relaxed?: string[];
  };
  results?: Array<{ origin?: string; destination?: string }>;
};

function formatDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function buildDeterministicDateCandidates(): string[] {
  if (process.env.E2E_OUTBOUND_DATE && /^\d{4}-\d{2}-\d{2}$/.test(process.env.E2E_OUTBOUND_DATE)) {
    return [process.env.E2E_OUTBOUND_DATE];
  }
  const base = new Date();
  const offsets = [2, 3, 4];
  return offsets.map((offset) => {
    const next = new Date(base);
    next.setDate(next.getDate() + offset);
    return formatDate(next);
  });
}

async function createSessionToken() {
  try {
    const email = `codex-testsprite-country-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
    const password = "Test123456!";
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) return null;
    const auth = (await response.json()) as { access_token?: string };
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
  try {
    await Promise.all([
      page.waitForResponse((response) => response.url().includes("/api/v1/airports/seeds") && response.status() === 200, {
        timeout: 30000,
      }),
      page.goto(`${BASE_URL}/quick-search`, { waitUntil: "networkidle", timeout: 30000 }),
    ]);
    await page.locator('input[name="origin_iata"]').waitFor({ state: "visible", timeout: 10000 });
    await page.locator('input[name="destination_iata"]').waitFor({ state: "visible", timeout: 10000 });
  } catch {
    await page.close();
    return null;
  }
  return page;
}

async function selectCountryOnly(page: Page, field: "origin" | "destination", countryRegex: RegExp) {
  const trigger = page.locator(".qs-route-card .qs-input-inline-action").nth(field === "origin" ? 0 : 1);
  await trigger.click();
  const modal = page.locator(".qs-airport-modal").first();
  await modal.waitFor({ state: "visible", timeout: 10000 });

  const countryButton = modal.locator(".airport-country-grid .country-pill").filter({ hasText: countryRegex }).first();
  await countryButton.click();
  const countryOnlyButton = modal.locator(".btn-secondary.btn-compact").first();
  await countryOnlyButton.click();
  await modal.waitFor({ state: "hidden", timeout: 10000 });
}

async function selectDeterministicFutureDate(page: Page, targetDate: string) {
  const datePicker = page.locator('[data-ui="qs-date-picker-v2"]').first();
  await datePicker.locator(".qs-date-trigger").click();
  const targetButton = page.locator(`.qs-date-popover .qs-date-day[data-date="${targetDate}"]:not(.is-disabled):not(.is-outside)`).first();
  if (await targetButton.count()) {
    await targetButton.click();
  } else {
    await page.locator(".qs-date-popover .qs-date-day:not(.is-disabled):not(.is-outside)").first().click();
  }
  await page.keyboard.press("Escape");
}

async function runCountryScopeAttempt(page: Page, targetDate: string) {
  const screenshotPath = path.join(TMP_DIR, `qs_country_scope_${targetDate}.png`);
  let capturedRequestBody = "";

  const rewriteQuickRequest = async (route: Route) => {
    const request = route.request();
    if (request.method() !== "POST") {
      await route.continue();
      return;
    }
    const payload = JSON.parse(request.postData() || "{}") as Record<string, unknown>;
    const travel = (payload.travel && typeof payload.travel === "object" ? payload.travel : {}) as Record<string, unknown>;
    travel.date = targetDate;
    travel.flex_before = 0;
    travel.flex_after = 0;
    payload.travel = travel;
    capturedRequestBody = JSON.stringify(payload);
    const typedPayload = payload as {
      origin?: { seed_iata?: string; seed_iata_list?: string[] };
      destination?: { seed_iata?: string; seed_iata_list?: string[] };
      travel?: { date?: string };
    };
    const originSeed = typedPayload.origin?.seed_iata || "FCO";
    const destinationSeed = typedPayload.destination?.seed_iata || "MAD";
    const mockedBody: QuickResponseShape = {
      query: {
        origin: {
          seed_iata: originSeed,
          seed_iata_list: typedPayload.origin?.seed_iata_list || [],
        },
        destination: {
          seed_iata: destinationSeed,
          seed_iata_list: typedPayload.destination?.seed_iata_list || [],
        },
        travel: {
          date: targetDate,
          flex_before: 0,
          flex_after: 0,
          travel_dates: [targetDate],
        },
      },
      meta: {
        rescue: {
          attempted: false,
          winning_step: null,
          pass_summaries: [{ step: "pass_1_exact", result_count: 1, warnings: [] }],
        },
      },
      filters: {
        warnings: [],
        relaxed: [],
      },
      results: [{ origin: originSeed, destination: destinationSeed }],
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockedBody),
    });
  };

  await page.route("**/api/v1/search/quick", rewriteQuickRequest);
  let quickJson: QuickResponseShape = {};
  let status = 0;
  try {
    const quickResponsePromise = page.waitForResponse((response) => response.url().includes("/api/v1/search/quick"), { timeout: 30000 });
    await page.getByRole("button", { name: /buscar|search/i }).first().click();
    const quickResponse = await quickResponsePromise;
    status = quickResponse.status();
    quickJson = (await quickResponse.json().catch(() => ({}))) as QuickResponseShape;
  } finally {
    await page.unroute("**/api/v1/search/quick", rewriteQuickRequest);
  }

  await page.waitForTimeout(1200);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  const rowCount = await page.locator(".qs-result-row").count();
  const listVisible = await page.locator(".qs-results-list").first().isVisible().catch(() => false);

  return {
    status,
    rowCount,
    listVisible,
    quickJson,
    capturedRequestBody,
    screenshotPath,
  };
}

test("testsprite country-scope ultra: Italy -> Spain sends seed_iata_list and renders visible rows", async (t) => {
  await fs.mkdir(TMP_DIR, { recursive: true });
  const dateCandidates = buildDeterministicDateCandidates();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  try {
    const page = await openQuickSearch(context);
    if (!page) {
      t.skip(`Quick-Search not reachable at ${BASE_URL} or backend ${API_BASE}. Start frontend/backend and retry.`);
      return;
    }
    await selectCountryOnly(page, "origin", /Italy|Italia/i);
    await selectCountryOnly(page, "destination", /Spain|Espa.n?a/i);

    const targetDate = dateCandidates[0];
    await selectDeterministicFutureDate(page, targetDate);
    const run = await runCountryScopeAttempt(page, targetDate);
    const parsedRequest = JSON.parse(run.capturedRequestBody || "{}") as {
      origin?: { seed_iata_list?: string[] };
      destination?: { seed_iata_list?: string[] };
    };
    const originSeedList = Array.isArray(parsedRequest.origin?.seed_iata_list) ? parsedRequest.origin?.seed_iata_list : [];
    const destinationSeedList = Array.isArray(parsedRequest.destination?.seed_iata_list) ? parsedRequest.destination?.seed_iata_list : [];
    const responseResults = Array.isArray(run.quickJson.results) ? run.quickJson.results : [];

    const attempts: Array<Record<string, unknown>> = [
      {
        targetDate,
        status: run.status,
        rows: run.rowCount,
        listVisible: run.listVisible,
        originSeedCount: originSeedList.length,
        destinationSeedCount: destinationSeedList.length,
        warnings: run.quickJson.filters?.warnings || [],
        rescue: run.quickJson.meta?.rescue || null,
        screenshotPath: run.screenshotPath,
      },
    ];

    await fs.writeFile(
      path.join(TMP_DIR, "quick_search_country_scope_ultra_report.json"),
      JSON.stringify({ generated_at: new Date().toISOString(), attempts }, null, 2),
      "utf8",
    );

    assert.equal(run.status, 200, `API /search/quick must return 200 (${targetDate}).`);
    assert.ok(originSeedList.length > 1, `Request must include origin.seed_iata_list>1 (${targetDate}).`);
    assert.ok(destinationSeedList.length > 1, `Request must include destination.seed_iata_list>1 (${targetDate}).`);
    assert.ok(responseResults.length > 0, `Mocked quick-search response must contain rows (${targetDate}).`);
    assert.equal(run.listVisible, true, `Results list must be visible when API returns rows (${targetDate}).`);
    assert.ok(run.rowCount > 0, `DOM must render at least one row when API has results (${targetDate}).`);
  } finally {
    await browser.close();
  }
});
