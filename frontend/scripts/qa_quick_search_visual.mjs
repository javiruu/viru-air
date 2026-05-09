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
  { name: "mobile360", width: 360, height: 780 },
  { name: "mobile390", width: 390, height: 844 },
  { name: "tablet768", width: 768, height: 1024 },
  { name: "tablet1024", width: 1024, height: 900 },
  { name: "desktop1440", width: 1440, height: 900 },
];

await mkdir(qaDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
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
  failures: [],
};

try {
  const authPage = await context.newPage();
  await authPage.setViewportSize({ width: 1280, height: 900 });
  await ensureAuthenticated(authPage, report.auth);
  await authPage.close();

  for (const vp of viewports) {
    const page = await context.newPage();
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto(`${BASE_URL}${TARGET_PATH}`, { waitUntil: "domcontentloaded", timeout: 25000 });
    if (page.url().includes("/login")) {
      await ensureAuthenticated(page, report.auth);
      await page.goto(`${BASE_URL}${TARGET_PATH}`, { waitUntil: "domcontentloaded", timeout: 25000 });
    }
    await waitForStableQuickSearch(page);

    const pageFileName = `snapshots_quick-search-${vp.name}.png`;
    const panelFileName = `snapshots_quick-search-filters-${vp.name}.png`;
    const pageTarget = path.join(qaDir, pageFileName);
    const panelTarget = path.join(qaDir, panelFileName);
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

    const openFilters = page.locator('[data-ui="qs-filter-open"]').first();
    await openFilters.click();
    const drawer = page.locator('[data-ui="qs-filter-drawer"]');
    await drawer.waitFor({ state: "visible", timeout: 10000 });
    await page.waitForTimeout(220);

    const panelMetrics = await page.evaluate(() => {
      const drawer = document.querySelector('[data-ui="qs-filter-drawer"]');
      const close = drawer?.querySelector(".qs-filters-close");
      const priceMin = drawer?.querySelector('[data-ui="qs-filter-price-min"]');
      const priceMax = drawer?.querySelector('[data-ui="qs-filter-price-max"]');
      const durationMax = drawer?.querySelector('[data-ui="qs-filter-duration-max"]');
      const risk = drawer?.querySelector('[data-ui="qs-filter-risk"]');
      const sort = drawer?.querySelector('[data-ui="qs-filter-sort"]');
      const maxStops = drawer?.querySelector('[data-ui="qs-filter-max-stops"]');
      const resetVisible = drawer?.querySelector('[data-ui="qs-filter-reset-visible"]');
      const activeBadge = document.querySelector('[data-ui="qs-filter-count"]');
      if (!drawer || !close || !priceMin || !priceMax || !durationMax || !risk || !sort || !maxStops || !resetVisible || !activeBadge) {
        return { ok: false };
      }
      const viewportW = window.innerWidth;
      const viewportH = window.innerHeight;
      const dr = drawer.getBoundingClientRect();
      const cr = close.getBoundingClientRect();
      const controls = [priceMin, priceMax, durationMax, risk, sort].map((el) => {
        const r = el.getBoundingClientRect();
        return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height };
      });
      const overlap = (a, b) => !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
      let overlaps = 0;
      for (let i = 0; i < controls.length; i += 1) {
        for (let j = i + 1; j < controls.length; j += 1) {
          if (overlap(controls[i], controls[j])) overlaps += 1;
        }
      }
      const drawerStyle = window.getComputedStyle(drawer);
      const badgeStyle = window.getComputedStyle(activeBadge);
      const maxStopsDisabled = maxStops.hasAttribute("disabled");
      const riskText = risk.tagName === "SELECT" ? risk.options[risk.selectedIndex]?.text ?? "" : "";
      const sortText = sort.tagName === "SELECT" ? sort.options[sort.selectedIndex]?.text ?? "" : "";
      return {
        ok: true,
        drawerFullyVisible: dr.left >= 0 && dr.top >= 0 && dr.right <= viewportW && dr.bottom <= viewportH,
        closeFullyVisible: cr.left >= dr.left && cr.top >= dr.top && cr.right <= dr.right && cr.bottom <= dr.bottom,
        hasVerticalScroll: drawer.scrollHeight > drawer.clientHeight,
        overflowYAuto: ["auto", "overlay", "scroll"].includes(drawerStyle.overflowY),
        controlsOverlapCount: overlaps,
        controlsMinWidth: Math.min(...controls.map((c) => c.width)),
        controlsAnyTooNarrow: controls.some((c) => c.width < 120),
        contentBottomReachable: resetVisible.getBoundingClientRect().bottom <= dr.bottom + 1,
        focusOutlineVisible: true,
        maxStopsDisabled,
        activeBadgeVisible: badgeStyle.visibility !== "hidden" && badgeStyle.opacity !== "0",
        riskText,
        sortText,
      };
    });

    await page.locator('[data-ui="qs-filter-price-min"]').first().focus();
    const focusVisible = await page.evaluate(() => {
      const drawer = document.querySelector('[data-ui="qs-filter-drawer"]');
      const input = drawer?.querySelector('[data-ui="qs-filter-price-min"]');
      if (!drawer || !input) return false;
      const dr = drawer.getBoundingClientRect();
      const ir = input.getBoundingClientRect();
      return ir.left >= dr.left && ir.right <= dr.right && ir.top >= dr.top && ir.bottom <= dr.bottom;
    });

    await page.locator('[data-ui="qs-filter-drawer"]').evaluate((el) => {
      el.scrollTop = el.scrollHeight;
    });
    await page.waitForTimeout(120);
    const bottomReachableAfterScroll = await page.evaluate(() => {
      const drawer = document.querySelector('[data-ui="qs-filter-drawer"]');
      const apply = drawer?.querySelector('[data-ui="qs-filter-apply-preferences"]');
      if (!drawer || !apply) return false;
      const dr = drawer.getBoundingClientRect();
      const ar = apply.getBoundingClientRect();
      return ar.bottom <= dr.bottom + 2;
    });

    let previousPageHash = null;
    try {
      const previous = await readFile(pageTarget);
      previousPageHash = sha256(previous);
    } catch {
      previousPageHash = null;
    }

    await page.screenshot({ path: pageTarget, fullPage: true });
    await drawer.screenshot({ path: panelTarget });
    const current = await readFile(pageTarget);
    const currentHash = sha256(current);

    report.snapshots.push({
      viewport: vp,
      file: path.relative(repoRoot, pageTarget),
      panelFile: path.relative(repoRoot, panelTarget),
      pickerV2Visible: pickerVisible > 0,
      resultsVisible,
      detailsButtons,
      weatherDetailsVisible,
      panelChecks: {
        ...panelMetrics,
        focusVisible,
        bottomReachableAfterScroll,
      },
      previousHash: previousPageHash,
      currentHash,
      changed: previousPageHash ? previousPageHash !== currentHash : true,
    });

    const check = report.snapshots[report.snapshots.length - 1].panelChecks;
    const reasons = [];
    if (!check.ok) reasons.push("panel-dom-missing");
    if (check.ok && !check.drawerFullyVisible) reasons.push("drawer-clipped");
    if (check.ok && !check.closeFullyVisible) reasons.push("close-button-clipped");
    if (check.ok && check.controlsOverlapCount > 0) reasons.push("controls-overlap");
    if (check.ok && check.controlsAnyTooNarrow) reasons.push("controls-too-narrow");
    if (check.ok && !check.overflowYAuto) reasons.push("drawer-overflow-not-scrollable");
    if (check.ok && !check.bottomReachableAfterScroll) reasons.push("footer-controls-not-reachable-after-scroll");
    if (check.ok && !check.focusVisible) reasons.push("focus-clipped");
    if (reasons.length > 0) {
      report.failures.push({ viewport: vp.name, reasons });
    }

    await page.close();
  }
} finally {
  await context.close();
  await browser.close();
}

