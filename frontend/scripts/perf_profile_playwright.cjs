const fs = require("fs");
const path = require("path");
const http = require("http");
const { spawn } = require("child_process");
const { chromium } = require("playwright");

const projectRoot = path.resolve(__dirname, "..");
const appDir = path.join(projectRoot, "src", "app");
const defaultOutputDir = path.resolve(projectRoot, "..", "logs_ia");
const baseUrl = process.env.BASE_URL || "http://127.0.0.1:3000";

const PROFILE_CONFIGS = Object.freeze({
  desktop: Object.freeze({
    viewport: null,
    isMobile: false,
    hasTouch: false,
    network: null,
  }),
  mobile: Object.freeze({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    network: null,
  }),
  fast3g: Object.freeze({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    network: Object.freeze({
      offline: false,
      latency: 150,
      downloadThroughput: Math.round((1.6 * 1024 * 1024) / 8),
      uploadThroughput: Math.round((750 * 1024) / 8),
      connectionType: "cellular3g",
    }),
  }),
});

function parseCsv(value, fallback) {
  if (!value || !value.trim()) return [...fallback];
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

const serverTimeoutMs = Number(process.env.SERVER_TIMEOUT_MS || "120000");
const settleMs = Number(process.env.SETTLE_MS || "1500");
const skipServer = process.env.SKIP_SERVER === "1";
const rounds = Number(process.env.ROUNDS || "1");
const loginEmail = process.env.LOGIN_EMAIL || "";
const loginPassword = process.env.LOGIN_PASSWORD || "";

function listRoutes() {
  const routes = new Set();
  function walk(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full);
      } else if (entry.isFile() && entry.name === "page.tsx") {
        const rel = path.relative(appDir, full);
        const parts = rel.split(path.sep);
        const cleaned = parts.filter((p) => !(p.startsWith("(") && p.endsWith(")")));
        cleaned.pop();
        const urlPath = cleaned.length ? `/${cleaned.join("/")}` : "/";
        routes.add(urlPath);
      }
    }
  }
  walk(appDir);
  return Array.from(routes).sort((a, b) => a.localeCompare(b));
}

function selectRoutes(allRoutes, rawRoutes) {
  const requested = parseCsv(rawRoutes, allRoutes);
  const normalized = requested.map((route) => (route.startsWith("/") ? route : `/${route}`));
  const unknown = normalized.filter((route) => !allRoutes.includes(route));
  if (unknown.length > 0) {
    throw new Error(`Unknown performance route(s): ${unknown.join(", ")}`);
  }
  const selected = normalized.filter((route, index) => normalized.indexOf(route) === index);
  if (selected.length === 0) throw new Error("No performance routes selected");
  return selected;
}

function parseProfiles(rawProfiles) {
  const profiles = parseCsv(rawProfiles, ["desktop"]);
  const unknown = profiles.filter((profile) => !Object.hasOwn(PROFILE_CONFIGS, profile));
  if (unknown.length > 0) {
    throw new Error(`Unknown performance profile(s): ${unknown.join(", ")}`);
  }
  return profiles.filter((profile, index) => profiles.indexOf(profile) === index);
}

function resolveOutputDir(environment = process.env) {
  const configured = environment.PERF_OUTPUT_DIR?.trim();
  return configured ? path.resolve(projectRoot, configured) : defaultOutputDir;
}

function shouldWriteJson(environment = process.env) {
  return environment.PERF_JSON === "1" || Boolean(environment.PERF_OUTPUT_DIR?.trim());
}

