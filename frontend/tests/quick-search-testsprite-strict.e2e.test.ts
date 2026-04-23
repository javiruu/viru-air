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

type RouteEvidence = {
  id: string;
  route: string;
  responseStatus: number | null;
  responseOk: boolean;
  responseSummary: string;
  resultsVisible: boolean;
  resultRows: number;
  firstRouteText: string;
  stateHeadline: string;
  probableCauses: string[];
  screenshotPath: string;
  error?: string;
};

const ROUTE_CASES: RouteCase[] = [
  { id: "QS201", origin: "BCN", destination: "DUB" },
  { id: "QS202", origin: "VLC", destination: "LIS" },
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
  const email = `codex-testsprite-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  const password = "Test123456!";
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new Error(`register_failed_${response.status}`);
  }
  const auth = (await response.json()) as { access_token?: string };
  if (!auth.access_token) {
    throw new Error("register_missing_token");
  }
  return auth.access_token;
}

async function openQuickSearch(context: BrowserContext) {
  const token = await createSessionToken();
  await context.addInitScript((value) => {
    window.localStorage.setItem("viru_token", value);
  }, token);

  const page = await context.newPage();
  await Promise.all([
    page.waitForResponse((response) => response.url().includes("/api/v1/airports/seeds") && response.status() === 200, {
      timeout: 30000,
    }),
    page.goto(`${BASE_URL}/quick-search`, { waitUntil: "networkidle", timeout: 30000 }),
  ]);

  await page.locator('input[name="origin_iata"]').waitFor({ state: "visible", timeout: 10000 });
  await page.locator('input[name="destination_iata"]').waitFor({ state: "visible", timeout: 10000 });
  await page.locator('[data-ui="qs-date-picker-v2"]').first().waitFor({ state: "visible", timeout: 10000 });
  return page;
}

async function selectAirport(page: Page, field: "origin" | "destination", iata: string) {
  const selector = field === "origin" ? 'input[name="origin_iata"]' : 'input[name="destination_iata"]';
  const suggestionsSelector = field === "origin" ? "#origin-suggestions" : "#destination-suggestions";
  const input = page.locator(selector);

  await input.click();
  await input.fill(iata.toLowerCase());
  await page.waitForTimeout(300);

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

async function selectDeterministicFutureDate(page: Page) {
  const targetDate = buildDeterministicFutureDateIso();
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

async function runRouteCase(page: Page, routeCase: RouteCase): Promise<RouteEvidence> {
  const routeLabel = `${routeCase.origin} -> ${routeCase.destination}`;
  const screenshotPath = path.join(TMP_DIR, `${routeCase.id.toLowerCase()}_strict.png`);
  const targetDate = buildDeterministicFutureDateIso();
  let responseStatus: number | null = null;
  let responseSummary = "";

  try {
    const originInput = page.locator('input[name="origin_iata"]');
    const destinationInput = page.locator('input[name="destination_iata"]');
    await originInput.fill("");
    await destinationInput.fill("");

    await selectAirport(page, "origin", routeCase.origin);
    await selectAirport(page, "destination", routeCase.destination);
    await selectDeterministicFutureDate(page);

    const rewriteQuickRequest = async (route: Route) => {
      const request = route.request();
      if (request.method() !== "POST") {
        await route.continue();
        return;
      }
      const rawBody = request.postData() || "{}";
      let payload: Record<string, unknown> = {};
      try {
        payload = JSON.parse(rawBody) as Record<string, unknown>;
      } catch {
        payload = {};
      }
      if (payload.travel && typeof payload.travel === "object") {
        const travel = payload.travel as Record<string, unknown>;
        travel.date = targetDate;
        travel.flex_before = 0;
        travel.flex_after = 0;
      }
      await route.continue({
        postData: JSON.stringify(payload),
        headers: {
          ...request.headers(),
          "content-type": "application/json",
        },
      });
    };
    await page.route("**/api/v1/search/quick", rewriteQuickRequest);

    let quickResponse;
    try {
      const quickResponsePromise = page.waitForResponse(
        (response) => response.url().includes("/api/v1/search/quick"),
        { timeout: 30000 },
      );
      await page.getByRole("button", { name: /buscar|search/i }).first().click();
      quickResponse = await quickResponsePromise;
    } finally {
      await page.unroute("**/api/v1/search/quick", rewriteQuickRequest);
    }
    responseStatus = quickResponse.status();
    const responseJson = await quickResponse.json().catch(() => null);
    if (responseJson && typeof responseJson === "object") {
      const asRecord = responseJson as Record<string, unknown>;
      const resultsCandidate =
        (Array.isArray(asRecord.results) && asRecord.results) ||
        (Array.isArray(asRecord.items) && asRecord.items) ||
        (Array.isArray(asRecord.flights) && asRecord.flights) ||
        [];
      const relaxCandidate =
        asRecord.relax_preview ??
        asRecord.relaxPreview ??
        asRecord.degraded ??
        asRecord.partial ??
        null;
      responseSummary = JSON.stringify({
        topLevelKeys: Object.keys(asRecord).slice(0, 20),
        resultsLength: Array.isArray(resultsCandidate) ? resultsCandidate.length : null,
        partialFlag: asRecord.partial ?? null,
        degradedFlag: asRecord.degraded ?? null,
        relaxPreview: relaxCandidate,
      }).slice(0, 500);
    } else {
      const responseText = await quickResponse.text().catch(() => "");
      const compact = responseText.replace(/\s+/g, " ").trim();
      responseSummary = compact.slice(0, 500);
    }

    await page.waitForTimeout(1200);

    const resultsList = page.locator(".qs-results-list").first();
    const resultRows = page.locator(".qs-result-row");
    const resultsVisible = await resultsList.isVisible().catch(() => false);
    const rowCount = await resultRows.count();
    const firstRouteText = rowCount > 0
      ? ((await page.locator(".qs-result-route").first().innerText()).replace(/\s+/g, " ").trim())
      : "";
    const stateHeadline = (await page.locator(".qs-state-panel h3, .qs-state-panel strong").first().innerText().catch(() => "")).trim();
    const probableCauses = (await page.locator(".qs-state-panel li").allInnerTexts().catch(() => []))
      .map((item) => item.replace(/\s+/g, " ").trim())
      .filter(Boolean);

    await page.screenshot({ path: screenshotPath, fullPage: true });

    assert.equal(responseStatus, 200, `Quick-search API failed for ${routeLabel} with status ${responseStatus}.`);
    assert.equal(resultsVisible, true, `Results list is not visible for ${routeLabel}.`);
    assert.ok(rowCount > 0, `No result rows rendered for ${routeLabel}.`);
    assert.match(firstRouteText, new RegExp(routeCase.origin, "i"));
    assert.match(firstRouteText, new RegExp(routeCase.destination, "i"));

    return {
      id: routeCase.id,
      route: routeLabel,
      responseStatus,
      responseOk: true,
      responseSummary,
      resultsVisible,
      resultRows: rowCount,
      firstRouteText,
      stateHeadline,
      probableCauses,
      screenshotPath,
    };
  } catch (error) {
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => undefined);
    return {
      id: routeCase.id,
      route: routeLabel,
      responseStatus,
      responseOk: responseStatus === 200,
      responseSummary,
      resultsVisible: false,
      resultRows: 0,
      firstRouteText: "",
      stateHeadline: "",
      probableCauses: [],
      screenshotPath,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

test("testsprite strict quick-search routes render visible results without false positives", async () => {
  await fs.mkdir(TMP_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });

  const evidence: RouteEvidence[] = [];
  try {
    const page = await openQuickSearch(context);
    for (const routeCase of ROUTE_CASES) {
      const result = await runRouteCase(page, routeCase);
      evidence.push(result);
    }
  } finally {
    await browser.close();
  }

  const reportPath = path.join(TMP_DIR, "quick_search_strict_results_report.json");
  await fs.writeFile(reportPath, JSON.stringify({ generated_at: new Date().toISOString(), evidence }, null, 2), "utf8");

  const failures = evidence.filter((item) => item.error);
  assert.equal(
    failures.length,
    0,
    `Quick-search strict checks failed in ${failures.length} case(s): ${failures.map((f) => `${f.id} ${f.route}: ${f.error}`).join(" | ")}`,
  );
});
