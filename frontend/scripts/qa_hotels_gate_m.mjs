import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = process.env.E2E_BASE_URL || "http://127.0.0.1:3600";
const apiBase = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const email = process.env.LOGIN_EMAIL || "";
const password = process.env.LOGIN_PASSWORD || "";
const outputDir = path.resolve(process.env.GATE_M_OUTPUT_DIR || "../docs/qa/evidence/hotels-h36-gate-m");

if (!email || !password) throw new Error("Gate M requires LOGIN_EMAIL and LOGIN_PASSWORD");

const loginResponse = await fetch(`${apiBase}/auth/login`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ email, password }),
});
if (!loginResponse.ok) throw new Error(`login_http_${loginResponse.status}`);
const tokens = await loginResponse.json();
if (typeof tokens.access_token !== "string" || !tokens.access_token) throw new Error("missing_access_token");

const profiles = [
  { name: "desktop", viewport: { width: 1440, height: 1200 }, isMobile: false, hasTouch: false },
  { name: "tablet", viewport: { width: 1024, height: 900 }, isMobile: false, hasTouch: false },
  { name: "mobile", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
  {
    name: "fast3g-cpu4",
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    network: {
      offline: false,
      latency: 150,
      downloadThroughput: Math.round((1.6 * 1024 * 1024) / 8),
      uploadThroughput: Math.round((750 * 1024) / 8),
      connectionType: "cellular3g",
    },
    cpuRate: 4,
  },
];

await fs.mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [];

function redactPath(rawPath) {
  return rawPath.replace(
    /(^\/api\/v1\/hotels\/)[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?=\/|$)/i,
    "$1[hotel-id]",
  );
}

function sanitize(value) {
  return String(value || "")
    .replace(/https?:\/\/[^\s"'<>]+/gi, (rawUrl) => {
      try {
        const parsed = new URL(rawUrl);
        return `${parsed.origin}${parsed.pathname}`;
      } catch {
        return "[url-redacted]";
      }
    })
    .replace(/(authorization\s*[:=]\s*bearer\s+)[^\s,;]+/gi, "$1[redacted]")
    .replace(/((?:token|api[_-]?key|password|secret)\s*[:=]\s*)[^\s,;]+/gi, "$1[redacted]")
    .replace(/([?&](?:token|api[_-]?key|password|secret|access_token)\s*=\s*)[^&\s]+/gi, "$1[redacted]")
    .replace(/(["'](?:token|api[_-]?key|password|secret|access_token|cookie)["']\s*[:=]\s*["'])[^"']*(["'])/gi, "$1[redacted]$2")
    .replace(/((?:cookie|set-cookie)\s*[:=]\s*)[^\s,;]+/gi, "$1[redacted]")
    .replace(/(["'](?:email|user(?:name)?|phone|address|query|search)["']\s*[:=]\s*["'])[^"']*(["'])/gi, "$1[redacted]$2")
    .replace(/((?:email|username|phone|address|query|search)\s*[:=]\s*)[^\s,;]+/gi, "$1[redacted]")
    .slice(0, 500);
}

async function createAuthState() {
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.evaluate(({ accessToken, refreshToken }) => {
      window.localStorage.setItem("viru_token", accessToken);
      if (refreshToken) window.localStorage.setItem("viru_refresh_token", refreshToken);
      window.localStorage.setItem("viru_dashboard_login_required", "true");
    }, { accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
    return await context.storageState();
  } finally {
    await context.close();
  }
}

async function runProfile(profile, authState) {
  const context = await browser.newContext({
    storageState: authState,
    viewport: profile.viewport,
    isMobile: profile.isMobile,
    hasTouch: profile.hasTouch,
  });
  const hotelRequests = [];
  const requestFailures = [];
  const hotelResponseFailures = [];
  const consoleErrors = [];
  const writeViolations = [];
  const navigationStartedAt = Date.now();
  let phase = "setup";
  let navigationStatus = null;
  let finalUrl = "";

  try {
    await context.addInitScript(() => {
      window.__gateM = { lcp: 0, cls: 0, longTasks: [] };
      try {
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            const candidate = entry.renderTime || entry.loadTime || entry.startTime;
            if (candidate > window.__gateM.lcp) window.__gateM.lcp = candidate;
          }
        }).observe({ type: "largest-contentful-paint", buffered: true });
      } catch {}
      try {
        let cls = 0;
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) cls += entry.value;
          }
          window.__gateM.cls = cls;
        }).observe({ type: "layout-shift", buffered: true });
      } catch {}
      try {
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            window.__gateM.longTasks.push({ duration: entry.duration, startTime: entry.startTime });
          }
        }).observe({ type: "longtask" });
      } catch {}
    });

    const page = await context.newPage();
    const cdp = await context.newCDPSession(page);
    await cdp.send("Network.enable");
    if (profile.network) {
      await cdp.send("Network.emulateNetworkConditions", profile.network);
      await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    }
    if (profile.cpuRate) {
      await cdp.send("Emulation.setCPUThrottlingRate", { rate: profile.cpuRate });
    }

    await page.route("**/api/v1/hotels**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      if (!url.pathname.startsWith("/api/v1/hotels")) return route.continue();
      if (request.method() !== "GET") {
        writeViolations.push({ method: request.method(), path: redactPath(url.pathname) });
        return route.abort("blockedbyclient");
      }
      return route.continue();
    });

    page.on("request", (request) => {
      const url = new URL(request.url());
      if (!url.pathname.startsWith("/api/v1/hotels")) return;
      if (request.method() !== "GET") writeViolations.push({ method: request.method(), path: redactPath(url.pathname) });
    });
    page.on("response", (response) => {
      const url = new URL(response.url());
      if (!url.pathname.startsWith("/api/v1/hotels")) return;
      const record = { method: response.request().method(), path: redactPath(url.pathname), status: response.status() };
      hotelRequests.push(record);
      if (response.status() >= 500) hotelResponseFailures.push(record);
    });
    page.on("requestfailed", (request) => {
      const url = new URL(request.url());
      if (!url.pathname.startsWith("/api/v1/hotels")) return;
      requestFailures.push({ method: request.method(), path: redactPath(url.pathname), error: sanitize(request.failure()?.errorText || "failed") });
    });
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(sanitize(message.text()));
    });

    phase = "navigation";
    const navigationResponse = await page.goto(`${baseUrl}/hoteles`, { waitUntil: "domcontentloaded", timeout: 60_000 });
    navigationStatus = navigationResponse?.status() ?? null;
    finalUrl = page.url().split("?")[0];

    phase = "shell";
    const city = page.locator('[data-testid="hotel-city-input"]');
    const submit = page.locator('[data-testid="hotel-search-submit"]');
    await city.waitFor({ state: "visible", timeout: 60_000 });
    const shellInteractiveAt = Date.now() - navigationStartedAt;
    const authReady = finalUrl.endsWith("/hoteles") && await city.isVisible();

    await city.focus();
    const focusBeforeSearch = await page.evaluate(() => document.activeElement?.getAttribute("data-testid") === "hotel-city-input");
    await city.fill("Madrid");

    phase = "search";
    const searchResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/api/v1/hotels/search" && response.status() === 200;
    }, { timeout: 60_000 });
    await submit.click();
    await searchResponse;

    phase = "results";
    const resultCards = page.locator(".hotel-result-card");
    await resultCards.first().waitFor({ state: "visible", timeout: 60_000 });
    const firstResultRenderedAt = Date.now() - navigationStartedAt;
    await page.waitForTimeout(500);

    phase = "measurements";
    const measurements = await page.evaluate(() => {
      const nav = performance.getEntriesByType("navigation")[0];
      const gate = window.__gateM || { lcp: 0, cls: 0, longTasks: [] };
      const longTasks = Array.isArray(gate.longTasks) ? gate.longTasks : [];
      const root = document.documentElement;
      const body = document.body;
      const zoom = Number.parseFloat(getComputedStyle(root).zoom || "1") || 1;
      const visualWidth = window.visualViewport?.width || window.innerWidth;
      const candidates = [...document.querySelectorAll("body *")]
        .map((element) => {
          const rect = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          return {
            tag: element.tagName,
            className: typeof element.className === "string" ? element.className.slice(0, 120) : "",
            id: element.id || "",
            left: Math.round(rect.left * 10) / 10,
            right: Math.round(rect.right * 10) / 10,
            width: Math.round(rect.width * 10) / 10,
            position: style.position,
            overflowX: style.overflowX,
          };
        })
        .filter((item) => item.width > 0 && (item.left < -2 || item.right > visualWidth + 2))
        .sort((a, b) => Math.max(b.right - visualWidth, 0) - Math.max(a.right - visualWidth, 0))
        .slice(0, 12);
      const visualOverflow = candidates.length > 0;
      return {
        ttfb: nav ? nav.responseStart - nav.startTime : null,
        domContentLoaded: nav ? nav.domContentLoadedEventEnd - nav.startTime : null,
        load: nav ? nav.loadEventEnd - nav.startTime : null,
        lcp: gate.lcp,
        cls: gate.cls,
        longTaskCount: longTasks.length,
        longTaskTotalMs: longTasks.reduce((sum, entry) => sum + entry.duration, 0),
        longestTaskMs: longTasks.reduce((max, entry) => Math.max(max, entry.duration), 0),
        horizontalOverflow: visualOverflow,
        overflowCandidates: candidates,
        layout: {
          zoom,
          innerWidth: window.innerWidth,
          visualViewportWidth: visualWidth,
          clientWidth: root.clientWidth,
          scrollWidth: root.scrollWidth,
          bodyClientWidth: body.clientWidth,
          bodyScrollWidth: body.scrollWidth,
          normalizedScrollWidth: root.scrollWidth * zoom,
        },
        viewport: { width: window.innerWidth, height: window.innerHeight },
      };
    });

    const result = {
      profile: profile.name,
      status: navigationStatus,
      finalUrl,
      authReady,
      shellInteractiveAt,
      firstResultRenderedAt,
      resultCount: await resultCards.count(),
      focusBeforeSearch,
      ...measurements,
      hotelRequests,
      requestFailures,
      hotelResponseFailures,
      writeViolations,
      consoleErrors,
      privacy: { credentials: false, tokens: false, queryStrings: false, trace: false },
    };
    result.failedAssertions = [];
    if (!result.authReady) result.failedAssertions.push("auth-not-ready");
    if (result.status !== 200) result.failedAssertions.push("navigation-not-200");
    if (result.resultCount === 0) result.failedAssertions.push("missing-first-result");
    if (!result.focusBeforeSearch) result.failedAssertions.push("search-focus-not-established");
    if (result.horizontalOverflow) result.failedAssertions.push("visual-horizontal-overflow");
    if (result.writeViolations.length > 0) result.failedAssertions.push("read-only-violation");
    if (result.requestFailures.length > 0) result.failedAssertions.push("hotel-request-failure");
    if (result.hotelResponseFailures.length > 0) result.failedAssertions.push("hotel-response-5xx");
    if (result.consoleErrors.length > 0) result.failedAssertions.push("unexpected-console-error");
    result.failedAssertionCount = result.failedAssertions.length;
    return result;
  } catch (error) {
    const failedAssertions = [`${phase}-failed`];
    if (navigationStatus !== 200) failedAssertions.push("navigation-not-200");
    return {
      profile: profile.name,
      status: navigationStatus,
      finalUrl,
      authReady: false,
      phase,
      errorCode: `${phase}-failed`,
      error: sanitize(error?.message || error),
      hotelRequests,
      requestFailures,
      hotelResponseFailures,
      writeViolations,
      consoleErrors,
      privacy: { credentials: false, tokens: false, queryStrings: false, trace: false },
      failedAssertions: [...new Set(failedAssertions)],
      failedAssertionCount: new Set(failedAssertions).size,
    };
  } finally {
    await context.close();
  }
}

