import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const evidenceDir = path.join(repoRoot, "docs", "qa", "evidence", "door-to-door-2026-06-20-phase54");

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const API_BASE = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

const scenarios = [
  { name: "desktop-dark", theme: "dark", viewport: { width: 1440, height: 1200 } },
  { name: "desktop-light", theme: "light", viewport: { width: 1440, height: 1200 } },
  { name: "mobile-dark", theme: "dark", viewport: { width: 390, height: 844 } },
  { name: "mobile-light", theme: "light", viewport: { width: 390, height: 844 } },
];
const requestedScenarios = (process.env.QA_D2D_SCENARIOS || "")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);
const activeScenarios = requestedScenarios.length > 0
  ? scenarios.filter((scenario) => requestedScenarios.includes(scenario.name))
  : scenarios;

async function registerAndCreateWatch() {
  const email = `codex-d2d-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  const password = "Test123456!";
  const authResponse = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const authPayload = await authResponse.json();
  if (!authResponse.ok || !authPayload.access_token) {
    throw new Error(`register_failed:${authResponse.status}:${JSON.stringify(authPayload)}`);
  }

  const travelDate = new Date(Date.now() + 1000 * 60 * 60 * 24 * 30).toISOString().slice(0, 10);
  const watchPayload = {
    origin_iata: "AGP",
    destination_iata: "TSF",
    travel_date_local: travelDate,
    target_price: 60,
  };
  const watchResponse = await fetch(`${API_BASE}/watchlist`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authPayload.access_token}`,
    },
    body: JSON.stringify(watchPayload),
  });
  const watch = await watchResponse.json();
  if (!watchResponse.ok || !watch.id) {
    throw new Error(`watch_create_failed:${watchResponse.status}:${JSON.stringify(watch)}`);
  }

  return { token: authPayload.access_token, watch };
}

async function waitForResults(page) {
  await page.locator('button[type="submit"]').click();
  await Promise.race([
    page.locator(".d2d-connected-timeline").waitFor({ state: "visible", timeout: 45000 }),
    page.locator(".d2d-empty-state").waitFor({ state: "visible", timeout: 45000 }),
    page.locator(".d2d-error-state").waitFor({ state: "visible", timeout: 45000 }),
  ]);
  await page.waitForTimeout(800);
}

