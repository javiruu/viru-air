import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { chromium, type BrowserContext, type Page, type Route } from "playwright";
import { createSessionToken } from "./helpers/e2e-backend";

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const TMP_DIR = path.resolve(process.cwd(), "..", "testsprite_tests", "tmp");

type Scenario = {
  id: string;
  originCountryRegex: RegExp;
  destinationCountryRegex: RegExp;
  filterMode: "default" | "relaxed";
};

type ScenarioEvidence = {
  id: string;
  status: number;
  rowCount: number;
  listVisible: boolean;
  firstRouteText: string;
  requestOriginSeedCount: number;
  requestDestinationSeedCount: number;
  responseFirstOrigin: string | null;
  responseFirstDestination: string | null;
  rescue: unknown;
  warnings: string[];
  screenshotPath: string;
  error?: string;
};

const SCENARIOS: Scenario[] = [
  {
    id: "ITALY_TO_SPAIN_DEFAULT",
    originCountryRegex: /Italy|Italia/i,
    destinationCountryRegex: /Spain|Espa.n?a/i,
    filterMode: "default",
  },
  {
    id: "SPAIN_TO_ITALY_RELAXED",
    originCountryRegex: /Spain|Espa.n?a/i,
    destinationCountryRegex: /Italy|Italia/i,
    filterMode: "relaxed",
  },
];

function formatDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function buildDeterministicDate(): string {
  if (process.env.E2E_OUTBOUND_DATE && /^\d{4}-\d{2}-\d{2}$/.test(process.env.E2E_OUTBOUND_DATE)) {
    return process.env.E2E_OUTBOUND_DATE;
  }
  const base = new Date();
  base.setDate(base.getDate() + 14);
  return formatDate(base);
}

async function openQuickSearch(context: BrowserContext) {
  let token: string;
  try {
    token = await createSessionToken();
  } catch {
    return null;
  }
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
  return page;
}

async function selectCountryOnly(page: Page, field: "origin" | "destination", countryRegex: RegExp) {
  const trigger = page.locator(".qs-route-card .qs-input-inline-action").nth(field === "origin" ? 0 : 1);
  await trigger.click();
  const modal = page.locator(".qs-airport-modal").first();
  await modal.waitFor({ state: "visible", timeout: 10000 });
  await modal.locator(".airport-country-grid .country-pill").filter({ hasText: countryRegex }).first().click();
  await modal.locator(".btn-secondary.btn-compact").first().click();
  await modal.waitFor({ state: "hidden", timeout: 10000 });
}

