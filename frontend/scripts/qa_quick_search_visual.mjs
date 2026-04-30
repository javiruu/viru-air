import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const qaDir = path.join(repoRoot, "docs", "qa");

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const LOGIN_EMAIL = process.env.QA_LOGIN_EMAIL || "user@viru.local";
const LOGIN_PASSWORD = process.env.QA_LOGIN_PASSWORD || "ViruUser123";
const TARGET_PATH = "/quick-search";

const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet768", width: 768, height: 1024 },
  { name: "mobile375", width: 375, height: 812 },
  { name: "mobile320", width: 320, height: 712 },
];

await mkdir(qaDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const report = {
  generatedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  targetPath: TARGET_PATH,
  auth: {
    attempted: false,
    success: false,
    loginUrlDetected: false,
    tokenFound: false,
    usingDefaultSeedCreds: !process.env.QA_LOGIN_EMAIL && !process.env.QA_LOGIN_PASSWORD,
  },
  snapshots: [],
};

try {
  const authPage = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await ensureAuthenticated(authPage, report.auth);
  await authPage.close();

  for (const vp of viewports) {
    const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
    await page.goto(`${BASE_URL}${TARGET_PATH}`, { waitUntil: "networkidle", timeout: 20000 });

    const fileName = `snapshots_quick-search-${vp.name}.png`;
    const target = path.join(qaDir, fileName);
    const pickerVisible = await page.locator('[data-ui="qs-date-picker-v2"]').first().count();
    const detailsButtons = await page.locator("button.qs-result-details-link").count();
    let weatherDetailsVisible = 0;
    let resultsVisible = 0;

    if (detailsButtons > 0) {
      await page.locator("button.qs-result-details-link").first().click();
      await page.waitForTimeout(700);
      weatherDetailsVisible = await page.locator(".qs-result-weather").count();
      resultsVisible = await page.locator(".qs-result-row").count();
    }

    let previousHash = null;
    try {
      const previous = await readFile(target);
      previousHash = sha256(previous);
    } catch {
      previousHash = null;
    }

    await page.screenshot({ path: target, fullPage: true });
    const current = await readFile(target);
    const currentHash = sha256(current);

    report.snapshots.push({
      viewport: vp,
      file: path.relative(repoRoot, target),
      pickerV2Visible: pickerVisible > 0,
      resultsVisible,
      detailsButtons,
      weatherDetailsVisible,
      previousHash,
      currentHash,
      changed: previousHash ? previousHash !== currentHash : true,
    });

    await page.close();
  }
} finally {
  await browser.close();
}

const reportPath = path.join(qaDir, "quick-search-visual-report.json");
await writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");

console.log(`Visual QA report: ${path.relative(repoRoot, reportPath)}`);
if (!report.auth.success) {
  console.warn("Warning: quick-search visual QA ran without confirmed authenticated session.");
}

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

async function ensureAuthenticated(page, authReport) {
  await page.goto(`${BASE_URL}${TARGET_PATH}`, { waitUntil: "networkidle", timeout: 25000 });
  const firstUrl = page.url();

  if (!firstUrl.includes("/login")) {
    authReport.success = true;
    authReport.tokenFound = await hasViruToken(page);
    return;
  }

  authReport.attempted = true;
  authReport.loginUrlDetected = true;

  await page.locator('input[name="email"]').first().fill(LOGIN_EMAIL);
  await page.locator('input[name="password"]').first().fill(LOGIN_PASSWORD);
  await page.locator('button[type="submit"]').first().click();

  await page.waitForTimeout(900);

  try {
    await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 12000 });
  } catch {
    // Best-effort: fall through to explicit target retry below.
  }

  await page.goto(`${BASE_URL}${TARGET_PATH}`, { waitUntil: "networkidle", timeout: 25000 });

  const finalUrl = page.url();
  authReport.tokenFound = await hasViruToken(page);
  authReport.success = authReport.tokenFound && !finalUrl.includes("/login");

  if (!authReport.success) {
    throw new Error("Unable to authenticate for /quick-search visual QA. Check frontend/backend services and QA_LOGIN_EMAIL/QA_LOGIN_PASSWORD.");
  }
}

async function hasViruToken(page) {
  return page.evaluate(() => Boolean(window.localStorage.getItem("viru_token")));
}
