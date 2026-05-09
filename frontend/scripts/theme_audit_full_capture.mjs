import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:3000';
const LOGIN_EMAIL = process.env.QA_LOGIN_EMAIL || 'user@viru.local';
const LOGIN_PASSWORD = process.env.QA_LOGIN_PASSWORD || 'ViruUser123';
const outDir = path.resolve('..', 'logs', 'theme-audit-2026-05-09-final');
await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 980 } });
const page = await context.newPage();

async function setTheme(theme) {
  await page.evaluate((t) => {
    localStorage.setItem('viru_theme', t);
    document.documentElement.setAttribute('data-theme', t);
  }, theme);
  await page.waitForTimeout(220);
}

async function ensureLogin() {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  const ok = await page.evaluate(async ({ email, password }) => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      if (!data?.access_token) return false;
      localStorage.setItem('viru_token', data.access_token);
      return true;
    } catch { return false; }
  }, { email: LOGIN_EMAIL, password: LOGIN_PASSWORD });
  if (!ok) {
    const email = page.locator('input[name="email"]').first();
    const pass = page.locator('input[name="password"]').first();
    if (await email.count()) await email.fill(LOGIN_EMAIL);
    if (await pass.count()) await pass.fill(LOGIN_PASSWORD);
    const submit = page.locator('button[type="submit"]').first();
    if (await submit.count()) await submit.click();
    await page.waitForTimeout(1400);
  }
}

async function openRoute(routeCandidates) {
  for (const route of routeCandidates) {
    await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(700);
    if (!page.url().includes('/login') && !page.url().includes('/404')) return route;
  }
  return routeCandidates[0];
}

async function cap(name, full=true){ await page.screenshot({ path: path.join(outDir,name), fullPage: full }); }

await ensureLogin();

// Dashboard dark full + account menu + footer
await openRoute(['/dashboard']);
await setTheme('dark');
await cap('dashboard-dark-full.png');
const trigger = page.locator('.account-trigger').first();
if (await trigger.count()) { await trigger.click(); await page.waitForTimeout(300); }
await cap('dashboard-dark-account-menu.png');
await page.evaluate(()=>window.scrollTo(0, document.body.scrollHeight));
await page.waitForTimeout(500);
await cap('dashboard-dark-footer.png');

// Quick search dark empty date
await openRoute(['/quick-search']);
await setTheme('dark');
await page.evaluate(() => {
  const input = document.querySelector('input[type="date"]');
  if (input) {
    input.value = '';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }
});
await page.waitForTimeout(350);
await cap('quick-search-dark-empty-date.png');

// Quick search dark with results attempt
const submitCandidates = [
  '[data-ui="qs-submit"]',
  'button:has-text("Buscar")',
  'button:has-text("Search")',
  '.btn-search'
];
for (const sel of submitCandidates) {
  const el = page.locator(sel).first();
  if (await el.count()) {
    const enabled = await el.isEnabled().catch(() => false);
    if (enabled) {
      await el.click();
      break;
    }
  }
}
await page.waitForTimeout(2200);
await cap('quick-search-dark-results-attempt.png');

// Recommendations dark
await openRoute(['/recomendaciones', '/recommendations']);
await setTheme('dark');
await page.waitForTimeout(700);
await cap('recommendations-dark-full.png');
await page.evaluate(()=>window.scrollTo(0, document.body.scrollHeight));
await page.waitForTimeout(500);
await cap('recommendations-dark-footer.png');

// Alerts dark
await openRoute(['/alerts']);
await setTheme('dark');
await page.waitForTimeout(700);
await cap('alerts-dark-full.png');

// Light controls
await openRoute(['/quick-search']);
await setTheme('light');
await page.waitForTimeout(700);
await cap('quick-search-light-full.png');

await openRoute(['/dashboard']);
await setTheme('light');
await page.waitForTimeout(700);
await cap('dashboard-light-full.png');

await context.close();
await browser.close();
console.log(outDir);
