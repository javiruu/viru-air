import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const baseUrl = process.env.E2E_BASE_URL || "http://127.0.0.1:3102";
const screenshotDir = path.join(repoRoot, "docs", "qa", "screenshots", "watchlist-live-flight-tracking");
const reportDir = path.join(repoRoot, "docs", "qa", "reports");
const reportPath = path.join(reportDir, "2026-07-21-watchlist-live-flight-tracking.json");

await mkdir(screenshotDir, { recursive: true });
await mkdir(reportDir, { recursive: true });

const watches = [
  {
    id: "watch-live",
    origin_iata: "MAD",
    destination_iata: "FCO",
    travel_date_local: "2026-07-21",
    target_price: 145,
    status: "active",
    watchers_count: 4,
    group_id: null,
  },
  {
    id: "watch-legacy",
    origin_iata: "AGP",
    destination_iata: "DUB",
    travel_date_local: "2026-07-24",
    target_price: 118,
    status: "active",
    watchers_count: 1,
    group_id: null,
  },
  {
    id: "watch-multi",
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date_local: "2026-07-26",
    target_price: 520,
    status: "active",
    watchers_count: 2,
    group_id: "trip-mad-jfk",
  },
];

const snapshots = [
  {
    watch_id: "watch-live",
    captured_at_utc: "2026-07-21T08:15:00Z",
    raw_price: 132,
    raw_currency: "EUR",
    departure_time_local: "2026-07-21T10:10:00+02:00",
    provider: "amadeus",
    is_stale: false,
    source_kind: "live",
  },
  {
    watch_id: "watch-live",
    captured_at_utc: "2026-07-20T08:15:00Z",
    raw_price: 149,
    raw_currency: "EUR",
    departure_time_local: "2026-07-21T10:10:00+02:00",
    provider: "amadeus",
    is_stale: false,
    source_kind: "live",
  },
  {
    watch_id: "watch-legacy",
    captured_at_utc: "2026-07-21T07:35:00Z",
    raw_price: 109,
    raw_currency: "EUR",
    departure_time_local: "2026-07-24T13:20:00+02:00",
    provider: "duffel",
    is_stale: false,
    source_kind: "live",
  },
  {
    watch_id: "watch-multi",
    captured_at_utc: "2026-07-21T07:05:00Z",
    raw_price: 486,
    raw_currency: "EUR",
    departure_time_local: "2026-07-26T07:10:00+02:00",
    provider: "amadeus",
    is_stale: false,
    source_kind: "live",
  },
];

function watchDetail(id) {
  const watch = watches.find((item) => item.id === id);
  const history = snapshots.filter((item) => item.watch_id === id).map(({ watch_id: _watchId, ...snapshot }) => snapshot);
  return {
    ...watch,
    latest_snapshot: history[0] ?? null,
    price_history: history,
  };
}

function summary(id) {
  const prices = snapshots.filter((item) => item.watch_id === id).map((item) => item.raw_price);
  const latest = prices[0] ?? null;
  const previous = prices[1] ?? null;
  return {
    watch_id: id,
    count: prices.length,
    min_price: prices.length ? Math.min(...prices) : null,
    max_price: prices.length ? Math.max(...prices) : null,
    avg_price: prices.length ? prices.reduce((sum, value) => sum + value, 0) / prices.length : null,
    latest_price: latest,
    delta_pct: latest != null && previous ? ((latest - previous) / previous) * 100 : null,
  };
}

