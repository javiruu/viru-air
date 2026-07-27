import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const baseUrl = process.env.E2E_BASE_URL || "http://127.0.0.1:3102";
const screenshotDir = path.join(repoRoot, "docs", "qa", "screenshots", "watchlist-delay-prediction");
const reportPath = path.join(repoRoot, "docs", "qa", "reports", "2026-07-28-watchlist-delay-prediction.json");

const watch = {
  id: "watch-prediction",
  origin_iata: "MAD",
  destination_iata: "FCO",
  travel_date_local: "2026-07-28",
  target_price: 145,
  status: "active",
  watchers_count: 4,
  group_id: null,
};

const snapshot = {
  watch_id: watch.id,
  captured_at_utc: "2026-07-27T20:15:00Z",
  raw_price: 132,
  raw_currency: "EUR",
  departure_time_local: "2026-07-28T12:00:00+02:00",
  provider: "amadeus",
  is_stale: false,
  source_kind: "live",
};

const liveTracking = {
  watch_id: watch.id,
  coverage: "live",
  provider_status: "ok",
  generated_at: "2026-07-28T09:45:00Z",
  refresh_after_seconds: 300,
  legs: [
    {
      sequence: 0,
      identity: {
        flight_instance_fingerprint: "qa-ib3230-20260728",
        flight_number: "IB3230",
        carrier_code: "IB",
        origin_iata: "MAD",
        destination_iata: "FCO",
        scheduled_departure_at: "2026-07-28T10:00:00Z",
        scheduled_arrival_at: "2026-07-28T12:25:00Z",
      },
      operational: {
        status: "scheduled",
        status_raw: "scheduled",
        observed_at: "2026-07-28T09:44:30Z",
        expires_at: "2026-07-28T09:49:30Z",
        freshness: "fresh",
        provider: "aviationstack",
        callsign: "IBE3230",
        departure: {
          scheduled_at: "2026-07-28T10:00:00Z",
          estimated_at: null,
          actual_at: null,
          terminal: "4",
          gate: "J42",
          delay_minutes: null,
        },
        arrival: {
          scheduled_at: "2026-07-28T12:25:00Z",
          estimated_at: null,
          actual_at: null,
          terminal: "1",
          gate: null,
          delay_minutes: null,
        },
        position: null,
        registration: "EC-ROT",
        aircraft_iata: "A320",
        aircraft_icao: "A320",
        data_quality: "status_only",
      },
      delay_prediction: {
        status: "available",
        model_version: "viru_rotation_v1",
        risk: "high",
        risk_score: 90,
        confidence: "high",
        predicted_delay_min_minutes: 20,
        predicted_delay_max_minutes: 40,
        turnaround_minutes: 20,
        factor_codes: ["incoming_running_late", "tight_turnaround", "incoming_airborne"],
        incoming_aircraft: {
          registration: "EC-ROT",
          flight_number: "IB1234",
          origin_iata: "BCN",
          destination_iata: "MAD",
          status: "active",
          scheduled_arrival_at: "2026-07-28T08:30:00Z",
          estimated_arrival_at: "2026-07-28T09:40:00Z",
          actual_arrival_at: null,
          observed_at: "2026-07-28T09:44:30Z",
          freshness: "fresh",
        },
      },
    },
  ],
};

await mkdir(screenshotDir, { recursive: true });
await mkdir(path.dirname(reportPath), { recursive: true });

const report = {
  generated_at: new Date().toISOString(),
  route: "/watchlist?watch_id=watch-prediction",
  completed: false,
  scenarios: [],
};

async function fulfillJson(route, body) {
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

async function installMocks(page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const apiPath = url.pathname.replace(/^.*\/api\/v1/, "");

    if (apiPath === "/auth/me") {
      await fulfillJson(route, { id: "qa-user", email: "qa@viru.local", locale: "es", is_admin: false });
      return;
    }
    if (apiPath === "/watchlist" && request.method() === "GET") {
      await fulfillJson(route, [watch]);
      return;
    }
    if (apiPath === `/watchlist/${watch.id}` && request.method() === "GET") {
      await fulfillJson(route, { ...watch, latest_snapshot: snapshot, price_history: [snapshot] });
      return;
    }
    if (apiPath === `/watchlist/${watch.id}/live`) {
      await fulfillJson(route, liveTracking);
      return;
    }
    if (apiPath === "/prices/history/batch") {
      await fulfillJson(route, [snapshot]);
      return;
    }
    if (apiPath.startsWith("/prices/summary")) {
      await fulfillJson(route, {
        watch_id: watch.id,
        count: 1,
        min_price: 132,
        max_price: 132,
        avg_price: 132,
        latest_price: 132,
        delta_pct: null,
      });
      return;
    }
    if (apiPath.startsWith("/prices/compare")) {
      await fulfillJson(route, { currency_mode: "single", watches: [], points: [] });
      return;
    }
    if (apiPath.startsWith("/airports/compatible")) {
      await fulfillJson(route, {
        seed_iata: "MAD",
        travel_date: "2026-07-28",
        compatible_iata: [],
        source: "qa",
      });
      return;
    }
    await fulfillJson(route, {});
  });
}