async function selectDate(page: Page, targetDate: string) {
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

test("testsprite real country scope: ES<->IT returns in-scope rows and evidence", async (t) => {
  await fs.mkdir(TMP_DIR, { recursive: true });
  const outboundDate = buildDeterministicDate();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const evidence: ScenarioEvidence[] = [];
  try {
    const page = await openQuickSearch(context);
    if (!page) {
      t.skip(`Quick-Search not reachable at ${BASE_URL}. Start frontend/backend and retry.`);
      return;
    }

    for (const scenario of SCENARIOS) {
      await selectCountryOnly(page, "origin", scenario.originCountryRegex);
      await selectCountryOnly(page, "destination", scenario.destinationCountryRegex);
      await selectDate(page, outboundDate);

      let capturedRequest: Record<string, unknown> = {};
      const intercept = async (route: Route) => {
        const req = route.request();
        if (req.method() !== "POST") {
          await route.continue();
          return;
        }
        const body = JSON.parse(req.postData() || "{}") as Record<string, unknown>;
        const travel = (body.travel && typeof body.travel === "object" ? body.travel : {}) as Record<string, unknown>;
        travel.date = outboundDate;
        travel.flex_before = 0;
        travel.flex_after = 0;
        body.travel = travel;

        if (scenario.filterMode === "relaxed") {
          const constraints = (body.constraints && typeof body.constraints === "object" ? body.constraints : {}) as Record<string, unknown>;
          constraints.strict_filters = false;
          constraints.departure_window = {};
          body.constraints = constraints;
          const origin = (body.origin && typeof body.origin === "object" ? body.origin : {}) as Record<string, unknown>;
          const destination = (body.destination && typeof body.destination === "object" ? body.destination : {}) as Record<string, unknown>;
          origin.include_nearby = true;
          destination.include_nearby = true;
          origin.radius_km = Math.max(150, Number(origin.radius_km || 150));
          destination.radius_km = Math.max(150, Number(destination.radius_km || 150));
          body.origin = origin;
          body.destination = destination;
        }

        capturedRequest = body;
        await route.continue({
          postData: JSON.stringify(body),
          headers: {
            ...req.headers(),
            "content-type": "application/json",
          },
        });
      };

      await page.route("**/api/v1/search/quick", intercept);
      const quickResponsePromise = page.waitForResponse((response) => response.url().includes("/api/v1/search/quick"), {
        timeout: 45000,
      });
      await page.getByRole("button", { name: /buscar|search/i }).first().click();
      const quickResponse = await quickResponsePromise;
      await page.unroute("**/api/v1/search/quick", intercept);

      const quickJson = (await quickResponse.json().catch(() => ({}))) as {
        meta?: { rescue?: unknown };
        filters?: { warnings?: string[] };
        results?: Array<{ origin?: string; destination?: string }>;
      };
      await page.waitForTimeout(1200);

      const rowCount = await page.locator(".qs-result-row").count();
      const listVisible = await page.locator(".qs-results-list").first().isVisible().catch(() => false);
      const firstRouteText = rowCount > 0
        ? (await page.locator(".qs-result-route").first().innerText()).replace(/\s+/g, " ").trim()
        : "";
      const screenshotPath = path.join(TMP_DIR, `qs_country_scope_real_${scenario.id.toLowerCase()}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });

      const requestOriginSeed = ((capturedRequest.origin as { seed_iata_list?: string[] } | undefined)?.seed_iata_list || []);
      const requestDestinationSeed = ((capturedRequest.destination as { seed_iata_list?: string[] } | undefined)?.seed_iata_list || []);
      const responseFirstOrigin = quickJson.results?.[0]?.origin || null;
      const responseFirstDestination = quickJson.results?.[0]?.destination || null;
      const scenarioEvidence: ScenarioEvidence = {
        id: scenario.id,
        status: quickResponse.status(),
        rowCount,
        listVisible,
        firstRouteText,
        requestOriginSeedCount: requestOriginSeed.length,
        requestDestinationSeedCount: requestDestinationSeed.length,
        responseFirstOrigin,
        responseFirstDestination,
        rescue: quickJson.meta?.rescue || null,
        warnings: quickJson.filters?.warnings || [],
        screenshotPath,
      };
      if (quickResponse.status() !== 200) {
        scenarioEvidence.error = `${scenario.id}: /search/quick must return 200`;
      } else if (requestOriginSeed.length <= 1) {
        scenarioEvidence.error = `${scenario.id}: origin.seed_iata_list must contain >1 IATA`;
      } else if (requestDestinationSeed.length <= 1) {
        scenarioEvidence.error = `${scenario.id}: destination.seed_iata_list must contain >1 IATA`;
      } else if (!listVisible) {
        scenarioEvidence.error = `${scenario.id}: .qs-results-list must be visible`;
      } else if (rowCount <= 0) {
        scenarioEvidence.error = `${scenario.id}: must render >=1 .qs-result-row`;
      } else if (!responseFirstOrigin || !requestOriginSeed.includes(responseFirstOrigin)) {
        scenarioEvidence.error = `${scenario.id}: first row origin must belong to origin seed pool`;
      } else if (!responseFirstDestination || !requestDestinationSeed.includes(responseFirstDestination)) {
        scenarioEvidence.error = `${scenario.id}: first row destination must belong to destination seed pool`;
      }
      evidence.push(scenarioEvidence);
    }
  } finally {
    await browser.close();
  }

  await fs.writeFile(
    path.join(TMP_DIR, "quick_search_country_scope_real_report.json"),
    JSON.stringify({ generated_at: new Date().toISOString(), evidence }, null, 2),
    "utf8",
  );

  const failures = evidence.filter((item) => item.error);
  assert.equal(
    failures.length,
    0,
    failures.map((item) => `${item.id}: ${item.error}`).join(" | "),
  );
});