function httpOk(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      res.resume();
      resolve(true);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(2000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForServer(url, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await httpOk(url)) return true;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

function startDevServer() {
  const child = spawn("cmd.exe", ["/c", "npm.cmd", "run", "dev"], {
    cwd: projectRoot,
    stdio: "pipe",
    windowsHide: true,
  });
  return child;
}

function formatMs(value) {
  if (value == null || Number.isNaN(value)) return "n/a";
  return `${Math.round(value)} ms`;
}

function avg(values) {
  if (!values.length) return null;
  const sum = values.reduce((acc, v) => acc + v, 0);
  return sum / values.length;
}

function p95(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.max(0, Math.ceil(sorted.length * 0.95) - 1);
  return sorted[idx];
}

function safePath(rawUrl) {
  try {
    return new URL(rawUrl).pathname;
  } catch {
    return "";
  }
}

function sanitizeDiagnosticText(value) {
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

function createRequestTracker(page) {
  const requests = new Map();
  const onRequest = (request) => {
    const pathname = safePath(request.url());
    if (!pathname.startsWith("/api/v1/hotels")) return;
    const key = `${request.method()} ${pathname}`;
    requests.set(key, (requests.get(key) || 0) + 1);
  };
  page.on("request", onRequest);
  return {
    snapshot() {
      return Object.fromEntries([...requests.entries()].sort(([a], [b]) => a.localeCompare(b)));
    },
    reset() {
      requests.clear();
    },
    dispose() {
      page.off("request", onRequest);
    },
  };
}

function resolveAuthLoginUrl(environment = process.env, pageBaseUrl = baseUrl) {
  const configuredBase = environment.PERF_AUTH_API_BASE?.trim() || "/api/v1";
  try {
    const apiBase = new URL(configuredBase, pageBaseUrl);
    const apiPath = apiBase.pathname.endsWith("/") ? apiBase.pathname : `${apiBase.pathname}/`;
    return new URL("auth/login", `${apiBase.origin}${apiPath}`).toString();
  } catch {
    return new URL("/api/v1/auth/login", pageBaseUrl).toString();
  }
}

async function requestAuthTokens() {
  const response = await fetch(resolveAuthLoginUrl(), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: loginEmail, password: loginPassword }),
  });
  if (!response.ok) {
    throw new Error(`Login failed with HTTP ${response.status}`);
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error("Login failed: invalid JSON response");
  }
  if (!payload || typeof payload.access_token !== "string" || !payload.access_token) {
    throw new Error("Login failed: access token missing from response");
  }
  return {
    accessToken: payload.access_token,
    refreshToken: typeof payload.refresh_token === "string" ? payload.refresh_token : null,
  };
}

async function createAuthState(browser) {
  if (!loginEmail || !loginPassword) return null;
  const tokens = await requestAuthTokens();
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(({ accessToken, refreshToken }) => {
      window.localStorage.setItem("viru_token", accessToken);
      if (refreshToken) {
        window.localStorage.setItem("viru_refresh_token", refreshToken);
      } else {
        window.localStorage.removeItem("viru_refresh_token");
      }
      window.localStorage.setItem("viru_dashboard_login_required", "true");
    }, tokens);
    return await context.storageState();
  } finally {
    await context.close();
  }
}

async function createProfileContext(browser, profileName, authState) {
  const profile = PROFILE_CONFIGS[profileName];
  const context = await browser.newContext({
    ...(authState ? { storageState: authState } : {}),
    ...(profile.viewport ? { viewport: profile.viewport } : {}),
    isMobile: profile.isMobile,
    hasTouch: profile.hasTouch,
  });
  try {
    const page = await context.newPage();
    if (profile.network) {
      const cdp = await context.newCDPSession(page);
      await cdp.send("Network.enable");
      await cdp.send("Network.emulateNetworkConditions", profile.network);
      await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    }
    return { context, page };
  } catch (error) {
    await context.close();
    throw error;
  }
}

async function collectPageMetrics(page) {
  return page.evaluate(() => {
    const nav = performance.getEntriesByType("navigation")[0];
    const perf = window.__perf || { lcp: 0, cls: 0 };
    return {
      ttfb: nav ? nav.responseStart - nav.startTime : null,
      domContentLoaded: nav ? nav.domContentLoadedEventEnd - nav.startTime : null,
      load: nav ? nav.loadEventEnd - nav.startTime : null,
      tti: performance.now(),
      lcp: perf.lcp,
      cls: perf.cls,
    };
  });
}

