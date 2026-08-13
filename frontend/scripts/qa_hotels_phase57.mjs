import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium, request } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const configuredEvidenceDir = process.env.H40_OUTPUT_DIR?.trim();
const evidenceDir = path.resolve(
  repoRoot,
  configuredEvidenceDir || path.join("docs", "qa", "evidence", "hotels-h40-rerun-current"),
);

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const API_BASE = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

const scenarios = [
  { name: "desktop-dark", theme: "dark", viewport: { width: 1440, height: 1200 } },
  { name: "desktop-light", theme: "light", viewport: { width: 1440, height: 1200 } },
  { name: "mobile-dark", theme: "dark", viewport: { width: 390, height: 844 } },
  { name: "mobile-light", theme: "light", viewport: { width: 390, height: 844 } },
];

function sanitizeDiagnosticText(value) {
  return String(value || "")
    .replace(/https?:\/\/[^\s"'<>]+/gi, (rawUrl) => {
      try {
        const parsed = new URL(rawUrl);
        return `${parsed.origin}${parsed.pathname}${parsed.search ? "?present" : ""}`;
      } catch {
        return "[url-redacted]";
      }
    })
    .replace(/(authorization\s*[:=]\s*bearer\s+)[^\s,;]+/gi, "$1[redacted]")
    .replace(/((?:token|api[_-]?key|password|secret)\s*[:=]\s*)[^\s,;]+/gi, "$1[redacted]")
    .replace(/([?&](?:token|api[_-]?key|password|secret|access_token)\s*=\s*)[^&\s]+/gi, "$1[redacted]")
    .slice(0, 500);
}

function redactApiUrl(rawUrl) {
  const url = new URL(rawUrl);
  const redactedPath = url.pathname.replace(
    /\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?=\/|$)/gi,
    "/[id]",
  );
  return `${url.origin}${redactedPath}${url.search ? "?present" : ""}`;
}

