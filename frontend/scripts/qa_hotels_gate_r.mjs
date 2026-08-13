import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = process.env.E2E_BASE_URL || "http://127.0.0.1:3500";
const apiBase = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const email = process.env.LOGIN_EMAIL || "";
const password = process.env.LOGIN_PASSWORD || "";
const outputDir = path.resolve(process.env.GATE_R_OUTPUT_DIR || "../docs/qa/evidence/hotels-h36-gate-r");
const traceEnabled = process.env.GATE_R_TRACE === "1";
if (traceEnabled && process.env.GATE_R_TRACE_ACK !== "I_UNDERSTAND_AUTH_TRACE") {
  throw new Error("Authenticated traces require GATE_R_TRACE_ACK=I_UNDERSTAND_AUTH_TRACE");
}

if (!email || !password) throw new Error("Gate R requires LOGIN_EMAIL and LOGIN_PASSWORD");

const loginResponse = await fetch(`${apiBase}/auth/login`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ email, password }),
});
if (!loginResponse.ok) throw new Error(`login_http_${loginResponse.status}`);
const tokens = await loginResponse.json();
if (typeof tokens.access_token !== "string" || !tokens.access_token) throw new Error("missing_access_token");

await fs.mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1200 } });
if (traceEnabled) {
  await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
}
await context.addInitScript(({ accessToken, refreshToken }) => {
  window.localStorage.setItem("viru_token", accessToken);
  if (refreshToken) window.localStorage.setItem("viru_refresh_token", refreshToken);
  window.localStorage.setItem("viru_dashboard_login_required", "true");
}, { accessToken: tokens.access_token, refreshToken: tokens.refresh_token });

const page = await context.newPage();
const hotelResponses = [];
const requestFailures = [];
const consoleErrors = [];
const scenarios = [];
const trackedPaths = new Set();
const readOnlyViolations = [];
const expectedConsoleSlots = new Map();

function redactHotelPath(rawPath) {
  return rawPath.replace(
    /(^\/api\/v1\/hotels\/)[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?=\/|$)/i,
    "$1[hotel-id]",
  );
}