async function collectHotelMilestones(page, route, navigationStartedAt, previousNavigationId) {
  const milestones = {
    shellInteractiveAt: null,
    firstResultRenderedAt: null,
  };
  if (route !== "/hoteles") return milestones;

  try {
    await page.waitForFunction(
      ({ previousId }) => {
        const currentId = window.__perfNavigationId;
        return Boolean(
          currentId
          && currentId !== previousId
          && document.querySelector('[data-testid="hotel-city-input"]'),
        );
      },
      { previousId: previousNavigationId },
      { timeout: 10_000 },
    );
    milestones.shellInteractiveAt = Date.now() - navigationStartedAt;
  } catch {
    return milestones;
  }

  if (process.env.PERF_HOTELS_FLOW !== "1") return milestones;

  try {
    const cityInput = page.locator('[data-testid="hotel-city-input"]');
    await cityInput.fill(process.env.PERF_HOTELS_CITY || "Madrid");
    await page.locator('[data-testid="hotel-search-submit"]').click();
    await page.locator(".hotel-result-card").first().waitFor({ state: "visible", timeout: 60_000 });
    milestones.firstResultRenderedAt = Date.now() - navigationStartedAt;
  } catch {
    // Keep the null value: an unavailable/empty/backend-blocked flow is evidence.
  }
  return milestones;
}

