import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = process.env.E2E_BASE_URL || "http://127.0.0.1:3101";
const outputDir = path.resolve(process.env.ADMIN_HOTELS_OUTPUT_DIR || "../docs/qa/evidence/h41-admin-hotels-observability");
const scenarios = [
  { name: "desktop-light", theme: "light", viewport: { width: 1440, height: 1000 } },
  { name: "desktop-dark", theme: "dark", viewport: { width: 1440, height: 1000 } },
  { name: "mobile-light", theme: "light", viewport: { width: 390, height: 844 } },
  { name: "mobile-dark", theme: "dark", viewport: { width: 390, height: 844 } },
];

const metrics = [
  { metric_date: "2026-08-09", metric_name: "sweep_run", provider: "local", outcome: "completed", count: 18, updated_at: "2026-08-09T12:10:00" },
  { metric_date: "2026-08-09", metric_name: "hotel_delivery", provider: "local", outcome: "retried", count: 2, updated_at: "2026-08-09T12:11:00" },
  { metric_date: "2026-08-08", metric_name: "alert_event", provider: "mock", outcome: "created", count: 7, updated_at: "2026-08-08T18:20:00" },
  { metric_date: "2026-08-08", metric_name: "hotel_delivery", provider: "unknown", outcome: "failed", count: 1, updated_at: "2026-08-08T18:21:00" },
];

await fs.mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const report = {
  generatedAt: new Date().toISOString(),
  runner: "qa_admin_hotels_observability",
  browserEngine: "chromium",
  browserVersion: browser.version(),
  baseUrl,
  humanReview: "pending",
  scenarios: [],
};

function responseJson(body, status = 200) {
  return { status, contentType: "application/json", body: JSON.stringify(body) };
}

