import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseUrl = "http://127.0.0.1:3000";
const outDir = path.resolve("docs/qa");

async function ensureOutDir() {
  await fs.mkdir(outDir, { recursive: true });
}

async function run() {
  await ensureOutDir();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded" });
  await page.fill('input[type="email"]', "user@viru.local");
  await page.fill('input[type="password"]', "ViruUser123");
  await page.click('button[type="submit"]');

  const toast = page.locator(".notification-center .notification-card").first();
  await toast.waitFor({ state: "visible", timeout: 15000 });

  await page.screenshot({ path: path.join(outDir, "notifications-login-desktop-full.png"), fullPage: true });
  await toast.screenshot({ path: path.join(outDir, "notifications-login-desktop-component.png") });

  await browser.close();

  console.log(path.join(outDir, "notifications-login-desktop-full.png"));
  console.log(path.join(outDir, "notifications-login-desktop-component.png"));
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