function liveTracking({ freshness = "fresh", status = "active" } = {}) {
  const tracking = {
    watch_id: "watch-live",
    coverage: freshness === "fresh" ? "live" : "temporarily_unavailable",
    provider_status: freshness === "fresh" ? "ok" : "unavailable",
    generated_at: "2026-07-21T08:38:00Z",
    refresh_after_seconds: 30,
    legs: [
      {
        sequence: 0,
        identity: {
          flight_instance_fingerprint: "ux-live-az61-20260721",
          flight_number: "AZ61",
          carrier_code: "AZ",
          origin_iata: "MAD",
          destination_iata: "FCO",
          scheduled_departure_at: "2026-07-21T08:10:00Z",
          scheduled_arrival_at: "2026-07-21T10:35:00Z",
        },
        operational: {
          status,
          status_raw: status,
          observed_at: "2026-07-21T08:37:30Z",
          expires_at: "2026-07-21T08:38:30Z",
          freshness,
          provider: "aviationstack",
          callsign: "ITY61",
          departure: {
            scheduled_at: "2026-07-21T08:10:00Z",
            estimated_at: "2026-07-21T08:24:00Z",
            actual_at: "2026-07-21T08:27:00Z",
            terminal: "1",
            gate: "B26",
            delay_minutes: 17,
          },
          arrival: {
            scheduled_at: "2026-07-21T10:35:00Z",
            estimated_at: "2026-07-21T10:48:00Z",
            actual_at: null,
            terminal: "3",
            gate: null,
            delay_minutes: 13,
          },
          position: {
            latitude: 41.02,
            longitude: 4.83,
            altitude_m: 10363,
            speed_mps: 238,
            heading_deg: 82,
            on_ground: false,
          },
          registration: "EI-IKU",
          aircraft_iata: "A320",
          aircraft_icao: "A320",
          data_quality: "provider_observation",
        },
      },
    ],
  };
  if (status === "landed" || status === "cancelled") {
    tracking.coverage = "completed";
    tracking.refresh_after_seconds = 21600;
    tracking.legs[0].operational.position = null;
    if (status === "landed") {
      tracking.legs[0].operational.arrival.actual_at = "2026-07-21T10:51:00Z";
    }
  }
  return tracking;
}

function identityMissing() {
  return {
    watch_id: "watch-legacy",
    coverage: "identity_missing",
    provider_status: "no_match",
    generated_at: "2026-07-21T08:38:00Z",
    refresh_after_seconds: 3600,
    legs: [],
  };
}

function multiLegTracking() {
  const first = structuredClone(liveTracking().legs[0]);
  first.identity = {
    ...first.identity,
    flight_instance_fingerprint: "ux-multi-ib3170-20260726",
    flight_number: "IB3170",
    carrier_code: "IB",
    origin_iata: "MAD",
    destination_iata: "BCN",
  };
  first.operational.status = "landed";
  first.operational.callsign = "IBE3170";
  first.operational.position = null;

  const second = structuredClone(first);
  second.sequence = 1;
  second.identity = {
    ...second.identity,
    flight_instance_fingerprint: "ux-multi-ba117-20260726",
    flight_number: "BA117",
    carrier_code: "BA",
    origin_iata: "BCN",
    destination_iata: "FCO",
  };
  second.operational.status = "scheduled";
  second.operational.callsign = "BAW117";
  second.operational.departure.actual_at = null;
  second.operational.departure.estimated_at = "2026-07-26T10:25:00Z";
  second.operational.arrival.actual_at = null;
  second.operational.arrival.estimated_at = "2026-07-26T18:12:00Z";

  const third = structuredClone(second);
  third.sequence = 2;
  third.identity = {
    ...third.identity,
    flight_instance_fingerprint: "ux-multi-aa2134-20260726",
    flight_number: "AA2134",
    carrier_code: "AA",
    origin_iata: "FCO",
    destination_iata: "DUB",
  };
  third.operational.callsign = "AAL2134";
  third.operational = null;

  return {
    watch_id: "watch-multi",
    coverage: "live",
    provider_status: "ok",
    generated_at: "2026-07-21T08:38:00Z",
    refresh_after_seconds: 60,
    legs: [first, second, third],
  };
}

const report = {
  generated_at: new Date().toISOString(),
  base_url: baseUrl,
  route: "/watchlist",
  completed: false,
  assertions: {},
  request_counts: { live_total: 0, by_watch: {} },
  console_errors: [],
  expected_console_errors: [],
  unexpected_http_errors: [],
  screenshots: [],
};

let failLiveRequests = false;
let delayNextLiveRequest = false;
let liveStatus = "active";

function recordLiveRequest(watchId) {
  report.request_counts.live_total += 1;
  report.request_counts.by_watch[watchId] = (report.request_counts.by_watch[watchId] ?? 0) + 1;
}