function sanitizeDiagnosticText(value) {
  return String(value || "")
    .replace(/https?:\/\/[^\\s"'<>]+/gi, (rawUrl) => {
      try {
        const parsed = new URL(rawUrl);
        return `${parsed.origin}${parsed.pathname}`;
      } catch {
        return "[url-redacted]";
      }
    })
    .replace(/(authorization\\s*[:=]\\s*bearer\\s+)[^\\s,;]+/gi, "$1[redacted]")
    .replace(/((?:token|api[_-]?key|password|secret)\\s*[:=]\\s*)[^\\s,;]+/gi, "$1[redacted]")
    .replace(/([?&](?:token|api[_-]?key|password|secret|access_token)\\s*=\\s*)[^&\\s]+/gi, "$1[redacted]")
    .replace(/([\"'](?:token|api[_-]?key|password|secret|access_token|cookie)[\"']\\s*[:=]\\s*[\"'])[^\"']*([\"'])/gi, "$1[redacted]$2")
    .replace(/([\"'](?:email|user(?:name)?|phone|address|query|search)[\"']\\s*[:=]\\s*[\"'])[^\"']*([\"'])/gi, "$1[redacted]$2")
    .slice(0, 300);
}

page.on("request", (request) => {
  const url = new URL(request.url());
  if (!url.pathname.startsWith("/api/v1/hotels")) return;
  if (request.method() !== "GET") {
    readOnlyViolations.push({ method: request.method(), path: redactHotelPath(url.pathname), status: "request-started" });
  }
});
page.on("response", (response) => {
  const url = new URL(response.url());
  if (!url.pathname.startsWith("/api/v1/hotels")) return;
  const method = response.request().method();
  const path = redactHotelPath(url.pathname);
  const record = { method, path, status: response.status() };
  hotelResponses.push(record);
  trackedPaths.add(`${record.method} ${record.path}`);
  if (method !== "GET") readOnlyViolations.push(record);
  if (
    response.status() === 503
    && (path === "/api/v1/hotels/search" || path === "/api/v1/hotels/[hotel-id]/parity")
  ) {
    expectedConsoleSlots.set(path, (expectedConsoleSlots.get(path) || 0) + 1);
  }
});
page.on("requestfailed", (request) => {
  const url = new URL(request.url());
  if (!url.pathname.startsWith("/api/v1/hotels")) return;
  const path = redactHotelPath(url.pathname);
  requestFailures.push({ method: request.method(), path, error: request.failure()?.errorText || "failed" });
});
page.on("console", (message) => {
  if (message.type() !== "error") return;
  const text = message.text().slice(0, 300);
  if (text.includes("status of 503 (Service Unavailable)")) {
    const expectedPath = [...expectedConsoleSlots.entries()].find(([, count]) => count > 0)?.[0];
    if (expectedPath) {
      expectedConsoleSlots.set(expectedPath, expectedConsoleSlots.get(expectedPath) - 1);
      return;
    }
  }
  consoleErrors.push(sanitizeDiagnosticText(text));
});

function safeUrl() {
  const url = new URL(page.url());
  return `${url.pathname}${url.search ? "?present" : ""}`;
}
function addScenario(name, data = {}) {
  scenarios.push({ name, ...data });
}
async function waitForResults() {
  await page.locator(".hotel-result-card").first().waitFor({ state: "visible", timeout: 30_000 });
  return page.locator(".hotel-result-card").count();
}
async function searchResponse(status) {
  return page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/api/v1/hotels/search" && response.status() === status;
  }, { timeout: 30_000 });
}
async function clickSearch() {
  await page.locator('[data-testid="hotel-search-submit"]').click();
}

try {
  await page.goto(`${baseUrl}/hoteles`, { waitUntil: "networkidle", timeout: 60_000 });
  await page.locator('[data-testid="hotel-city-input"]').waitFor({ state: "visible", timeout: 30_000 });
  const city = page.locator('[data-testid="hotel-city-input"]');
  const submit = page.locator('[data-testid="hotel-search-submit"]');

  await city.fill("Madrid");
  await Promise.all([searchResponse(200), clickSearch()]);
  const resultCount = await waitForResults();
  addScenario("city-search", { status: "success", resultCount, url: safeUrl() });

  await page.locator(".hotel-result-card").first().locator(".hotel-result-main").click();
  await page.waitForTimeout(500);
  addScenario("selection", {
    selectedUrl: safeUrl(),
    detailPanelPresent: await page.locator("#hotel-detail-panel").count() === 1,
  });

  await page.locator(".hotel-search-mode-tab").nth(1).click();
  const areaInput = page.locator(".hotel-area-autocomplete input");
  await areaInput.fill("Madrid");
  await page.locator(".hotel-area-suggestion-item").first().waitFor({ state: "visible", timeout: 30_000 });
  const suggestionPresent = await page.locator(".hotel-area-suggestion-item").count() > 0;
  await page.locator(".hotel-area-suggestion-item").first().click();
  const resolved = await page.locator(".hotel-area-resolved-badge").count() > 0;
  let areaStatus = "success";
  let areaCount = 0;
  try {
    const areaResponse = page.waitForResponse(
      (response) => new URL(response.url()).pathname === "/api/v1/hotels/area-search",
      { timeout: 30_000 },
    );
    await clickSearch();
    const response = await areaResponse;
    if (response.status() !== 200) throw new Error(`area_search_http_${response.status()}`);
    areaCount = await page.locator(".hotel-area-result-card").count();
  } catch (error) {
    areaStatus = error instanceof Error ? error.message : "response_or_empty_timeout";
  }
  addScenario("area-autocomplete-search", { status: areaStatus, suggestionPresent, resolved, areaCount });

  await page.locator(".hotel-search-mode-tab").first().click();
  await city.fill("ControlledError");
  await page.route("**/api/v1/hotels/search**", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ detail: "controlled_gate_r_error" }),
  }));
  await clickSearch();
  const mainAlert = page.locator('#main-content > .notice[role="alert"]');
  await mainAlert.waitFor({ state: "visible", timeout: 30_000 });
  addScenario("controlled-error", {
    alertPresent: true,
    queryRetained: (await city.inputValue()) === "ControlledError",
    alertText: (await mainAlert.innerText()).slice(0, 180),
  });
  await page.unroute("**/api/v1/hotels/search**");

  await city.fill("ControlledEmpty");
  await page.route("**/api/v1/hotels/search**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: "[]",
  }));
  await clickSearch();
  await page.locator(".hotel-empty-state").waitFor({ state: "visible", timeout: 30_000 });
  addScenario("controlled-empty", {
    emptyPresent: true,
    alertCount: await page.locator('#main-content > .notice[role="alert"]').count(),
    queryRetained: (await city.inputValue()) === "ControlledEmpty",
  });
  await page.unroute("**/api/v1/hotels/search**");

  await city.fill("Madrid");
  await Promise.all([searchResponse(200), clickSearch()]);
  await waitForResults();
  await page.route("**/api/v1/hotels/*/parity", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ detail: "controlled_parity_error" }),
  }));
  const resultCards = page.locator(".hotel-result-card");
  const resultCardCount = await resultCards.count();
  if (resultCardCount < 2) throw new Error("gate_r_requires_two_results_for_parity_scenario");
  const parityTarget = resultCards.nth(1);
  await parityTarget.locator(".hotel-result-main").click();
  await page.locator(".hotel-parity-signal .status-pill.error").waitFor({ state: "visible", timeout: 30_000 });
  addScenario("controlled-parity-error", { errorBadgePresent: true, selectedNewResult: true });
  await page.unroute("**/api/v1/hotels/*/parity");

  let delayed = true;
  await page.route("**/api/v1/hotels/search**", async (route) => {
    if (!delayed) return route.continue();
    await new Promise((resolve) => setTimeout(resolve, 3_000));
    try { await route.continue(); } catch { /* navigation cancelled the request */ }
  });
  await city.fill("CancelMe");
  const failuresBefore = requestFailures.length;
  await clickSearch();
  await page.waitForTimeout(200);
  await page.goto(`${baseUrl}/dashboard`, { waitUntil: "domcontentloaded", timeout: 30_000 });
  delayed = false;
  await page.unroute("**/api/v1/hotels/search**");
  const cancelledSearchRequests = requestFailures.filter(
    (failure) => failure.path === "/api/v1/hotels/search" && failure.error === "net::ERR_ABORTED",
  ).length;
  addScenario("navigation-cancel", {
    leftHotels: new URL(page.url()).pathname === "/dashboard",
    hotelRequestFailures: requestFailures.length - failuresBefore,
    cancellationValidated: cancelledSearchRequests > 0,
    alertPresentAfterNavigation: await page.locator('#main-content > .notice[role="alert"]').count() > 0,
  });
} finally {
  if (traceEnabled) {
    await context.tracing.stop({ path: path.join(outputDir, "gate-r.trace.zip") });
  }
  const unexpectedConsoleErrors = [...consoleErrors];
  const scenario = (name) => scenarios.find((item) => item.name === name);
  const gateAssertions = [
    readOnlyViolations.length === 0,
    traceEnabled === false,
    scenario("city-search")?.status === "success" && scenario("city-search")?.resultCount > 0,
    scenario("selection")?.detailPanelPresent === true,
    scenario("area-autocomplete-search")?.status === "success",
    scenario("controlled-error")?.alertPresent === true && scenario("controlled-error")?.queryRetained === true,
    scenario("controlled-empty")?.emptyPresent === true && scenario("controlled-empty")?.alertCount === 0,
    scenario("controlled-parity-error")?.errorBadgePresent === true,
    scenario("navigation-cancel")?.leftHotels === true
      && scenario("navigation-cancel")?.cancellationValidated === true
      && scenario("navigation-cancel")?.alertPresentAfterNavigation === false,
  ];
  await fs.writeFile(path.join(outputDir, "gate-r.json"), `${JSON.stringify({
    generatedAt: new Date().toISOString(),
    baseUrl,
    profile: "desktop",
    scenarios,
    hotelResponses,
    trackedPaths: [...trackedPaths].sort(),
    requestFailures,
    consoleErrors,
    unexpectedConsoleErrors,
    readOnlyViolations,
    failedGateRAssertions: gateAssertions.filter((passed) => !passed).length,
    traceEnabled,
    privacy: { email: false, password: false, token: false, queryStrings: false },
  }, null, 2)}\n`, "utf8");
  await browser.close();
  if (unexpectedConsoleErrors.length > 0 || gateAssertions.some((passed) => !passed)) process.exitCode = 1;
}

console.log(`Saved Gate R evidence to ${outputDir}`);