async function runScenario(scenario) {
  const context = await browser.newContext({
    viewport: scenario.viewport,
    colorScheme: scenario.theme,
    isMobile: scenario.viewport.width < 500,
    hasTouch: scenario.viewport.width < 500,
  });
  await context.addInitScript(({ theme }) => {
    window.localStorage.setItem("viru_token", "qa-observability-token-opaque");
    window.localStorage.setItem("viru_locale", "es");
    window.localStorage.setItem("viru-theme", theme);
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, { theme: scenario.theme });

  const page = await context.newPage();
  const consoleErrors = [];
  const requests = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.includes("/api/v1/admin/hotels/observability")) {
      requests.push({ method: request.method(), url: `${url.pathname}?present` });
    }
    if (url.pathname.includes("/api/v1/admin/hotels/health")) {
      requests.push({ method: request.method(), url: `${url.pathname}?present` });
    }
    if (url.pathname.includes("/api/v1/admin/hotels/runs")) {
      requests.push({ method: request.method(), url: `${url.pathname}?present` });
    }
    if (url.pathname.includes("/api/v1/admin/hotels/provider-controls")) {
      requests.push({ method: request.method(), url: `${url.pathname}?present` });
    }
    if (url.pathname.includes("/api/v1/admin/hotels/sweep-leases")) {
      requests.push({ method: request.method(), url: `${url.pathname}?present` });
    }
    if (url.pathname.includes("/api/v1/admin/hotels/provider-outcomes")) {
      requests.push({ method: request.method(), url: `${url.pathname}?present` });
    }
  });

  await page.route("**/api/v1/auth/me", (route) => route.fulfill(responseJson({ id: "qa-admin", email: "qa-admin@example.invalid", locale: "es", is_admin: true })));
  await page.route("**/api/v1/notifications/summary", (route) => route.fulfill(responseJson({ unread: 0 })));
  await page.route("**/api/v1/admin/hotels/runs**", (route) => route.fulfill(responseJson({
    limit: 8,
    runs: [
      { provider: "local", status: "completed", started_at: "2026-08-09T12:10:00", finished_at: "2026-08-09T12:10:01", duration_seconds: 1, items_processed: 18, has_error: false, outcomes: { snapshots_created: 18 } },
      { provider: "mock", status: "partial", started_at: "2026-08-09T11:10:00", finished_at: "2026-08-09T11:10:03", duration_seconds: 3, items_processed: 4, has_error: true, outcomes: { provider_fetch_failed: 1 } },
    ],
  })));
  await page.route("**/api/v1/admin/hotels/provider-outcomes**", (route) => route.fulfill(responseJson({
    limit: 20,
    generated_at: "2026-08-09T12:12:00",
    sample_size: 2,
    providers: [
      { provider: "local", runs: 2, statuses: { running: 0, completed: 1, partial: 1, failed: 0, skipped: 0, unknown: 0 }, outcomes: { offers_scanned: 5, snapshots_created: 3, provider_fetch_failed: 1 } },
    ],
    totals: { offers_scanned: 5, snapshots_created: 3, provider_fetch_failed: 1 },
  })));
  await page.route("**/api/v1/admin/hotels/sweep-leases**", (route) => route.fulfill(responseJson({
    limit: 20,
    generated_at: "2026-08-09T12:12:00",
    sample_size: 2,
    attention_count: 1,
    counts: { queued: 0, running: 0, expired: 1, done: 1, partial: 0, skipped: 0, failed: 0, unknown: 0 },
    leases: [
      { state: "expired", attempt_count: 2, lease_expires_at: "2026-08-09T12:00:00", finished_at: null, last_error_code: null, has_provider_run: true, attention: true, updated_at: "2026-08-09T12:00:00" },
      { state: "done", attempt_count: 1, lease_expires_at: null, finished_at: "2026-08-09T11:00:00", last_error_code: null, has_provider_run: false, attention: false, updated_at: "2026-08-09T11:00:00" },
    ],
  })));
  await page.route("**/api/v1/admin/hotels/provider-controls**", (route) => route.fulfill(responseJson({
    limit: 50,
    budgets: [
      { provider: "makcorps", operation: "revalidation", window_key: "2026-08-09", hard_limit: 10, units_reserved: 2, units_used: 3, units_released: 1, units_remaining: 5, window_expires_at: "2026-08-10T00:00:00", source: "local_config" },
    ],
    circuits: [
      { provider: "makcorps", operation: "area_search", status: "open", consecutive_failures: 3, failure_threshold: 3, opened_at: "2026-08-09T12:00:00", next_probe_at: "2026-08-09T12:05:00", last_error_code: "timeout", updated_at: "2026-08-09T12:00:00" },
    ],
  })));
  await page.route("**/api/v1/admin/hotels/health**", (route) => route.fulfill(responseJson({
    status: "degraded",
    generated_at: "2026-08-09T12:12:00",
    window_hours: 24,
    latest_run: {
      provider: "local",
      status: "completed",
      started_at: "2026-08-09T12:10:00",
      finished_at: "2026-08-09T12:10:01",
      age_seconds: 121,
    },
    providers: [
      { provider: "local", status: "degraded", runs: 1, running: 0, completed: 1, partial: 0, failed: 0, skipped: 0, deliveries_failed: 0, last_run_at: "2026-08-09T12:10:00", last_run_status: "completed", last_finished_at: "2026-08-09T12:10:01", age_seconds: 121 },
      { provider: "makcorps", status: "unknown", runs: 0, running: 0, completed: 0, partial: 0, failed: 0, skipped: 0, deliveries_failed: 0, last_run_at: null, last_run_status: null, last_finished_at: null, age_seconds: null },
      { provider: "mock", status: "unknown", runs: 0, running: 0, completed: 0, partial: 0, failed: 0, skipped: 0, deliveries_failed: 0, last_run_at: null, last_run_status: null, last_finished_at: null, age_seconds: null },
      { provider: "unknown", status: "unknown", runs: 0, running: 0, completed: 0, partial: 0, failed: 0, skipped: 0, deliveries_failed: 0, last_run_at: null, last_run_status: null, last_finished_at: null, age_seconds: null },
    ],
  })));
  await page.route("**/api/v1/admin/hotels/observability**", async (route) => {
    const url = new URL(route.request().url());
    const selectedProvider = url.searchParams.get("provider");
    const selectedMetric = url.searchParams.get("metric_name");
    const selectedOutcome = url.searchParams.get("outcome");
    const filtered = metrics.filter((metric) =>
      (!selectedProvider || metric.provider === selectedProvider)
      && (!selectedMetric || metric.metric_name === selectedMetric)
      && (!selectedOutcome || metric.outcome === selectedOutcome),
    );
    await route.fulfill(responseJson({ days: Number(url.searchParams.get("days") || 7), metrics: filtered }));
  });

  await page.goto(`${baseUrl}/admin/hotels-observability`, { waitUntil: "networkidle", timeout: 60_000 });
  await page.getByRole("heading", { name: /Observabilidad hotelera|Hotel observability/i }).waitFor({ state: "visible", timeout: 30_000 });
  await page.getByRole("heading", { name: /Ledger operativo|Operational ledger/i }).waitFor({ state: "visible", timeout: 30_000 });
  await page.getByRole("heading", { name: /Runs recientes|Recent runs/i }).waitFor({ state: "visible", timeout: 30_000 });
  await page.getByRole("heading", { name: /Leases del sweep|Sweep leases/i }).waitFor({ state: "visible", timeout: 30_000 });
  await page.getByRole("heading", { name: /Outcomes por provider|Provider outcomes/i }).waitFor({ state: "visible", timeout: 30_000 });

  const initialRows = await page.locator(".hotel-observability-table tbody tr").count();
  const tableVisible = await page.locator(".hotel-observability-table").isVisible();
  const filtersVisible = await page.locator(".hotel-observability-filter-grid").isVisible();
  const healthVisible = await page.locator(".hotel-observability-health").isVisible();
  const titleVisible = await page.getByRole("heading", { name: /Observabilidad hotelera|Hotel observability/i }).isVisible();
  const healthRequestCount = requests.filter((request) => request.url.startsWith("/api/v1/admin/hotels/health")).length;
  const runsRequestCount = requests.filter((request) => request.url.startsWith("/api/v1/admin/hotels/runs")).length;
  const controlsRequestCount = requests.filter((request) => request.url.startsWith("/api/v1/admin/hotels/provider-controls")).length;
  const controlsVisible = await page.locator(".hotel-observability-controls").isVisible();
  const leasesRequestCount = requests.filter((request) => request.url.startsWith("/api/v1/admin/hotels/sweep-leases")).length;
  const leasesVisible = await page.locator(".hotel-observability-leases").isVisible();
  const outcomesRequestCount = requests.filter((request) => request.url.startsWith("/api/v1/admin/hotels/provider-outcomes")).length;
  const outcomesVisible = await page.locator(".hotel-observability-outcomes").isVisible();
  const runsVisible = await page.locator(".hotel-observability-runs").isVisible();

  const providerSelect = page.locator(".hotel-observability-filter-grid select").nth(1);
  await providerSelect.focus();
  const focusVisible = await providerSelect.evaluate((element) => document.activeElement === element);
  await providerSelect.selectOption("local");
  const filteredResponse = page.waitForResponse(
    (response) => response.url().includes("/admin/hotels/observability") && response.request().method() === "GET",
    { timeout: 30_000 },
  );
  await page.getByRole("button", { name: /Actualizar lectura|Refresh reading/i }).click();
  await filteredResponse;
  await page.waitForTimeout(200);
  const filteredRows = await page.locator(".hotel-observability-table tbody tr").count();
  const providerCells = await page.locator(".hotel-observability-provider").allTextContents();
  const filterWorked = filteredRows > 0 && providerCells.every((provider) => provider.trim() === "local");

  const overflowReport = await page.evaluate(() => {
    const root = document.documentElement;
    const viewportWidth = window.visualViewport?.width || window.innerWidth;
    const candidates = [...document.querySelectorAll("body *")]
      .map((element) => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return {
          tag: element.tagName,
          className: typeof element.className === "string" ? element.className.slice(0, 120) : "",
          left: Math.round(rect.left * 10) / 10,
          right: Math.round(rect.right * 10) / 10,
          width: Math.round(rect.width * 10) / 10,
          display: style.display,
          visibility: style.visibility,
          position: style.position,
          inHiddenTableHead: Boolean(element.closest("thead")),
        };
      })
      .filter((item) => item.width > 0
        && !item.inHiddenTableHead
        && item.display !== "none"
        && item.visibility !== "hidden"
        && item.position !== "absolute"
        && (item.left < -2 || item.right > viewportWidth + 2))
      .slice(0, 12);
    return {
      // The app intentionally uses html zoom: 75% on desktop. Compare visible
      // geometry, not the raw body scrollWidth, which is expressed pre-zoom.
      horizontalOverflow: candidates.length > 0,
      viewportWidth,
      rootScrollWidth: root.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      candidates,
    };
  });
  const horizontalOverflow = overflowReport.horizontalOverflow;
  const screenshotPath = path.join(outputDir, `${scenario.name}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const result = {
    scenario: scenario.name,
    theme: scenario.theme,
    viewport: scenario.viewport,
    titleVisible,
    filtersVisible,
    healthVisible,
    healthRequestCount,
    runsRequestCount,
    controlsRequestCount,
    controlsVisible,
    leasesRequestCount,
    leasesVisible,
    outcomesRequestCount,
    outcomesVisible,
    runsVisible,
    tableVisible,
    initialRows,
    filteredRows,
    filterWorked,
    focusVisible,
    horizontalOverflow,
    overflowReport,
    consoleErrors,
    requests,
    screenshot: path.relative(path.resolve(".."), screenshotPath),
  };
  result.failedAssertions = [];
  if (!titleVisible) result.failedAssertions.push("missing-title");
  if (!filtersVisible) result.failedAssertions.push("missing-filters");
  if (!healthVisible) result.failedAssertions.push("missing-health");
  if (healthRequestCount < 1) result.failedAssertions.push("health-request-missing");
  if (runsRequestCount < 1) result.failedAssertions.push("runs-request-missing");
  if (controlsRequestCount < 1) result.failedAssertions.push("provider-controls-request-missing");
  if (!controlsVisible) result.failedAssertions.push("missing-provider-controls");
  if (leasesRequestCount < 1) result.failedAssertions.push("sweep-leases-request-missing");
  if (!leasesVisible) result.failedAssertions.push("missing-sweep-leases");
  if (outcomesRequestCount < 1) result.failedAssertions.push("provider-outcomes-request-missing");
  if (!outcomesVisible) result.failedAssertions.push("missing-provider-outcomes");
  if (!runsVisible) result.failedAssertions.push("missing-runs");
  if (!tableVisible || initialRows < 1) result.failedAssertions.push("missing-ledger-rows");
  if (!filterWorked) result.failedAssertions.push("provider-filter-failed");
  if (!focusVisible) result.failedAssertions.push("focus-not-established");
  if (horizontalOverflow) result.failedAssertions.push("horizontal-overflow");
  if (consoleErrors.length > 0) result.failedAssertions.push("console-errors");
  result.failedAssertionCount = result.failedAssertions.length;

  await context.close();
  return result;
}

try {
  for (const scenario of scenarios) {
    report.scenarios.push(await runScenario(scenario));
  }
} finally {
  await browser.close();
}

report.failedAssertions = report.scenarios.reduce((sum, scenario) => sum + scenario.failedAssertionCount, 0);
await fs.writeFile(path.join(outputDir, "report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(`Saved admin hotel observability evidence to ${outputDir}`);
if (report.failedAssertions > 0) process.exitCode = 1;