async function fulfillJson(route, body, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function installMocks(page) {
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    if (failLiveRequests && message.text().includes("503")) {
      report.expected_console_errors.push(message.text());
      return;
    }
    report.console_errors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 400 && !response.url().includes("/watchlist/watch-live/live")) {
      report.unexpected_http_errors.push({ url: response.url(), status: response.status() });
    }
  });

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const apiPath = url.pathname.replace(/^.*\/api\/v1/, "");

    if (apiPath === "/auth/me") {
      await fulfillJson(route, { id: "qa-user", email: "qa@viru.local", locale: "es", is_admin: false });
      return;
    }
    if (apiPath === "/watchlist" && request.method() === "GET") {
      await fulfillJson(route, watches);
      return;
    }
    if (apiPath === "/prices/history/batch") {
      await fulfillJson(route, snapshots);
      return;
    }
    if (apiPath.startsWith("/prices/summary")) {
      await fulfillJson(route, summary(url.searchParams.get("watch_id")));
      return;
    }
    if (apiPath.startsWith("/prices/compare")) {
      await fulfillJson(route, { currency_mode: "single", watches: [], points: [] });
      return;
    }
    const liveMatch = apiPath.match(/^\/watchlist\/([^/]+)\/live$/);
    if (liveMatch) {
      const watchId = liveMatch[1];
      recordLiveRequest(watchId);
      if (delayNextLiveRequest) {
        delayNextLiveRequest = false;
        await new Promise((resolve) => setTimeout(resolve, 700));
      }
      if (failLiveRequests && watchId === "watch-live") {
        await fulfillJson(route, { detail: "operational_provider_unavailable" }, 503);
        return;
      }
      await fulfillJson(
        route,
        watchId === "watch-live"
          ? liveTracking({ status: liveStatus })
          : watchId === "watch-multi"
            ? multiLegTracking()
            : identityMissing(),
      );
      return;
    }
    const detailMatch = apiPath.match(/^\/watchlist\/([^/]+)$/);
    if (detailMatch && request.method() === "GET") {
      await fulfillJson(route, watchDetail(detailMatch[1]));
      return;
    }
    if (apiPath.startsWith("/airports/compatible")) {
      await fulfillJson(route, { seed_iata: "MAD", travel_date: "2026-07-21", compatible_iata: [], source: "qa" });
      return;
    }
    await fulfillJson(route, {});
  });
}

async function createPage(browser, viewport, theme, locale = "es") {
  const context = await browser.newContext({ viewport, reducedMotion: "reduce" });
  await context.addInitScript(({ selectedTheme, selectedLocale }) => {
    localStorage.setItem("viru_token", "qa_token_for_mocked_browser_session_1234567890");
    localStorage.setItem("viru-theme", selectedTheme);
    localStorage.setItem("viru-locale", selectedLocale);
    localStorage.setItem("viru-ftue-watchlist", "dismissed");
  }, { selectedTheme: theme, selectedLocale: locale });
  const page = await context.newPage();
  await installMocks(page);
  return { context, page };
}

async function openWatchlist(page) {
  await page.goto(`${baseUrl}/watchlist?watch_id=watch-live`, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.locator(".watch-live-flight-leg").waitFor({ state: "visible", timeout: 20_000 });
  await page.locator(".watch-map-stage .maplibregl-canvas").waitFor({ state: "visible", timeout: 20_000 });
  await page.waitForTimeout(1_000);
}

async function capture(page, filename, locator = null) {
  const targetPath = path.join(screenshotDir, filename);
  if (locator) {
    await locator.screenshot({ path: targetPath });
  } else {
    await page.screenshot({ path: targetPath, fullPage: true });
  }
  report.screenshots.push(path.relative(repoRoot, targetPath).replaceAll("\\", "/"));
}

async function assertNoHorizontalOverflow(page, label) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  report.assertions[`${label}_horizontal_overflow_px`] = overflow;
  if (overflow > 1) throw new Error(`${label} has ${overflow}px horizontal overflow`);
}

const browser = await chromium.launch({ headless: true });