async function captureScenario(browser, setup, scenario) {
  const context = await browser.newContext({
    viewport: scenario.viewport,
    colorScheme: scenario.theme,
    isMobile: scenario.viewport.width < 500,
    hasTouch: scenario.viewport.width < 500,
  });
  const trackedResponses = [];
  const consoleErrors = [];

  await context.addInitScript(({ token, theme }) => {
    window.localStorage.setItem("viru_token", token);
    window.localStorage.setItem("viru-theme", theme);
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, { token: setup.token, theme: scenario.theme });

  const page = await context.newPage();
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/v1/door-to-door") || url.includes("/api/v1/watchlist")) {
      trackedResponses.push({ url, status: response.status() });
    }
  });

  await page.goto(`${BASE_URL}/puerta-a-puerta?watchId=${encodeURIComponent(setup.watch.id)}`, {
    waitUntil: "networkidle",
    timeout: 60000,
  });

  const watchSelect = page.locator("select").first();
  await watchSelect.waitFor({ state: "visible", timeout: 15000 });
  await page.waitForFunction((watchId) => {
    const select = document.querySelector("select");
    return Boolean(select && select.value === watchId);
  }, setup.watch.id, { timeout: 15000 });

  await waitForResults(page);

  const timeline = page.locator(".d2d-connected-timeline");
  const timelineVisible = await timeline.isVisible().catch(() => false);
  const emptyVisible = await page.locator(".d2d-empty-state").isVisible().catch(() => false);
  const errorVisible = await page.locator(".d2d-error-state").isVisible().catch(() => false);

  if (!timelineVisible && !emptyVisible && !errorVisible) {
    throw new Error(`no_terminal_state:${scenario.name}`);
  }

  if (!timelineVisible) {
    throw new Error(`timeline_not_visible:${scenario.name}`);
  }

  await page.locator("#d2d-results-sentinel").scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    const sentinel = document.getElementById("d2d-results-sentinel");
    const absoluteTop = sentinel
      ? sentinel.getBoundingClientRect().top + window.scrollY
      : 0;
    window.scrollTo({ top: absoluteTop + 260, behavior: "instant" });
  });
  await page.waitForTimeout(800);

  const sticky = page.locator(".d2d-sticky-bar");
  await sticky.waitFor({ state: "visible", timeout: 15000 });

  const metrics = await page.evaluate(() => {
    const stickyBar = document.querySelector(".d2d-sticky-bar");
    const stickyNav = document.querySelector(".d2d-sticky-nav");
    const timeline = document.querySelector(".d2d-connected-timeline");
    const timelineLegs = document.querySelectorAll(".d2d-timeline-leg");
    const routeVisual = document.querySelector(".d2d-route-visual");
    if (!stickyBar || !stickyNav || !timeline) {
      return { ok: false };
    }
    const stickyRect = stickyBar.getBoundingClientRect();
    const navRect = stickyNav.getBoundingClientRect();
    const timelineRect = timeline.getBoundingClientRect();
    const stickyStyle = window.getComputedStyle(stickyBar);
    return {
      ok: true,
      stickyTopVisible: stickyRect.top >= -1 && stickyRect.top <= 8,
      stickyWithinViewport: stickyRect.bottom <= window.innerHeight + 1,
      stickyPosition: stickyStyle.position,
      navHasHorizontalOverflow: stickyNav.scrollWidth > stickyNav.clientWidth + 2,
      navHeight: navRect.height,
      timelineLegCount: timelineLegs.length,
      timelineVisibleHeight: timelineRect.height,
      routeVisualPresent: Boolean(routeVisual),
      pageHeight: document.documentElement.scrollHeight,
      viewport: { width: window.innerWidth, height: window.innerHeight },
    };
  });

  const fullPath = path.join(evidenceDir, `${scenario.name}-full.png`);
  const stickyPath = path.join(evidenceDir, `${scenario.name}-sticky.png`);
  const timelinePath = path.join(evidenceDir, `${scenario.name}-timeline.png`);

  await page.screenshot({ path: fullPath, fullPage: true });
  await sticky.screenshot({ path: stickyPath });
  await page.locator("#d2d-section-timeline").screenshot({ path: timelinePath });

  await context.close();

  return {
    scenario: scenario.name,
    theme: scenario.theme,
    viewport: scenario.viewport,
    metrics,
    trackedResponses,
    consoleErrors,
    files: {
      full: path.relative(repoRoot, fullPath),
      sticky: path.relative(repoRoot, stickyPath),
      timeline: path.relative(repoRoot, timelinePath),
    },
  };
}

await mkdir(evidenceDir, { recursive: true });

const setup = await registerAndCreateWatch();
const browser = await chromium.launch({ headless: true });
const report = {
  generatedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  apiBase: API_BASE,
  watchId: setup.watch.id,
  route: `${setup.watch.origin_iata}-${setup.watch.destination_iata}`,
  scenarios: [],
};

try {
  for (const scenario of activeScenarios) {
    try {
      report.scenarios.push(await captureScenario(browser, setup, scenario));
    } catch (error) {
      report.scenarios.push({
        scenario: scenario.name,
        theme: scenario.theme,
        viewport: scenario.viewport,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }
} finally {
  await browser.close();
}

const reportPath = path.join(evidenceDir, "report.json");
await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");

const failures = report.scenarios.flatMap((scenario) => {
  if ("error" in scenario) {
    return [{ scenario: scenario.scenario, reasons: [scenario.error] }];
  }
  const reasons = [];
  if (!scenario.metrics.ok) reasons.push("missing-dom");
  if (scenario.metrics.ok && scenario.metrics.stickyPosition !== "sticky") reasons.push("sticky-not-sticky");
  if (scenario.metrics.ok && !scenario.metrics.stickyTopVisible) reasons.push("sticky-top-offset");
  if (scenario.metrics.ok && !scenario.metrics.stickyWithinViewport) reasons.push("sticky-overflow");
  if (scenario.metrics.ok && scenario.metrics.timelineLegCount < 2) reasons.push("timeline-too-short");
  if (scenario.consoleErrors.length > 0) reasons.push("console-errors");
  return reasons.length > 0 ? [{ scenario: scenario.scenario, reasons }] : [];
});

console.log(`Door-to-door visual QA report: ${path.relative(repoRoot, reportPath)}`);
if (failures.length > 0) {
  console.error(JSON.stringify(failures));
  process.exitCode = 1;
}