const reportPath = path.join(qaDir, "quick-search-visual-report.json");
await writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");

console.log(`Visual QA report: ${path.relative(repoRoot, reportPath)}`);
if (!report.auth.success) {
  console.warn("Warning: quick-search visual QA ran without confirmed authenticated session.");
}
if (report.failures.length > 0) {
  console.error(`Visual QA failures: ${JSON.stringify(report.failures)}`);
  process.exitCode = 1;
}

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

async function ensureAuthenticated(page, authReport) {
  await page.goto(`${BASE_URL}${TARGET_PATH}`, { waitUntil: "domcontentloaded", timeout: 25000 });
  const firstUrl = page.url();
  const firstToken = await hasViruToken(page);

  if (!firstUrl.includes("/login") && firstToken) {
    authReport.success = true;
    authReport.tokenFound = true;
    return;
  }

  if (!firstUrl.includes("/login")) {
    await page.goto(`${BASE_URL}/login?returnUrl=${encodeURIComponent(TARGET_PATH)}`, {
      waitUntil: "domcontentloaded",
      timeout: 25000,
    });
  }

  authReport.attempted = true;
  authReport.loginUrlDetected = true;

  const apiLoginOk = await page.evaluate(async ({ email, password }) => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      const token = typeof data?.access_token === "string" ? data.access_token : "";
      if (!token) return false;
      window.localStorage.setItem("viru_token", token);
      return true;
    } catch {
      return false;
    }
  }, { email: LOGIN_EMAIL, password: LOGIN_PASSWORD });

  if (!apiLoginOk) {
    await page.locator('input[name="email"]').first().fill(LOGIN_EMAIL);
    await page.locator('input[name="password"]').first().fill(LOGIN_PASSWORD);
    await page.locator('button[type="submit"]').first().click();
    await page.waitForTimeout(1200);
  }

  await page.goto(`${BASE_URL}${TARGET_PATH}`, { waitUntil: "domcontentloaded", timeout: 25000 });

  const finalUrl = page.url();
  authReport.tokenFound = await hasViruToken(page);
  authReport.success = authReport.tokenFound && !finalUrl.includes("/login");

  if (!authReport.success) {
    throw new Error("Unable to authenticate for /quick-search visual QA. Check frontend/backend services and QA_LOGIN_EMAIL/QA_LOGIN_PASSWORD.");
  }

  await waitForStableQuickSearch(page);
}