const browser = await chromium.launch({ headless: true });

try {
  for (const scenario of [
    { name: "desktop_dark", width: 1440, height: 1000, theme: "dark" },
    { name: "desktop_light", width: 1440, height: 1000, theme: "light" },
    { name: "mobile_dark", width: 390, height: 844, theme: "dark" },
    { name: "mobile_light", width: 390, height: 844, theme: "light" },
  ]) {
    const context = await browser.newContext({
      viewport: { width: scenario.width, height: scenario.height },
      reducedMotion: "reduce",
    });
    await context.addInitScript(({ theme }) => {
      localStorage.setItem("viru_token", "qa_token_for_mocked_browser_session_1234567890");
      localStorage.setItem("viru-theme", theme);
      localStorage.setItem("viru-locale", "es");
      localStorage.setItem("viru-ftue-watchlist", "dismissed");
    }, { theme: scenario.theme });
    const page = await context.newPage();
    const consoleErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    await installMocks(page);
    await page.goto(`${baseUrl}/watchlist?watch_id=${watch.id}`, {
      waitUntil: "domcontentloaded",
      timeout: 30_000,
    });

    const prediction = page.locator(".watch-delay-prediction");
    await prediction.waitFor({ state: "visible", timeout: 20_000 });
    const assertions = {
      title: await prediction.getByText("Predicción de retraso", { exact: true }).isVisible(),
      range: await prediction.getByText("+20–40 min", { exact: true }).isVisible(),
      incoming: await prediction.getByText("IB1234 · EC-ROT", { exact: true }).isVisible(),
      risk: await prediction.getByText("Riesgo alto · 90/100", { exact: true }).isVisible(),
      evidence: await prediction.getByText("Escala muy ajustada", { exact: true }).isVisible(),
      disclaimer: await prediction
        .getByText("Estimación temprana y explicable; no sustituye el horario oficial.", { exact: true })
        .isVisible(),
      no_raw_i18n: (await prediction.getByText(/^watchlist\./).count()) === 0,
      no_horizontal_overflow:
        (await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)) <= 1,
      no_console_errors: consoleErrors.length === 0,
    };
    if (Object.values(assertions).some((value) => value !== true)) {
      throw new Error(`Failed ${scenario.name}: ${JSON.stringify(assertions)}`);
    }
    const screenshotPath = path.join(screenshotDir, `${scenario.name}.png`);
    const livePanel = page.locator(".watch-live-flight");
    const captureHeight = scenario.width <= 520 ? 1400 : scenario.height;
    if (captureHeight !== scenario.height) {
      await page.setViewportSize({ width: scenario.width, height: captureHeight });
    }
    await livePanel.scrollIntoViewIfNeeded();
    if (scenario.width <= 520) {
      await page.evaluate(() => window.scrollBy(0, -132));
    }
    const panelBox = await livePanel.boundingBox();
    if (!panelBox) throw new Error(`Missing panel geometry for ${scenario.name}`);
    await page.screenshot({
      path: screenshotPath,
      captureBeyondViewport: true,
      clip: {
        x: Math.max(0, panelBox.x),
        y: Math.max(0, panelBox.y),
        width: panelBox.width,
        height: panelBox.height,
      },
    });
    report.scenarios.push({
      ...scenario,
      capture_height: captureHeight,
      assertions,
      screenshot: path.relative(repoRoot, screenshotPath).replaceAll("\\", "/"),
    });
    await context.close();
  }
  report.completed = true;
} finally {
  await browser.close();
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
}

console.log(`QA report: ${path.relative(repoRoot, reportPath)}`);
console.log(`Scenarios: ${report.scenarios.length}`);
