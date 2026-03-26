const fs = require("fs");
const path = require("path");
const http = require("http");
const { spawn } = require("child_process");
const { chromium } = require("playwright");

const projectRoot = path.resolve(__dirname, "..");
const appDir = path.join(projectRoot, "src", "app");
const logsDir = path.resolve(projectRoot, "..", "logs_ia");
const baseUrl = process.env.BASE_URL || "http://127.0.0.1:3000";
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

async function createAuthState(browser) {
  if (!loginEmail || !loginPassword) return null;
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded" });
  await page.fill("input[name='email']", loginEmail);
  await page.fill("input[name='password']", loginPassword);
  await page.click("button[type='submit']");
  await page.waitForFunction(() => window.localStorage.getItem("viru_token"), { timeout: 60000 });
  await page.goto(`${baseUrl}/dashboard`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 60000 });
  const token = await page.evaluate(() => window.localStorage.getItem("viru_token"));
  if (!token) {
    await context.close();
    throw new Error("Login failed: viru_token not found in localStorage");
  }
  const state = await context.storageState();
  await context.close();
  return state;
}

async function run() {
  const routes = listRoutes();
  if (!routes.length) {
    throw new Error(`No routes found under ${appDir}`);
  }

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

  const browser = await chromium.launch({ headless: true });
  const results = [];

  const authState = await createAuthState(browser);

  for (let round = 1; round <= rounds; round += 1) {
    const context = await browser.newContext(authState ? { storageState: authState } : {});
    const page = await context.newPage();

    await page.addInitScript(() => {
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
      let row = {
        round,
        route,
        url: target,
        finalUrl: "",
        status: "",
        ttfb: null,
        lcp: null,
        cls: null,
        tti: null,
        domContentLoaded: null,
        load: null,
        error: "",
      };
      try {
        const response = await page.goto(target, { waitUntil: "domcontentloaded" });
        row.status = response ? String(response.status()) : "";
        await page.waitForLoadState("networkidle", { timeout: 60000 });
        await page.waitForTimeout(settleMs);
        const metrics = await page.evaluate(() => {
          const nav = performance.getEntriesByType("navigation")[0];
          const ttfb = nav ? nav.responseStart - nav.startTime : null;
          const domContentLoaded = nav ? nav.domContentLoadedEventEnd - nav.startTime : null;
          const load = nav ? nav.loadEventEnd - nav.startTime : null;
          const tti = performance.now();
          const perf = window.__perf || { lcp: 0, cls: 0 };
          return { ttfb, domContentLoaded, load, tti, lcp: perf.lcp, cls: perf.cls };
        });
        row = { ...row, ...metrics, finalUrl: page.url() };
      } catch (error) {
        row.error = error && error.message ? error.message : String(error);
      }
      results.push(row);
    }

    await context.close();
  }

  await browser.close();
  if (serverProcess) {
    serverProcess.kill();
  }

  const now = new Date();
  const stamp = now
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\..+/, "");
  if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });
  const logPath = path.join(logsDir, `perf_playwright_${stamp}.md`);

  const lines = [];
  lines.push(`# Playwright Performance Report`);
  lines.push("");
  lines.push(`Base URL: ${baseUrl}`);
  lines.push(`Routes: ${routes.length}`);
  lines.push(`Rounds: ${rounds}`);
  lines.push(`Timestamp: ${now.toISOString()}`);
  lines.push("");
  lines.push(`TTI note: approximated as time to network idle + settle (${settleMs}ms).`);
  lines.push("");
  lines.push("## Summary (avg / p95)");
  lines.push("");
  lines.push("| Route | Status | Final URL | TTFB avg | TTFB p95 | LCP avg | LCP p95 | CLS avg | CLS p95 | TTI avg | TTI p95 | DCL avg | Load avg | Errors |");
  lines.push("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |");

  for (const route of routes) {
    const items = results.filter((r) => r.route === route);
    const ttfbVals = items.map((r) => r.ttfb).filter((v) => v != null && !Number.isNaN(v));
    const lcpVals = items.map((r) => r.lcp).filter((v) => v != null && !Number.isNaN(v));
    const clsVals = items.map((r) => r.cls).filter((v) => v != null && !Number.isNaN(v));
    const ttiVals = items.map((r) => r.tti).filter((v) => v != null && !Number.isNaN(v));
    const dclVals = items.map((r) => r.domContentLoaded).filter((v) => v != null && !Number.isNaN(v));
    const loadVals = items.map((r) => r.load).filter((v) => v != null && !Number.isNaN(v));
    const errors = items.map((r) => r.error).filter(Boolean);
    const sample = items.find((r) => r.finalUrl);

    lines.push(
      `| ${route} | ${sample?.status || ""} | ${sample?.finalUrl || ""} | ${formatMs(avg(ttfbVals))} | ${formatMs(p95(ttfbVals))} | ${formatMs(avg(lcpVals))} | ${formatMs(p95(lcpVals))} | ${clsVals.length ? (avg(clsVals) || 0).toFixed(3) : "n/a"} | ${clsVals.length ? (p95(clsVals) || 0).toFixed(3) : "n/a"} | ${formatMs(avg(ttiVals))} | ${formatMs(p95(ttiVals))} | ${formatMs(avg(dclVals))} | ${formatMs(avg(loadVals))} | ${errors.length ? errors.join(" | ") : ""} |`
    );
  }

  for (let round = 1; round <= rounds; round += 1) {
    lines.push("");
    lines.push(`## Round ${round}`);
    lines.push("");
    lines.push("| Route | Status | Final URL | TTFB | LCP | CLS | TTI | DCL | Load | Error |");
    lines.push("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |");
    for (const r of results.filter((row) => row.round === round)) {
      lines.push(
        `| ${r.route} | ${r.status || ""} | ${r.finalUrl || ""} | ${formatMs(r.ttfb)} | ${formatMs(r.lcp)} | ${r.cls == null ? "n/a" : r.cls.toFixed(3)} | ${formatMs(r.tti)} | ${formatMs(r.domContentLoaded)} | ${formatMs(r.load)} | ${r.error || ""} |`
      );
    }
  }

  fs.writeFileSync(logPath, lines.join("\n"), "utf8");

  console.log(`Saved report to ${logPath}`);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