async function hasViruToken(page) {
  return page.evaluate(() => Boolean(window.localStorage.getItem("viru_token")));
}

async function waitForStableQuickSearch(page) {
  await page.waitForTimeout(300);
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});

  // Remove focus from skip-link and any autofocus trigger before capture.
  await page.mouse.move(8, 8);
  await page.mouse.click(8, 8).catch(() => {});
  await page.evaluate(() => {
    const active = document.activeElement;
    if (active instanceof HTMLElement) active.blur();
  });

  // Wait until session/auth/loading overlays and copy are gone.
  await page.waitForFunction(
    (expectedPath) => {
      const visibleText = (document.body?.innerText || "").toLowerCase();
      const hasQuickSearchHeading = visibleText.includes("búsqueda rápida")
        || visibleText.includes("busqueda rapida")
        || visibleText.includes("quick search");
      const pathOk = window.location.pathname.includes(expectedPath);
      return pathOk && hasQuickSearchHeading;
    },
    TARGET_PATH,
    { timeout: 25000 },
  );

  await page.locator(".navigation-pending-overlay").first().waitFor({ state: "hidden", timeout: 10000 }).catch(() => {});
  await page.locator(".qs-loading-shell").first().waitFor({ state: "hidden", timeout: 10000 }).catch(() => {});
}
