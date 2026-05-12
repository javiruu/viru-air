import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { chromium, type BrowserContext, type Page, type Route } from "playwright";

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const API_BASE = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const TMP_DIR = path.resolve(process.cwd(), "..", "testsprite_tests", "tmp");

type RouteCase = {
  id: string;
  origin: string;
  destination: string;
};

type QuickResponseShape = {
  query?: {
    origin?: { seed_iata?: string };
    destination?: { seed_iata?: string };
    travel?: { date?: string };
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

const CANDIDATE_ROUTES: RouteCase[] = [
  { id: "QS301", origin: "BCN", destination: "DUB" },
  { id: "QS302", origin: "VLC", destination: "LIS" },
  { id: "QS303", origin: "MAD", destination: "OPO" },
  { id: "QS304", origin: "AGP", destination: "LIS" },
];

function buildDeterministicFutureDateIso(): string {
  if (process.env.E2E_OUTBOUND_DATE && /^\d{4}-\d{2}-\d{2}$/.test(process.env.E2E_OUTBOUND_DATE)) {
    return process.env.E2E_OUTBOUND_DATE;
  }
  const date = new Date();
  date.setDate(date.getDate() + 1);
  return date.toISOString().slice(0, 10);
}

async function createSessionToken() {
  try {
    const email = `codex-testsprite-ultra-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
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

async function selectAirport(page: Page, field: "origin" | "destination", iata: string) {
  const selector = field === "origin" ? 'input[name="origin_iata"]' : 'input[name="destination_iata"]';
  const suggestionsSelector = field === "origin" ? "#origin-suggestions" : "#destination-suggestions";
  const input = page.locator(selector);
  await input.click();
  await input.fill(iata.toLowerCase());
  await page.waitForTimeout(250);

  const exactOption = page.locator(`${suggestionsSelector} button`).filter({
    has: page.locator("strong", { hasText: iata.toUpperCase() }),
  });
  if ((await exactOption.count()) > 0) {
    await exactOption.first().click();
    return;
  }
  await input.fill(iata.toUpperCase());
  await input.press("Tab");
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

async function runStrictRouteCase(page: Page, routeCase: RouteCase, targetDate: string) {
  const screenshotPath = path.join(TMP_DIR, `${routeCase.id.toLowerCase()}_ultra.png`);
  const originInput = page.locator('input[name="origin_iata"]');
  const destinationInput = page.locator('input[name="destination_iata"]');
  await originInput.fill("");
  await destinationInput.fill("");
  await selectAirport(page, "origin", routeCase.origin);
  await selectAirport(page, "destination", routeCase.destination);
  await selectDeterministicFutureDate(page, targetDate);

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
    await route.continue({
      postData: capturedRequestBody,
      headers: { ...request.headers(), "content-type": "application/json" },
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

  const resultRows = page.locator(".qs-result-row");
  const rowCount = await resultRows.count();
  const listVisible = await page.locator(".qs-results-list").first().isVisible().catch(() => false);
  const statePanelVisible = await page.locator(".qs-state-panel").first().isVisible().catch(() => false);

  return {
    status,
    screenshotPath,
    capturedRequestBody,
    response: quickJson,
    rowCount,
    listVisible,
    statePanelVisible,
  };
}

test("testsprite ultra-strict: route contract and visible results stay consistent", async (t) => {
  await fs.mkdir(TMP_DIR, { recursive: true });
  const targetDate = buildDeterministicFutureDateIso();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  try {
    const page = await openQuickSearch(context);
    if (!page) {
      t.skip(`Quick-Search not reachable at ${BASE_URL} or backend ${API_BASE}. Start frontend/backend and retry.`);
      return;
    }
    let validated = 0;
    const evidence: Array<Record<string, unknown>> = [];

    for (const routeCase of CANDIDATE_ROUTES) {
      const result = await runStrictRouteCase(page, routeCase, targetDate);
      const responseResults = Array.isArray(result.response.results) ? result.response.results : [];
      const rescue = result.response.meta?.rescue;
      const warnings = result.response.filters?.warnings || [];

      evidence.push({
        id: routeCase.id,
        route: `${routeCase.origin}-${routeCase.destination}`,
        status: result.status,
        rows: result.rowCount,
        listVisible: result.listVisible,
        rescue,
        warnings,
        screenshotPath: result.screenshotPath,
      });

      assert.equal(result.status, 200, `API /search/quick must return 200 (${routeCase.id}).`);
      assert.ok(result.capturedRequestBody.includes(targetDate), `Request body must contain deterministic date (${routeCase.id}).`);
      assert.equal(result.response.query?.origin?.seed_iata, routeCase.origin, `Response query origin mismatch (${routeCase.id}).`);
      assert.equal(result.response.query?.destination?.seed_iata, routeCase.destination, `Response query destination mismatch (${routeCase.id}).`);
      assert.equal(result.response.query?.travel?.date, targetDate, `Response query date mismatch (${routeCase.id}).`);
      if (rescue) {
        assert.ok(Array.isArray(rescue.pass_summaries), `meta.rescue.pass_summaries must be an array when rescue exists (${routeCase.id}).`);
      }

      if (responseResults.length > 0) {
        assert.equal(result.listVisible, true, `Results list must be visible when response has rows (${routeCase.id}).`);
        assert.ok(result.rowCount > 0, `DOM must render at least one row when response has results (${routeCase.id}).`);
        validated += 1;
      } else {
        assert.equal(result.statePanelVisible, true, `State panel must be visible when response is empty (${routeCase.id}).`);
        assert.ok(
          rescue?.attempted || warnings.length > 0,
          `Empty response must expose rescue attempt or explicit warnings (${routeCase.id}).`,
        );
      }
    }

    await fs.writeFile(
      path.join(TMP_DIR, "quick_search_ultra_strict_report.json"),
      JSON.stringify({ generated_at: new Date().toISOString(), targetDate, evidence }, null, 2),
      "utf8",
    );

    assert.ok(validated >= 2, `Expected at least 2 strict routes with visible results, got ${validated}.`);
  } finally {
    await browser.close();
  }
});

test("testsprite ultra-strict: empty response must render explicit empty-state evidence", async (t) => {
  await fs.mkdir(TMP_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  try {
    const page = await openQuickSearch(context);
    if (!page) {
      t.skip(`Quick-Search not reachable at ${BASE_URL} or backend ${API_BASE}. Start frontend/backend and retry.`);
      return;
    }
    const targetDate = buildDeterministicFutureDateIso();
    let interceptedQuick = 0;

    await selectAirport(page, "origin", "MAD");
    await selectAirport(page, "destination", "BCN");
    await selectDeterministicFutureDate(page, targetDate);

    await page.route("**/api/v1/search/quick*", async (route) => {
      interceptedQuick += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          query: {
            origin: { seed_iata: "MAD", include_nearby: false, radius_km: 150, max_candidates: 6 },
            destination: { seed_iata: "BCN", include_nearby: false, radius_km: 150, max_candidates: 6 },
            travel: { date: targetDate, flex_before: 0, flex_after: 0, travel_dates: [targetDate] },
            constraints: {
              departure_window: { after: "07:00", before: "22:00" },
              exclude_origins: [],
              exclude_destinations: [],
              strict_filters: true,
              include_stops: false,
              max_stops: 0,
              duration_max_min: null,
              risk_allowed: null,
              soft_filters_weight: 0.6,
            },
            execution: { max_pairs: 12, max_requests: 120, timeout_ms: 8000, concurrency_limit: 6 },
            expanded_origins: [],
            expanded_destinations: [],
          },
          meta: {
            query_trace_id: "qs_mock_ultra",
            contract_version: "quick_search.v2",
            rescue: {
              attempted: true,
              applied_steps: ["pass_2_rescue_date", "pass_3_rescue_nearby"],
              winning_step: "pass_3_rescue_nearby",
              pass_summaries: [
                { step: "pass_1_exact", result_count: 0, warnings: ["ryanair_availability_failed_partial"] },
                { step: "pass_2_rescue_date", result_count: 0, warnings: ["ryanair_availability_failed_partial"] },
                { step: "pass_3_rescue_nearby", result_count: 1, warnings: ["ryanair_availability_failed_partial"] },
              ],
            },
          },
          filters: {
            applied: { departure_window: { after: "07:00", before: "22:00" } },
            relaxed: [],
            warnings: ["ryanair_availability_failed_partial", "rescue_mode_applied"],
            discarded: 0,
          },
          results: [],
        }),
      });
    });

    const quickResponsePromise = page.waitForResponse((response) => response.url().includes("/api/v1/search/quick"), { timeout: 30000 });
    await page.getByRole("button", { name: /buscar|search/i }).first().click();
    const quickResponse = await quickResponsePromise;
    await page.waitForTimeout(900);

    assert.equal(quickResponse.status(), 200);
    assert.ok(interceptedQuick >= 1, "Mocked /search/quick should be intercepted at least once.");

    const mockedBody = (await quickResponse.json().catch(() => ({}))) as QuickResponseShape;
    const resultsListVisible = await page.locator(".qs-results-list").first().isVisible().catch(() => false);

    assert.equal(resultsListVisible, false, "Results list must not be visible when API returns empty results.");
    assert.ok(Array.isArray(mockedBody.results) && mockedBody.results.length === 0, "Mocked quick-search response must remain empty.");
    assert.ok(
      (mockedBody.filters?.warnings || []).includes("rescue_mode_applied"),
      "Empty mocked response must contain explicit degraded warning (rescue_mode_applied).",
    );
  } finally {
    await browser.close();
  }
});
