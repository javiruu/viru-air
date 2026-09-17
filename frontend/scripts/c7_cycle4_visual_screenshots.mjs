import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const suffix = process.argv[2] || "before";
const baseUrl = "http://127.0.0.1:3101";
const outDir = path.resolve(`../docs/qa/screenshots/c7.4/${suffix}`);
fs.mkdirSync(outDir, { recursive: true });

async function bootstrapContext(context) {
  await context.addInitScript(() => {
    window.localStorage.setItem(
      "viru_token",
      "tok_12345678901234567890123456789012345678901234567890",
    );
  });
}

async function mockCommon(page) {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "admin-1",
        email: "admin@viru.app",
        locale: "es",
        is_admin: true,
      }),
    });
  });

  await page.route("**/api/v1/admin/users", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "u1",
          email: "ana@viru.app",
          is_admin: false,
          is_verified: true,
          locale: "es",
          timezone: "Europe/Madrid",
          created_at: "2026-03-01T10:00:00Z",
        },
        {
          id: "u2",
          email: "ops@viru.app",
          is_admin: true,
          is_verified: true,
          locale: "en",
          timezone: "Europe/Berlin",
          created_at: "2026-03-02T11:00:00Z",
        },
      ]),
    });
  });

  await page.route("**/api/v1/watchlist", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "w1",
          origin_iata: "MAD",
          destination_iata: "DUB",
          travel_date_local: "2026-04-21",
          status: "active",
        },
      ]),
    });
  });

  await page.route("**/api/v1/admin/users/*/watchlist", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "w2",
          origin_iata: "BCN",
          destination_iata: "LIS",
          travel_date_local: "2026-04-30",
          status: "active",
        },
      ]),
    });
  });

  await page.route("**/api/v1/suggestions", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok" }),
      });
      return;
    }
    await route.fallback();
  });
}

async function shot(page, url, file) {
  await page.goto(`${baseUrl}${url}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(outDir, file), fullPage: true });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 2200 } });
  await bootstrapContext(context);
  const page = await context.newPage();
  await mockCommon(page);

  await shot(page, "/admin", "01-admin.png");
  await shot(page, "/suggestions", "02-suggestions.png");
  await shot(page, "/policies", "03-policies.png");

  await browser.close();
  console.log(`Saved screenshots in ${outDir}`);
})();
