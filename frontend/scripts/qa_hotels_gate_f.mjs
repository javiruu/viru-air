import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = process.env.E2E_BASE_URL || "http://127.0.0.1:3603";
const apiBase = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const email = process.env.LOGIN_EMAIL || "";
const password = process.env.LOGIN_PASSWORD || "";
const outputDir = path.resolve(process.env.GATE_F_OUTPUT_DIR || "../docs/qa/evidence/hotels-h36-gate-f");
const consentKey = "viru_hotels_rum_consent";

if (!email || !password) throw new Error("Gate F requires LOGIN_EMAIL and LOGIN_PASSWORD");

const loginResponse = await fetch(`${apiBase}/auth/login`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ email, password }),
});
if (!loginResponse.ok) throw new Error(`login_http_${loginResponse.status}`);
const tokens = await loginResponse.json();
if (typeof tokens.access_token !== "string" || !tokens.access_token) throw new Error("missing_access_token");

await fs.mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const allowedKeys = new Set([
  "schema_version",
  "surface",
  "metric",
  "value_bucket",
  "rating",
  "navigation_type",
  "device_class",
]);
const allowedMetrics = new Set(["lcp", "inp", "cls", "ttfb"]);
const allowedRatings = new Set(["good", "needs_improvement", "poor"]);
const allowedDevices = new Set(["mobile", "tablet", "desktop"]);
const allowedNavigationTypes = new Set(["navigate", "reload", "back_forward", "prerender"]);
const timingBuckets = new Set(["0-250ms", "250-500ms", "500-1000ms", "1000-2000ms", "2000-4000ms", "4000-8000ms", "8000+ms", "unknown"]);
const clsBuckets = new Set(["0-0.1", "0.1-0.25", "0.25-0.5", "0.5+", "unknown"]);

function sanitize(value) {
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
    .slice(0, 300);
}

async function authState() {
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.evaluate(({ accessToken, refreshToken }) => {
      localStorage.setItem("viru_token", accessToken);
      if (refreshToken) localStorage.setItem("viru_refresh_token", refreshToken);
      localStorage.setItem("viru_dashboard_login_required", "true");
    }, { accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
    return await context.storageState();
  } finally {
    await context.close();
  }
}

function validatePayload(payload) {
  const metadata = payload?.metadata;
  const failures = [];
  if (payload?.event_name !== "hotel_rum_vitals") failures.push("wrong-event-name");
  if (!metadata || typeof metadata !== "object") return [...failures, "missing-metadata"];
  if (Object.keys(metadata).some((key) => !allowedKeys.has(key)) || Object.keys(metadata).length !== allowedKeys.size) failures.push("metadata-keys-not-allowlisted");
  if (metadata.schema_version !== 1) failures.push("schema-version");
  if (metadata.surface !== "hoteles") failures.push("surface");
  if (!allowedMetrics.has(metadata.metric)) failures.push("metric");
  if (!allowedRatings.has(metadata.rating)) failures.push("rating");
  if (!allowedDevices.has(metadata.device_class)) failures.push("device-class");
  if (!allowedNavigationTypes.has(metadata.navigation_type)) failures.push("navigation-type");
  const buckets = metadata.metric === "cls" ? clsBuckets : timingBuckets;
  if (!buckets.has(metadata.value_bucket)) failures.push("value-bucket");
  return failures;
}

async function runScenario(name, consent, storage) {
  const context = await browser.newContext({ storageState: storage, viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });    const events = [];
    const rumEvents = [];
    const consoleErrors = [];

  try {
    await context.addInitScript(({ consentValue }) => {
      if (consentValue) localStorage.setItem("viru_hotels_rum_consent", consentValue);
    }, { consentValue: consent ? "granted" : null });
    const page = await context.newPage();
    await page.route("**/api/v1/ux/events", async (route) => {
      const request = route.request();
      let payload = null;
      try {
        payload = JSON.parse(request.postData() || "null");
      } catch {
        payload = { parse_error: true };
      }
      const eventName = typeof payload?.event_name === "string" ? payload.event_name : "unknown";
      events.push({ method: request.method(), eventName });
      if (eventName === "hotel_rum_vitals") rumEvents.push(payload);
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok" }) });
    });
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(sanitize(message.text()));
    });
    const response = await page.goto(`${baseUrl}/hoteles`, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.locator('[data-testid="hotel-city-input"]').waitFor({ state: "visible", timeout: 60_000 });
    await page.waitForTimeout(800);
    await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded", timeout: 60_000 }).catch(() => undefined);
    await page.waitForTimeout(800);
    const payloadFailures = rumEvents.flatMap((payload) => validatePayload(payload));
    return {
      scenario: name,
      consent,
      navigationStatus: response?.status() ?? null,
      eventsSeen: events.length,
      rumEventsSeen: rumEvents.length,
      eventNames: events.map((event) => event.eventName),
      payloadFailures: [...new Set(payloadFailures)],
      methods: events.map((event) => event.method),
      consoleErrors,
      privacy: { credentials: false, tokens: false, queryStrings: false, rawPayloads: false },
      failedAssertions: [
        ...(response?.status() === 200 ? [] : ["navigation-not-200"]),
        ...(consent ? (rumEvents.length > 0 ? [] : ["consent-event-missing"]) : (rumEvents.length === 0 ? [] : ["consent-bypass"])),
        ...(payloadFailures.length === 0 ? [] : ["payload-not-allowlisted"]),
        ...(consoleErrors.length === 0 ? [] : ["console-error"]),
      ],
    };
  } catch (error) {
    return {
      scenario: name,
      consent,
      eventsSeen: events.length,
      rumEventsSeen: rumEvents.length,
      eventNames: events.map((event) => event.eventName),
      payloadFailures: [],
      methods: events.map((event) => event.method),
      error: sanitize(error?.message || error),
      consoleErrors,
      privacy: { credentials: false, tokens: false, queryStrings: false, rawPayloads: false },
      failedAssertions: [`${name}-failed`],
    };
  } finally {
    await context.close();
  }
}

try {
  const storage = await authState();
  const results = [
    await runScenario("consent-absent", false, storage),
    await runScenario("consent-granted", true, storage),
  ];
  const report = {
    generatedAt: new Date().toISOString(),
    baseUrl: baseUrl.split("?")[0],
    route: "/hoteles",
    eventName: "hotel_rum_vitals",
    transport: "authenticated-fetch-keepalive-intercepted-in-qa",
    traceEnabled: false,
    results,
    failedGateFAssertions: results.reduce((sum, result) => sum + result.failedAssertions.length, 0),
    privacy: { credentials: false, tokens: false, queryStrings: false, rawPayloads: false, authenticatedTrace: false, violations: [] },
  };
  const serialized = JSON.stringify(report);
  const violations = [];
  if (/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/.test(serialized)) violations.push("jwt-marker");
  if (/[?&](?:token|password|secret|access_token)=/i.test(serialized)) violations.push("query-secret-marker");
  report.privacy.violations = violations;
  if (violations.length > 0) throw new Error(`gate_f_privacy_validation_failed:${violations.join(",")}`);
  await fs.writeFile(path.join(outputDir, "gate-f.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(`Saved Gate F evidence to ${outputDir}`);
  if (report.failedGateFAssertions > 0) process.exitCode = 1;
} finally {
  await browser.close();
}
