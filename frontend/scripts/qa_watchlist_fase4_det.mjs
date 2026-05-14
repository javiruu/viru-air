import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const screenshotsDir = path.join(repoRoot, "docs", "qa", "screenshots");

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const API_BASE = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
const LOGIN_EMAIL = process.env.QA_LOGIN_EMAIL || "user@viru.local";
const LOGIN_PASSWORD = process.env.QA_LOGIN_PASSWORD || "ViruUser123";
const TARGET_PATH = "/watchlist";

await mkdir(screenshotsDir, { recursive: true });

const token = await loginAndGetToken();
await ensureMinimumWatches(token);

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

const report = {
  generatedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  targetPath: TARGET_PATH,
  auth: { success: false },
  interactions: {},
  consoleErrors: [],
  request500: [],
  screenshots: {},
};

page.on("console", (msg) => { if (msg.type() === "error") report.consoleErrors.push(msg.text()); });
page.on("response", (res) => { if (res.status() >= 500) report.request500.push({ url: res.url(), status: res.status() }); });

try {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded", timeout: 25000 });
  await page.evaluate((access) => localStorage.setItem("viru_token", access), token);
  report.auth.success = true;

  await gotoWatchlist(page);
  await page.waitForSelector(".watch-row", { timeout: 20000 });

  const rows = page.locator(".watch-row");
  const rowCount = await rows.count();
  if (rowCount < 2) throw new Error(`Need >=2 rows. Found ${rowCount}`);

  await rows.nth(0).click();
  await page.waitForTimeout(600);
  const route1 = (await page.locator(".watch-detail-route strong").innerText()).trim();

  await rows.nth(1).click();
  await page.waitForTimeout(600);
  const route2 = (await page.locator(".watch-detail-route strong").innerText()).trim();

  report.interactions.routeSwitch = { firstRoute: route1, secondRoute: route2, changed: route1 !== route2 };

  const detailActions = page.locator(".watch-detail-actions button");
  if (await detailActions.count() >= 1) {
    await detailActions.nth(0).click();
    await page.waitForTimeout(700);
    report.interactions.refreshClicked = true;
  }
  if (await detailActions.count() >= 2) {
    const beforeLabel = (await detailActions.nth(1).innerText()).trim();
    await detailActions.nth(1).click();
    await page.waitForTimeout(900);
    const afterLabel = (await page.locator(".watch-detail-actions button").nth(1).innerText()).trim();
    report.interactions.pauseResumeFromDet = { beforeLabel, afterLabel, changed: beforeLabel !== afterLabel };
  }

  const bulkChecks = page.locator(".watch-bulk-checkbox");
  await bulkChecks.nth(0).check();
  await bulkChecks.nth(1).check();
  await page.waitForTimeout(500);
  report.interactions.comparePanelVisibleAfterSelection = await page.locator(".compare-tabs").first().isVisible().catch(() => false);

  const historyLine = await page.locator(".history-route-line-text").first().innerText().catch(() => "");
  report.interactions.historyResponds = historyLine.trim().length > 0;

  const desktopPath = path.join(screenshotsDir, "watchlist-fase4-det-desktop-1440x900.png");
  await page.screenshot({ path: desktopPath, fullPage: true });

  const mobile = await context.newPage();
  await mobile.setViewportSize({ width: 375, height: 812 });
  mobile.on("console", (msg) => { if (msg.type() === "error") report.consoleErrors.push(`[mobile] ${msg.text()}`); });
  mobile.on("response", (res) => { if (res.status() >= 500) report.request500.push({ url: res.url(), status: res.status(), viewport: "mobile" }); });
  await mobile.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded", timeout: 25000 });
  await mobile.evaluate((access) => localStorage.setItem("viru_token", access), token);
  await gotoWatchlist(mobile);
  await mobile.waitForTimeout(900);
  const mobilePath = path.join(screenshotsDir, "watchlist-fase4-det-mobile-375x812.png");
  await mobile.screenshot({ path: mobilePath, fullPage: true });
  await mobile.close();

  report.screenshots.desktop = path.relative(repoRoot, desktopPath);
  report.screenshots.mobile = path.relative(repoRoot, mobilePath);

  const reportPath = path.join(screenshotsDir, "watchlist-fase4-det-verification.json");
  await writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");

  if (!report.interactions.routeSwitch.changed) throw new Error("DET did not change with route selection.");
  const blockingConsoleErrors = report.consoleErrors.filter((entry) => !entry.includes("Failed to fetch RSC payload") && !entry.includes("status of 409"));
  if (blockingConsoleErrors.length) throw new Error(`Console errors: ${blockingConsoleErrors.length}`);
  if (report.request500.length) throw new Error(`HTTP 500 detected: ${report.request500.length}`);

  console.log(`Saved: ${path.relative(repoRoot, desktopPath)}`);
  console.log(`Saved: ${path.relative(repoRoot, mobilePath)}`);
  console.log(`Saved: ${path.relative(repoRoot, reportPath)}`);
} finally {
  await context.close();
  await browser.close();
}

async function gotoWatchlist(page) {
  await page.goto(`${BASE_URL}${TARGET_PATH}`, { waitUntil: "domcontentloaded", timeout: 25000 });
  if (page.url().includes("/login")) {
    await page.waitForTimeout(400);
    await page.goto(`${BASE_URL}${TARGET_PATH}`, { waitUntil: "domcontentloaded", timeout: 25000 });
  }
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
}

async function loginAndGetToken() {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: LOGIN_EMAIL, password: LOGIN_PASSWORD }),
  });
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
  const data = await res.json();
  if (!data?.access_token) throw new Error("No access_token on login response");
  return data.access_token;
}

async function ensureMinimumWatches(token) {
  const listRes = await fetch(`${API_BASE}/api/v1/watchlist`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!listRes.ok) throw new Error(`Watchlist load failed: ${listRes.status}`);
  const list = await listRes.json();
  if (Array.isArray(list) && list.length >= 2) return;

  const seeds = [
    { origin_iata: "MAD", destination_iata: "KUN", travel_date_local: "2026-09-15", target_price: 95 },
    { origin_iata: "ALC", destination_iata: "TSF", travel_date_local: "2026-09-20", target_price: 70 },
  ];

  for (const seed of seeds) {
    await fetch(`${API_BASE}/api/v1/watchlist`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(seed),
    });
  }
}