async function registerUser() {
  const api = await request.newContext();
  const email = `codex-hotels-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  const password = "Test123456!";
  const response = await api.post(`${API_BASE}/auth/register`, {
    data: { email, password },
  });
  const body = await response.json();
  await api.dispose();
  if (!response.ok() || !body.access_token) {
    throw new Error(`register_failed:${response.status()}:${JSON.stringify(body)}`);
  }
  return body.access_token;
}

async function clickAndWait(page, buttonName, responsePart) {
  const responsePromise = page.waitForResponse(
    (response) => {
      const url = new URL(response.url());
      return url.pathname === responsePart
        && response.request().method() === "GET"
        && response.status() === 200;
    },
    { timeout: 45000 },
  );
  await Promise.all([
    responsePromise,
    clickButtonInView(page, page.getByRole("button", { name: buttonName })),
  ]);
}

async function clickButtonInView(page, locator) {
  await locator.waitFor({ state: "visible", timeout: 15000 });

  for (let attempt = 0; attempt < 4; attempt += 1) {
    const scrollDelta = await locator.evaluate((element) => {
      element.scrollIntoView({ block: "center", inline: "nearest" });
      const rect = element.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      const mobileNav = document.querySelector(".mobile-bottom-nav");
      const mobileNavRect = mobileNav?.getBoundingClientRect();
      const headerRect = document.querySelector(".shell-header")?.getBoundingClientRect();
      const safeTop = Math.max(8, (headerRect?.bottom ?? 0) + 8);
      const safeBottom = Math.min(
        viewportHeight - 8,
        (mobileNavRect?.top ?? viewportHeight) - 8,
      );

      if (rect.top < safeTop) return rect.top - safeTop;
      if (rect.bottom > safeBottom) return rect.bottom - safeBottom;
      return 0;
    });

    if (scrollDelta !== 0) {
      await page.evaluate((delta) => window.scrollBy({ top: delta, behavior: "instant" }), scrollDelta);
    }
    await page.waitForTimeout(250);

    const point = await locator.evaluate((element) => {
      const rect = element.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const hit = document.elementFromPoint(x, y);
      return hit && (hit === element || element.contains(hit))
        ? { x: rect.width / 2, y: rect.height / 2 }
        : null;
    });

    if (point) {
      await locator.click({ position: point });
      return;
    }

    await page.waitForTimeout(150);
  }

  throw new Error("click_target_occluded_after_safe_scroll");
}

async function setupScenario(browser, scenario) {
  const token = await registerUser();
  const context = await browser.newContext({
    viewport: scenario.viewport,
    colorScheme: scenario.theme,
    locale: "es-ES",
    isMobile: scenario.viewport.width < 500,
    hasTouch: scenario.viewport.width < 500,
  });

  await context.addInitScript(({ token: initToken, theme }) => {
    window.localStorage.setItem("viru_token", initToken);
    window.localStorage.setItem("viru-theme", theme);
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, { token, theme: scenario.theme });

  const page = await context.newPage();
  const trackedResponses = [];
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(sanitizeDiagnosticText(message.text()));
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/v1/hotels")) {
      trackedResponses.push({ url: redactApiUrl(url), status: response.status() });
    }
  });

  await page.goto(`${BASE_URL}/hoteles`, { waitUntil: "networkidle", timeout: 60000 });
  await page.addStyleTag({
    content: `
      .notification-center,
      .notification-card {
        pointer-events: none !important;
      }
    `,
  });
  return { context, page, trackedResponses, consoleErrors };
}

async function exerciseHotelsFlow(page) {
  // Keep the runner aligned with the stable contract shared by the other hotel gates.
  // The visible label is localized and can be translated/structured differently;
  // data-testid is intentionally locale-independent for browser evidence.
  const cityInput = page.locator('[data-testid="hotel-city-input"]');
  await cityInput.fill("Madrid");
  await clickAndWait(page, "Buscar hoteles", "/api/v1/hotels/search");

  const resultCards = page.locator(".hotel-result-card");
  await resultCards.first().waitFor({ state: "visible", timeout: 30000 });
  const resultCount = await resultCards.count();
  if (resultCount === 0) throw new Error("no_results");

  const firstResult = resultCards.first();
  await clickButtonInView(page, firstResult.locator(".hotel-result-main"));

  const trackButton = firstResult.getByRole("button", { name: /Seguir precio|Siguiendo precio|Track price|Following price|Trackear precio|Ya en seguimiento/ });
  await trackButton.waitFor({ state: "visible", timeout: 15000 });
  await clickButtonInView(page, trackButton);
  await page.locator(".hotel-tracked-offer-item").first().waitFor({ state: "visible", timeout: 30000 });

  const watchButton = firstResult.getByRole("button", { name: /Guardar hotel|Guardado|Save hotel|Saved|Añadir a seguimiento|En seguimiento/ });
  await watchButton.waitFor({ state: "visible", timeout: 15000 });
  await clickButtonInView(page, watchButton);
  await page.locator(".hotel-watchlist-item").first().waitFor({ state: "visible", timeout: 30000 });

  const alertThreshold = page.locator('.hotel-alerts-form input[inputmode="decimal"]').first();
  await alertThreshold.waitFor({ state: "visible", timeout: 15000 });
  await alertThreshold.fill("120");
  const createAlert = page.getByRole("button", { name: "Crear alerta" });
  await createAlert.waitFor({ state: "visible", timeout: 15000 });
  const alertCreated = page.waitForResponse(
    (response) => response.url().includes("/api/v1/hotels/alert-rules") && response.request().method() === "POST" && response.status() < 500,
    { timeout: 30000 },
  );
  await clickButtonInView(page, createAlert);
  await alertCreated;
  await page.locator(".hotel-alert-rule-item").first().waitFor({ state: "visible", timeout: 30000 });

  const createCompSet = page.getByRole("button", { name: "Crear comparativa" });
  await createCompSet.waitFor({ state: "visible", timeout: 15000 });
  const compSetCreated = page.waitForResponse(
    (response) => response.url().includes("/api/v1/hotels/comp-sets") && response.request().method() === "POST" && response.status() < 500,
    { timeout: 30000 },
  );
  await clickButtonInView(page, createCompSet);
  await compSetCreated;
  await page.locator(".hotel-comp-set-summary").waitFor({ state: "visible", timeout: 30000 });

  const nearbyAdd = page.locator(".hotel-nearby-actions .btn-ghost").first();
  if (await nearbyAdd.count()) {
    await clickButtonInView(page, nearbyAdd);
    await page.locator(".hotel-comp-set-member-item").first().waitFor({ state: "visible", timeout: 30000 }).catch(() => undefined);
  }

  await page.waitForTimeout(1200);
}

async function captureScenario(browser, scenario) {
  const { context, page, trackedResponses, consoleErrors } = await setupScenario(browser, scenario);
  await exerciseHotelsFlow(page);

  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.waitForTimeout(300);

  const metrics = await page.evaluate(() => {
    const resultCards = document.querySelectorAll(".hotel-result-card");
    const trackedOffers = document.querySelectorAll(".hotel-tracked-offer-item");
    const watchlistItems = document.querySelectorAll(".hotel-watchlist-item");
    const alertRules = document.querySelectorAll(".hotel-alert-rule-item");
    const compSetSummary = document.querySelector(".hotel-comp-set-summary");
    const pageRoot = document.documentElement;
    return {
      resultCount: resultCards.length,
      trackedOfferCount: trackedOffers.length,
      watchlistCount: watchlistItems.length,
      alertRuleCount: alertRules.length,
      compSetVisible: Boolean(compSetSummary),
      hasHorizontalOverflow: pageRoot.scrollWidth > window.innerWidth + 1,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      theme: document.documentElement.dataset.theme || "",
    };
  });

  const fullPath = path.join(evidenceDir, `${scenario.name}-full.png`);
  const sidebarPath = path.join(evidenceDir, `${scenario.name}-sidebar.png`);
  const resultsPath = path.join(evidenceDir, `${scenario.name}-results.png`);

  await page.screenshot({ path: fullPath, fullPage: true });
  await page.locator(".hoteles-side-column").screenshot({ path: sidebarPath });
  await page.locator(".hotel-results-panel").screenshot({ path: resultsPath });

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
      sidebar: path.relative(repoRoot, sidebarPath),
      results: path.relative(repoRoot, resultsPath),
    },
  };
}

await mkdir(evidenceDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const report = {
  generatedAt: new Date().toISOString(),
  runner: "qa_hotels_phase57",
  browserEngine: "chromium",
  browserVersion: browser.version(),
  crossBrowser: { status: "incomplete", browsers: ["chromium"] },
  baseUrl: redactApiUrl(BASE_URL),
  apiBase: redactApiUrl(API_BASE),
  locale: "es-ES",
  evidenceDir: path.relative(repoRoot, evidenceDir),
  humanReview: "pending",
  privacy: { status: "pending", violations: [] },
  scenarios: [],
};

try {
  for (const scenario of scenarios) {
    try {
      report.scenarios.push(await captureScenario(browser, scenario));
    } catch (error) {
      report.scenarios.push({
        scenario: scenario.name,
        theme: scenario.theme,
        viewport: scenario.viewport,
        error: sanitizeDiagnosticText(error instanceof Error ? error.message : String(error)),
      });
    }
  }
} finally {
  await browser.close();
}

const reportPath = path.join(evidenceDir, "report.json");
const serializedReport = JSON.stringify(report);
const privacyViolations = [];
if (/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/.test(serializedReport)) privacyViolations.push("jwt-marker");
if (/(?:authorization|bearer|password|secret|api[_-]?key|access_token)\s*[:=]/i.test(serializedReport)) privacyViolations.push("credential-marker");
if (/[?&](?:token|password|secret|access_token|api[_-]?key)=/i.test(serializedReport)) privacyViolations.push("sensitive-query-marker");
if (/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i.test(serializedReport)) privacyViolations.push("email-marker");
if (privacyViolations.length > 0) {
  report.privacy = { status: "failed", violations: privacyViolations };
  throw new Error(`phase57_privacy_validation_failed:${privacyViolations.join(",")}`);
}
report.privacy = { status: "passed", violations: [] };
await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");

const failures = report.scenarios.flatMap((scenario) => {
  if ("error" in scenario) return [{ scenario: scenario.scenario, reasons: [scenario.error] }];
  const reasons = [];
  if (scenario.metrics.resultCount < 1) reasons.push("missing-results");
  if (scenario.metrics.trackedOfferCount < 1) reasons.push("missing-tracked-offer");
  if (scenario.metrics.watchlistCount < 1) reasons.push("missing-watchlist");
  if (scenario.metrics.alertRuleCount < 1) reasons.push("missing-alert-rule");
  if (!scenario.metrics.compSetVisible) reasons.push("missing-comp-set");
  if (scenario.metrics.hasHorizontalOverflow) reasons.push("horizontal-overflow");
  if (scenario.consoleErrors.length > 0) reasons.push("console-errors");
  return reasons.length > 0 ? [{ scenario: scenario.scenario, reasons }] : [];
});

console.log(`Hotels visual QA report: ${path.relative(repoRoot, reportPath)}`);
if (failures.length > 0) {
  console.error(JSON.stringify(failures));
  process.exitCode = 1;
}