try {
  const authState = await createAuthState();
  for (const profile of profiles) results.push(await runProfile(profile, authState));
} finally {
  await browser.close();
}

const report = {
  generatedAt: new Date().toISOString(),
  baseUrl: baseUrl.split("?")[0],
  profiles: profiles.map(({ name, viewport, network, cpuRate }) => ({ name, viewport, network: Boolean(network), cpuRate: cpuRate || 1 })),
  results,
  failedGateMAssertions: results.reduce((sum, result) => sum + (result.failedAssertionCount || 0), 0),
  traceEnabled: false,
  privacy: { credentials: false, tokens: false, queryStrings: false, authenticatedTrace: false, violations: [] },
};
const serializedReport = JSON.stringify(report);
const privacyViolations = [];
if (/[?&](?:token|api[_-]?key|password|secret|access_token)=/i.test(serializedReport)) privacyViolations.push("query-or-secret-marker");
if (/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/.test(serializedReport)) privacyViolations.push("jwt-marker");
if (/authorization\s*[:=]\s*(?!\[redacted\])[^\s,;]+|bearer\s+(?!\[redacted\])[^\s,;]+/i.test(serializedReport)) privacyViolations.push("authorization-marker");
report.privacy.violations = privacyViolations;
if (privacyViolations.length > 0) throw new Error(`gate_m_privacy_validation_failed:${privacyViolations.join(",")}`);
await fs.writeFile(path.join(outputDir, "gate-m.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(`Saved Gate M evidence to ${outputDir}`);
if (report.failedGateMAssertions > 0) process.exitCode = 1;
