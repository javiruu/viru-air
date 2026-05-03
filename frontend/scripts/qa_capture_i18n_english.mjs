import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const qaDir = path.join(repoRoot, "docs", "qa");

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const USER_EMAIL = process.env.QA_LOGIN_EMAIL || "user@viru.local";
const USER_PASSWORD = process.env.QA_LOGIN_PASSWORD || "ViruUser123";
const ADMIN_EMAIL = process.env.QA_ADMIN_EMAIL || "admin@viru.local";
const ADMIN_PASSWORD = process.env.QA_ADMIN_PASSWORD || "ViruAdmin123";

const publicRoutes = ["/", "/login", "/register", "/forgot-password", "/policies", "/ayuda"];
const privateRoutes = [
  "/dashboard",
  "/watchlist",
  "/alerts",
  "/quick-search",
  "/recomendaciones",
  "/suggestions",
  "/history",
  "/preferencias",
  "/preferencias/apariencia",
  "/preferencias/busqueda",
  "/preferencias/region",
  "/cuenta/perfil",
  "/cuenta/seguridad",
  "/soporte/ayuda",
  "/soporte/contacto",
  "/soporte/feedback",
  "/soporte/about-us",
  "/soporte/novedades/price-windows",
];
const adminRoutes = ["/admin", "/admin/product-health"];

const spanishNeedles = [
  "iniciar sesion",
  "sesion cerrada",
  "cerrar sesion",
  "contrasena",
  "correo electronico",
  "busqueda",
  "seguimiento",
  "politicas",
  "sugerencias",
  "recomendaciones",
  "guardar",
  "volver",
  "ayuda",
  "apariencia",
  "sesion caducada",
  "acceso requerido",
];

const report = {
  generatedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  locale: "en",
  summary: {
    pagesScanned: 0,
    pagesWithPotentialSpanish: 0,
  },
  pages: [],
};

await mkdir(qaDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
try {
  const publicContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await publicContext.addInitScript(() => {
    window.localStorage.setItem("viru_locale", "en");
  });
  const publicPage = await publicContext.newPage();
  for (const route of publicRoutes) {
    await scanRoute(publicPage, route, "public");
  }
  await publicContext.close();

  const privateContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const privatePage = await privateContext.newPage();
  await login(privatePage, USER_EMAIL, USER_PASSWORD);
  await setEnglishPreference(privatePage);
  for (const route of privateRoutes) {
    await scanRoute(privatePage, route, "private");
  }
  await privateContext.close();

  const adminContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const adminPage = await adminContext.newPage();
  await login(adminPage, ADMIN_EMAIL, ADMIN_PASSWORD);
  await setEnglishPreference(adminPage);
  for (const route of adminRoutes) {
    await scanRoute(adminPage, route, "admin");
  }
  await adminContext.close();
} finally {
  await browser.close();
}

report.summary.pagesScanned = report.pages.length;
report.summary.pagesWithPotentialSpanish = report.pages.filter((item) => item.matches.length > 0).length;

const reportPath = path.join(qaDir, "i18n-english-audit-report.json");
await writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");

console.log(`I18N English audit report: ${path.relative(repoRoot, reportPath)}`);
console.log(`Scanned pages: ${report.summary.pagesScanned}`);
console.log(`Pages with potential Spanish: ${report.summary.pagesWithPotentialSpanish}`);

async function login(page, email, password) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle", timeout: 25000 });
  await page.evaluate(() => {
    window.localStorage.setItem("viru_locale", "en");
  });
  await page.locator('input[name="email"]').first().fill(email);
  await page.locator('input[name="password"]').first().fill(password);
  await page.locator('button[type="submit"]').first().click();
  try {
    await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 15000 });
  } catch {
    // Keep flow deterministic with explicit target navigation below.
  }
  await page.goto(`${BASE_URL}/dashboard`, { waitUntil: "networkidle", timeout: 25000 });
}

async function setEnglishPreference(page) {
  await page.goto(`${BASE_URL}/preferencias/region`, { waitUntil: "networkidle", timeout: 25000 });
  const languageSelect = page.locator('select[name="language"]');
  const languageSelectCount = await languageSelect.count();
  if (languageSelectCount > 0) {
    await languageSelect.first().selectOption("en");
    const saveButton = page.locator('button[type="submit"]');
    if ((await saveButton.count()) > 0) {
      await saveButton.first().click();
      await page.waitForTimeout(700);
    }
  }
  await page.evaluate(() => {
    window.localStorage.setItem("viru_locale", "en");
  });
}

async function scanRoute(page, route, scope) {
  await page.goto(`${BASE_URL}${route}`, { waitUntil: "networkidle", timeout: 25000 });
  await page.waitForTimeout(1800);

  const bodyText = await page.evaluate(() => document.body?.innerText || "");
  const normalized = normalize(bodyText);
  const matches = spanishNeedles.filter((needle) => normalized.includes(needle));
  const screenshot = `i18n-en-${scope}-${slugify(route)}.png`;
  const screenshotPath = path.join(qaDir, screenshot);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  report.pages.push({
    scope,
    route,
    finalUrl: page.url(),
    matches,
    screenshot: path.relative(repoRoot, screenshotPath),
  });
}

function normalize(value) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function slugify(route) {
  if (route === "/") return "home";
  return route.replaceAll("/", "-").replace(/^-+/, "");
}