async function run() {
  const allRoutes = listRoutes();
  if (!allRoutes.length) {
    throw new Error(`No routes found under ${appDir}`);
  }
  const routes = selectRoutes(allRoutes, process.env.PERF_ROUTES);
  const profiles = parseProfiles(process.env.PERF_PROFILES);

  let serverProcess = null;
  const serverUp = await httpOk(baseUrl);
  if (!serverUp && !skipServer) {
    serverProcess = startDevServer();
    const ok = await waitForServer(baseUrl, serverTimeoutMs);
    if (!ok) {
      if (serverProcess) serverProcess.kill();
      throw new Error(`Dev server did not become ready within ${serverTimeoutMs}ms`);
    }
  }
  if (!serverUp && skipServer) {
    throw new Error(`Server not reachable at ${baseUrl} and SKIP_SERVER=1`);
  }

  let browser = null;
  const results = [];

  try {
    browser = await chromium.launch({ headless: true });
    const authState = await createAuthState(browser);

    for (const profileName of profiles) {
      for (let round = 1; round <= rounds; round += 1) {
        let context = null;
        let requestTracker = null;
        try {
          const profileContext = await createProfileContext(browser, profileName, authState);
          context = profileContext.context;
          const page = profileContext.page;
          const consoleErrors = [];
          requestTracker = createRequestTracker(page);
          page.on("console", (message) => {
            if (message.type() === "error") consoleErrors.push(sanitizeDiagnosticText(message.text()));
          });

          await page.addInitScript(() => {
            window.__perfNavigationId = `${Date.now()}-${Math.random()}`;
            window.__perf = { lcp: 0, cls: 0 };
            try {
              const lcpObserver = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                  const candidate = entry.renderTime || entry.loadTime || entry.startTime;
                  if (candidate > window.__perf.lcp) window.__perf.lcp = candidate;
                }
              });
              lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
            } catch {}
            try {
              let cls = 0;
              const clsObserver = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                  if (!entry.hadRecentInput) cls += entry.value;
                }
                window.__perf.cls = cls;
              });
              clsObserver.observe({ type: "layout-shift", buffered: true });
            } catch {}
          });

          for (const route of routes) {
            const target = `${baseUrl}${route}`;
            requestTracker.reset();
            await page.evaluate(() => {
              if (window.__perf) window.__perf = { lcp: 0, cls: 0 };
            });
            const consoleErrorsAtStart = consoleErrors.length;
            let row = {
              round,
              profile: profileName,
              route,
              finalUrl: "",
              status: "",
              ttfb: null,
              lcp: null,
              cls: null,
              tti: null,
              shellInteractiveAt: null,
              firstResultRenderedAt: null,
              domContentLoaded: null,
              load: null,
              hotelRequests: {},
              consoleErrors: [],
              error: "",
            };
            const navigationStartedAt = Date.now();
            const previousNavigationId = await page.evaluate(() => window.__perfNavigationId || null);
            const milestonesPromise = collectHotelMilestones(page, route, navigationStartedAt, previousNavigationId);
            try {
              const response = await page.goto(target, { waitUntil: "domcontentloaded" });
              row.status = response ? String(response.status()) : "";
              await page.waitForLoadState("networkidle", { timeout: 60000 });
              await page.waitForTimeout(settleMs);
              const metrics = await collectPageMetrics(page);
              const milestones = await milestonesPromise;
              row = {
                ...row,
                ...metrics,
                ...milestones,
                finalUrl: page.url().split("?")[0],
                hotelRequests: requestTracker.snapshot(),
                consoleErrors: consoleErrors.slice(consoleErrorsAtStart),
              };
            } catch (error) {
              await milestonesPromise.catch(() => undefined);
              row.error = sanitizeDiagnosticText(error && error.message ? error.message : error);
              row.hotelRequests = requestTracker.snapshot();
              row.consoleErrors = consoleErrors.slice(consoleErrorsAtStart);
            }
            results.push(row);
          }
        } finally {
          requestTracker?.dispose();
          await context?.close();
        }
      }
    }
  } finally {
    await browser?.close();
    if (serverProcess) serverProcess.kill();
  }

  const now = new Date();
  const stamp = now.toISOString().replace(/[-:]/g, "").replace(/\..+/, "");
  const outputDir = resolveOutputDir();
  fs.mkdirSync(outputDir, { recursive: true });
  const reportBase = path.join(outputDir, `perf_playwright_${stamp}`);
  const markdownPath = `${reportBase}.md`;
  const jsonPath = `${reportBase}.json`;
  const report = {
    generatedAt: now.toISOString(),
    baseUrl: baseUrl.split("?")[0],
    routes,
    profiles,
    rounds,
    settleMs,
    hotelsFlowEnabled: process.env.PERF_HOTELS_FLOW === "1",
    authConfigured: Boolean(loginEmail && loginPassword),
    results,
  };

  const lines = [];
  lines.push("# Playwright Performance Report");
  lines.push("");
  lines.push(`Base URL: ${report.baseUrl}`);
  lines.push(`Routes: ${routes.join(", ")}`);
  lines.push(`Profiles: ${profiles.join(", ")}`);
  lines.push(`Rounds: ${rounds}`);
  lines.push(`Timestamp: ${now.toISOString()}`);
  lines.push("");
  lines.push(`TTI note: approximated as time to network idle + settle (${settleMs}ms), not an INP measurement.`);
  lines.push("");
  lines.push("## Summary (avg / p95)");
  lines.push("");
  lines.push("| Profile | Route | Status | TTFB avg | TTFB p95 | LCP avg | LCP p95 | CLS avg | CLS p95 | TTI avg | TTI p95 | Shell interactive avg | First result avg | Hotel requests | Errors |");
  lines.push("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |");

  for (const profileName of profiles) {
    for (const route of routes) {
      const items = results.filter((row) => row.profile === profileName && row.route === route);
      const metricValues = (key) => items.map((row) => row[key]).filter((value) => value != null && !Number.isNaN(value));
      const errors = items.flatMap((row) => [...row.consoleErrors, row.error].filter(Boolean));
      const requestCount = items.reduce((sum, row) => sum + Object.values(row.hotelRequests).reduce((inner, count) => inner + count, 0), 0);
      const shellValues = metricValues("shellInteractiveAt");
      const firstResultValues = metricValues("firstResultRenderedAt");
      lines.push(`| ${profileName} | ${route} | ${items[0]?.status || ""} | ${formatMs(avg(metricValues("ttfb")))} | ${formatMs(p95(metricValues("ttfb")))} | ${formatMs(avg(metricValues("lcp")))} | ${formatMs(p95(metricValues("lcp")))} | ${metricValues("cls").length ? avg(metricValues("cls")).toFixed(3) : "n/a"} | ${metricValues("cls").length ? p95(metricValues("cls")).toFixed(3) : "n/a"} | ${formatMs(avg(metricValues("tti")))} | ${formatMs(p95(metricValues("tti")))} | ${formatMs(avg(shellValues))} | ${formatMs(avg(firstResultValues))} | ${requestCount} | ${errors.length ? errors.join(" | ") : ""} |`);
    }
  }

  lines.push("");
  lines.push("## Raw result index");
  lines.push("");
  lines.push("The JSON report contains per-round metrics, sanitized hotel API paths, and truncated console/error text.");
  fs.writeFileSync(markdownPath, lines.join("\n"), "utf8");
  if (shouldWriteJson()) fs.writeFileSync(jsonPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");

  console.log(`Saved report to ${markdownPath}`);
  if (shouldWriteJson()) console.log(`Saved JSON report to ${jsonPath}`);
}

if (require.main === module) {
  run().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = {
  PROFILE_CONFIGS,
  listRoutes,
  resolveAuthLoginUrl,
  parseCsv,
  parseProfiles,
  resolveOutputDir,
  selectRoutes,
  shouldWriteJson,
  sanitizeDiagnosticText,
};
