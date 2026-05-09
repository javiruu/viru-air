import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const LOGIN_EMAIL = process.env.QA_LOGIN_EMAIL || "user@viru.local";
const LOGIN_PASSWORD = process.env.QA_LOGIN_PASSWORD || "ViruUser123";
const outDir = path.resolve("..", "logs", "theme-audit-2026-05-09");
await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 980 } });
const page = await context.newPage();

async function setTheme(theme) {
  await page.evaluate((t) => {
    localStorage.setItem("viru_theme", t);
    document.documentElement.setAttribute("data-theme", t);
  }, theme);
  await page.waitForTimeout(200);
}

async function login() {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded" });
  const ok = await page.evaluate(async ({ email, password }) => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      if (!data?.access_token) return false;
      localStorage.setItem("viru_token", data.access_token);
      return true;
    } catch {
      return false;
    }
  }, { email: LOGIN_EMAIL, password: LOGIN_PASSWORD });

  if (!ok) {
    await page.getByRole("textbox", { name: /email/i }).fill(LOGIN_EMAIL);
    await page.getByLabel(/contraseña|password/i).fill(LOGIN_PASSWORD);
    await page.getByRole("button", { name: /entrar|login|iniciar/i }).click();
    await page.waitForTimeout(1200);
  }
}

await login();

await page.goto(`${BASE_URL}/quick-search`, { waitUntil: "domcontentloaded" });
await setTheme("light");
await page.waitForTimeout(800);
await page.screenshot({ path: path.join(outDir, "quick-search-light.png"), fullPage: true });

await setTheme("dark");
await page.waitForTimeout(600);
await page.screenshot({ path: path.join(outDir, "quick-search-dark.png"), fullPage: true });

await page.goto(`${BASE_URL}/dashboard`, { waitUntil: "domcontentloaded" });
await setTheme("dark");
await page.waitForTimeout(800);
await page.screenshot({ path: path.join(outDir, "dashboard-dark.png"), fullPage: true });

const accountTrigger = page.locator(".account-trigger").first();
if (await accountTrigger.count()) {
  await accountTrigger.click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(outDir, "account-menu-dark.png"), fullPage: true });
}

await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
await page.waitForTimeout(600);
await page.screenshot({ path: path.join(outDir, "footer-dark.png"), fullPage: true });

await context.close();
await browser.close();
console.log(outDir);