try {
  const desktopDark = await createPage(browser, { width: 1440, height: 1100 }, "dark");
  await openWatchlist(desktopDark.page);
  report.assertions.active_status_visible = await desktopDark.page.getByText("En vuelo", { exact: true }).isVisible();
  report.assertions.position_label_visible = await desktopDark.page.getByText("Posición real en el mapa", { exact: true }).isVisible();
  report.assertions.callsign_visible = await desktopDark.page.getByText("ITY61", { exact: true }).isVisible();
  report.assertions.telemetry_visible = await desktopDark.page.getByText("Altitud 10.363 m", { exact: true }).isVisible();
  const observedMarker = desktopDark.page.locator(".watch-map-live-marker");
  await observedMarker.waitFor({ state: "visible", timeout: 20_000 });
  report.assertions.observed_marker_visible = (await observedMarker.count()) === 1;
  report.assertions.observed_marker_heading_bound = await observedMarker.evaluate(
    (element) => element.style.getPropertyValue("--watch-map-heading") === "82deg",
  );
  const observedMarkerGeometry = await observedMarker.evaluate((element) => {
    const marker = element.getBoundingClientRect();
    const stage = element.closest(".watch-map-stage")?.getBoundingClientRect();
    if (!stage) return { inside: false, marker: null, stage: null, topElement: null };
    const topElement = document.elementFromPoint(marker.left + marker.width / 2, marker.top + marker.height / 2);
    return {
      inside:
        marker.left >= stage.left + 2 &&
        marker.right <= stage.right - 2 &&
        marker.top >= stage.top + 2 &&
        marker.bottom <= stage.bottom - 2,
      marker: { left: marker.left, right: marker.right, top: marker.top, bottom: marker.bottom },
      stage: { left: stage.left, right: stage.right, top: stage.top, bottom: stage.bottom },
      topElement: topElement?.className?.toString() ?? topElement?.tagName ?? null,
    };
  });
  report.marker_geometry = observedMarkerGeometry;
  report.assertions.observed_marker_inside_map_bounds = observedMarkerGeometry.inside;
  report.assertions.observed_map_popup_not_auto_open =
    (await desktopDark.page.locator(".watch-map-panel .maplibregl-popup").count()) === 0;
  report.assertions.reduced_motion_active = await desktopDark.page.evaluate(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  await assertNoHorizontalOverflow(desktopDark.page, "desktop_dark");
  await capture(desktopDark.page, "01-desktop-dark-page.png");
  await capture(desktopDark.page, "02-desktop-dark-live-panel.png", desktopDark.page.locator(".watch-live-flight"));
  await capture(desktopDark.page, "14-desktop-dark-observed-position-map.png", desktopDark.page.locator(".watch-map-panel"));

  const requestsBeforeHidden = report.request_counts.live_total;
  await desktopDark.page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await desktopDark.page.waitForTimeout(31_000);
  report.assertions.hidden_tab_suppressed_polling = report.request_counts.live_total === requestsBeforeHidden;
  await desktopDark.page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => false });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await desktopDark.page.waitForTimeout(800);
  report.assertions.visible_tab_resumed_polling = report.request_counts.live_total > requestsBeforeHidden;

  const legacyRow = desktopDark.page.locator(".watch-row", { hasText: "AGP → DUB" });
  await legacyRow.click();
  await desktopDark.page.getByText("Esta ruta aún no sabe qué avión seguir", { exact: true }).waitFor({ state: "visible" });
  report.assertions.identity_copy_has_no_raw_i18n_keys =
    (await desktopDark.page.getByText(/^watchlist\.(live|map)\./).count()) === 0;
  report.assertions.identity_map_popup_not_auto_open =
    (await desktopDark.page.locator(".watch-map-panel .maplibregl-popup").count()) === 0;
  report.assertions.identity_recovery_cta_visible = await desktopDark.page.getByRole("link", { name: "Buscar este vuelo exacto" }).isVisible();
  report.assertions.identity_state_hides_useless_refresh = (await desktopDark.page.locator(".watch-live-flight-refresh").count()) === 0;
  await capture(desktopDark.page, "06-desktop-dark-identity-missing.png", desktopDark.page.locator(".watch-live-flight"));

  const multiRow = desktopDark.page.locator(".watch-row", { hasText: "MAD → DUB" });
  await multiRow.click();
  await desktopDark.page.getByText("IB3170", { exact: true }).waitFor({ state: "visible" });
  const secondaryLegs = desktopDark.page.locator(".watch-live-flight-leg--secondary");
  report.assertions.multileg_secondary_legs_collapsed =
    (await secondaryLegs.count()) === 2 &&
    (await secondaryLegs.evaluateAll((elements) => elements.every((element) => !element.hasAttribute("open"))));
  await capture(desktopDark.page, "08-desktop-dark-multileg-collapsed.png", desktopDark.page.locator(".watch-live-flight"));
  await secondaryLegs.nth(1).locator("summary").click();
  report.assertions.multileg_missing_leg_visible = await secondaryLegs.nth(1).getByText(
    "Este tramo está enlazado, pero todavía no tiene una observación operacional fiable.",
    { exact: true },
  ).isVisible();
  report.assertions.no_synthetic_route_dot = (await desktopDark.page.locator(".watch-map-route-dot").count()) === 0;
  report.assertions.no_position_copy_visible = await desktopDark.page.getByText(
    "Sin posición observada: la línea muestra la ruta, no la ubicación del avión.",
    { exact: true },
  ).isVisible();
  await capture(desktopDark.page, "13-desktop-dark-multileg-partial.png", desktopDark.page.locator(".watch-live-flight"));
  await desktopDark.page.waitForTimeout(1_200);
  await capture(desktopDark.page, "09-desktop-dark-no-position-map.png", desktopDark.page.locator(".watch-map-panel"));

  const liveRow = desktopDark.page.locator(".watch-row", { hasText: "MAD → FCO" });
  await liveRow.click();
  await desktopDark.page.locator(".watch-live-flight-leg").waitFor({ state: "visible" });
  failLiveRequests = true;
  await desktopDark.page.locator(".watch-live-flight-refresh").click();
  await desktopDark.page.getByText("La última comprobación no ha respondido", { exact: true }).waitFor({ state: "visible" });
  report.assertions.stale_while_error_preserved = await desktopDark.page.locator(".watch-live-flight-leg").isVisible();
  report.assertions.error_degrades_coverage_badge = await desktopDark.page.getByText("Señal intermitente", { exact: true }).isVisible();
  report.assertions.error_labels_retained_data = await desktopDark.page.getByText("Último dato conocido", { exact: true }).isVisible();
  await capture(desktopDark.page, "07-desktop-dark-stale-error.png", desktopDark.page.locator(".watch-live-flight"));
  failLiveRequests = false;
  liveStatus = "landed";
  await desktopDark.page.locator(".watch-live-flight-refresh").click();
  await desktopDark.page.getByText("Aterrizado", { exact: true }).waitFor({ state: "visible" });
  report.assertions.landed_state_visible = true;
  liveStatus = "cancelled";
  await desktopDark.page.locator(".watch-live-flight-refresh").click();
  await desktopDark.page.getByText("Cancelado", { exact: true }).waitFor({ state: "visible" });
  report.assertions.cancelled_state_visible = true;
  liveStatus = "active";
  await desktopDark.context.close();

  const desktopLight = await createPage(browser, { width: 1440, height: 1100 }, "light");
  await openWatchlist(desktopLight.page);
  await assertNoHorizontalOverflow(desktopLight.page, "desktop_light");
  await capture(desktopLight.page, "03-desktop-light-live-panel.png", desktopLight.page.locator(".watch-live-flight"));
  const cdp = await desktopLight.context.newCDPSession(desktopLight.page);
  await cdp.send("Emulation.setPageScaleFactor", { pageScaleFactor: 2 });
  report.assertions.zoom_200_live_panel_visible = await desktopLight.page.locator(".watch-live-flight").isVisible();
  await desktopLight.context.close();

  const reportedViewport = await createPage(browser, { width: 1074, height: 787 }, "light");
  await openWatchlist(reportedViewport.page);
  await reportedViewport.page.locator(".watch-row", { hasText: "AGP → DUB" }).click();
  await reportedViewport.page
    .getByText("Esta ruta aún no sabe qué avión seguir", { exact: true })
    .waitFor({ state: "visible" });
  report.assertions.reported_viewport_has_no_raw_i18n_keys =
    (await reportedViewport.page.getByText(/^watchlist\.(live|map)\./).count()) === 0;
  report.assertions.reported_viewport_popup_not_auto_open =
    (await reportedViewport.page.locator(".watch-map-panel .maplibregl-popup").count()) === 0;
  await capture(reportedViewport.page, "15-reported-viewport-light-page.png");
  await reportedViewport.page.locator(".watch-map-chip.is-primary").first().click();
  const manualPopup = reportedViewport.page.locator(".watch-map-panel .maplibregl-popup");
  await manualPopup.waitFor({ state: "visible" });
  const manualPopupGeometry = await manualPopup.evaluate((element) => {
    const popup = element.getBoundingClientRect();
    const stage = element.closest(".watch-map-stage")?.getBoundingClientRect();
    if (!stage) return { inside: false, popup: null, stage: null };
    return {
      inside:
        popup.left >= stage.left &&
        popup.right <= stage.right &&
        popup.top >= stage.top &&
        popup.bottom <= stage.bottom,
      popup: { left: popup.left, right: popup.right, top: popup.top, bottom: popup.bottom },
      stage: { left: stage.left, right: stage.right, top: stage.top, bottom: stage.bottom },
    };
  });
  report.manual_popup_geometry = manualPopupGeometry;
  report.assertions.reported_viewport_manual_popup_inside_map = manualPopupGeometry.inside;
  await capture(
    reportedViewport.page,
    "16-reported-viewport-light-manual-popup.png",
    reportedViewport.page.locator(".watch-map-panel"),
  );
  await reportedViewport.context.close();

  const tablet = await createPage(browser, { width: 768, height: 1024 }, "light");
  await openWatchlist(tablet.page);
  await assertNoHorizontalOverflow(tablet.page, "tablet_light");
  await capture(tablet.page, "10-tablet-light-live-panel.png", tablet.page.locator(".watch-live-flight"));
  await tablet.context.close();

  for (const [theme, filename] of [["dark", "04-mobile-dark-live-panel.png"], ["light", "05-mobile-light-live-panel.png"]]) {
    const mobile = await createPage(browser, { width: 390, height: 844 }, theme);
    await openWatchlist(mobile.page);
    await assertNoHorizontalOverflow(mobile.page, `mobile_${theme}`);
    await capture(mobile.page, filename, mobile.page.locator(".watch-live-flight"));
    await mobile.context.close();
  }

  for (const [width, height, theme, locale, filename] of [
    [375, 812, "dark", "es", "11-mobile-375-dark-live-panel.png"],
    [320, 700, "light", "en", "12-mobile-320-light-live-panel.png"],
  ]) {
    const narrowMobile = await createPage(browser, { width, height }, theme, locale);
    await openWatchlist(narrowMobile.page);
    await assertNoHorizontalOverflow(narrowMobile.page, `mobile_${width}_${theme}`);
    await capture(narrowMobile.page, filename);
    if (width === 375) {
      const mobileMap = narrowMobile.page.locator(".watch-map-panel");
      await mobileMap.scrollIntoViewIfNeeded();
      await narrowMobile.page.waitForTimeout(1_200);
      await capture(narrowMobile.page, "17-mobile-375-dark-map.png", mobileMap);
    }
    await narrowMobile.context.close();
  }

  delayNextLiveRequest = true;
  const race = await createPage(browser, { width: 1280, height: 900 }, "dark");
  await race.page.goto(`${baseUrl}/watchlist?watch_id=watch-live`, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await race.page.locator(".watch-row", { hasText: "AGP → DUB" }).waitFor({ state: "visible", timeout: 20_000 });
  await race.page.locator(".watch-row", { hasText: "AGP → DUB" }).click();
  await race.page.getByText("Esta ruta aún no sabe qué avión seguir", { exact: true }).waitFor({ state: "visible", timeout: 5_000 });
  await race.page.waitForTimeout(900);
  report.assertions.race_did_not_overwrite_selection =
    (await race.page.getByText("Esta ruta aún no sabe qué avión seguir", { exact: true }).isVisible()) &&
    (await race.page.locator(".watch-live-flight-leg").count()) === 0;
  await capture(race.page, "18-race-1280-dark-page.png");
  await race.context.close();

  const requiredAssertions = [
    "active_status_visible",
    "position_label_visible",
    "callsign_visible",
    "telemetry_visible",
    "observed_marker_visible",
    "observed_marker_heading_bound",
    "observed_marker_inside_map_bounds",
    "observed_map_popup_not_auto_open",
    "reduced_motion_active",
    "hidden_tab_suppressed_polling",
    "visible_tab_resumed_polling",
    "identity_recovery_cta_visible",
    "identity_copy_has_no_raw_i18n_keys",
    "identity_map_popup_not_auto_open",
    "identity_state_hides_useless_refresh",
    "multileg_secondary_legs_collapsed",
    "multileg_missing_leg_visible",
    "no_synthetic_route_dot",
    "no_position_copy_visible",
    "stale_while_error_preserved",
    "error_degrades_coverage_badge",
    "error_labels_retained_data",
    "landed_state_visible",
    "cancelled_state_visible",
    "zoom_200_live_panel_visible",
    "reported_viewport_has_no_raw_i18n_keys",
    "reported_viewport_popup_not_auto_open",
    "reported_viewport_manual_popup_inside_map",
    "race_did_not_overwrite_selection",
  ];
  for (const assertion of requiredAssertions) {
    if (report.assertions[assertion] !== true) throw new Error(`Failed assertion: ${assertion}`);
  }
  if (report.console_errors.length) throw new Error(`Console errors: ${report.console_errors.length}`);
  if (report.unexpected_http_errors.length) throw new Error(`Unexpected HTTP errors: ${report.unexpected_http_errors.length}`);
  report.completed = true;
} finally {
  await browser.close();
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
}

console.log(`QA report: ${path.relative(repoRoot, reportPath)}`);
console.log(`Screenshots: ${report.screenshots.length}`);
