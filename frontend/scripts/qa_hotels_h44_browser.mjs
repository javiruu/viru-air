import { mkdir, readFile, unlink } from "node:fs/promises";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

import { chromium, request } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const backendRoot = path.join(repoRoot, "backend");
const outputDir = path.resolve(
  repoRoot,
  process.env.H44_OUTPUT_DIR?.trim() || path.join("docs", "qa", "evidence", "hotels-h44-browser-current"),
);
const configuredBaseUrl = process.env.H44_BASE_URL?.trim() || "";
const configuredApiBaseUrl = process.env.H44_API_BASE_URL?.trim() || "";
const faultProfile = process.env.H44_FAULT_PROFILE?.trim() || "happy_path";
const datasetId = "hoteles-demo-v1";
const pythonCommand = process.env.PYTHON || "python";
const demoPassword = "ViruDemoOnly-2026";
const demoUsers = {
  owner: "demo-user-a@viru.local",
  observer: "demo-user-b@viru.local",
};

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

function redactUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);
    const pathWithIds = url.pathname.replace(
      /\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?=\/|$)/gi,
      "/[id]",
    );
    return `${url.origin}${pathWithIds}${url.search ? "?present" : ""}`;
  } catch {
    return "[url-redacted]";
  }
}

function sanitize(value) {
  return String(value || "")
    .replace(/https?:\/\/[^\s"'<>]+/gi, redactUrl)
    .replace(/(authorization\s*[:=]\s*bearer\s+)[^\s,;]+/gi, "$1[redacted]")
    .replace(/((?:token|api[_-]?key|password|secret)\s*[:=]\s*)[^\s,;]+/gi, "$1[redacted]")
    .replace(/([?&](?:token|api[_-]?key|password|secret|access_token)\s*=\s*)[^&\s]+/gi, "$1[redacted]")
    .replace(/\b[\w.+-]+@[\w.-]+\.[A-Z]{2,}\b/gi, "[email-redacted]")
    .slice(0, 500);
}

function sanitizeProcessLogs(logs) {
  if (!logs) return null;
  return { stdout: sanitize(logs.stdout), stderr: sanitize(logs.stderr) };
}

function assertCondition(condition, message) {
  if (!condition) throw new Error(message);
}

async function reservePort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : null;
  await new Promise((resolve) => server.close(resolve));
  assertCondition(Number.isInteger(port), "port_reservation_failed");
  return port;
}

function runProcess(command, args, { cwd, env, timeoutMs = 120_000 } = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, { cwd, env, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const append = (target, chunk) => chunk.length > 12_000 ? `${target}${chunk}`.slice(-12_000) : `${target}${chunk}`;
    child.stdout.on("data", (chunk) => { stdout = append(stdout, chunk.toString()); });
    child.stderr.on("data", (chunk) => { stderr = append(stderr, chunk.toString()); });
    const timeout = setTimeout(() => {
      timedOut = true;
      terminateProcess(child);
    }, timeoutMs);
    child.once("close", (code, signal) => {
      clearTimeout(timeout);
      resolve({ code, signal, stdout, stderr, timedOut });
    });
    child.once("error", (error) => {
      clearTimeout(timeout);
      resolve({ code: null, signal: null, stdout, stderr: `${stderr}\n${error.message}`, timedOut });
    });
  });
}

function startProcess(command, args, { cwd, env }) {
  const child = spawn(command, args, { cwd, env, stdio: ["ignore", "pipe", "pipe"] });
  let stdout = "";
  let stderr = "";
  const append = (target, chunk) => chunk.length > 12_000 ? `${target}${chunk}`.slice(-12_000) : `${target}${chunk}`;
  child.stdout.on("data", (chunk) => { stdout = append(stdout, chunk.toString()); });
  child.stderr.on("data", (chunk) => { stderr = append(stderr, chunk.toString()); });
  child.on("error", (error) => { stderr = append(stderr, error.message); });
  return { child, getLogs: () => ({ stdout, stderr }) };
}

async function stopProcess(processHandle) {
  const child = processHandle?.child;
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  terminateProcess(child);
  await Promise.race([
    new Promise((resolve) => child.once("close", resolve)),
    sleep(5_000),
  ]);
  if (child.exitCode === null && child.signalCode === null) {
    child.kill("SIGKILL");
    await sleep(250);
  }
}

function terminateProcess(child) {
  if (!child || child.killed) return;
  if (process.platform === "win32" && child.pid) {
    const killer = spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
    killer.once("error", () => child.kill());
    return;
  }
  child.kill("SIGTERM");
}

async function waitForHttp(url, { timeoutMs = 120_000 } = {}) {
  const startedAt = Date.now();
  let lastError = "unreachable";
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.status < 500) return response.status;
      lastError = `http_${response.status}`;
    } catch (error) {
      lastError = sanitize(error?.message || error);
    }
    await sleep(500);
  }
  throw new Error(`service_not_ready:${redactUrl(url)}:${lastError}`);
}

function lastJsonLine(output) {
  const lines = output.trim().split(/\r?\n/).filter(Boolean);
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    try {
      return JSON.parse(lines[index]);
    } catch {
      // Alembic/uvicorn output may precede the script's JSON report.
    }
  }
  return null;
}

async function loadProfileManifest() {
  const manifestPath = path.join(backendRoot, "app", "hotels", "fixtures", "hotel_fault_profiles.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  const profile = manifest.profiles?.[faultProfile];
  assertCondition(profile && typeof profile === "object", `unknown_fault_profile:${faultProfile}`);
  return { manifestVersion: manifest.version, profile };
}

function dbUrlFor(dbPath) {
  return `sqlite:///${dbPath.split(path.sep).join("/")}`;
}

function demoEnvironment(dbUrl, { profile = "happy_path" } = {}) {
  return {
    ...process.env,
    APP_ENV: "local_fixture",
    DB_URL: dbUrl,
    HOTEL_PROVIDER: "mock",
    HOTEL_PROFILE: "local_fixture",
    HOTEL_MOCK_FAULT_PROFILE: profile,
    HOTEL_FEATURE_ENABLED: "true",
    HOTEL_SWEEP_ENABLED: "false",
    HOTEL_GEOCODER_ENABLED: "false",
    RUN_DB_INIT: "false",
    RUN_SEED_USERS: "false",
    WATCHLIST_STARTUP_REFRESH_ENABLED: "false",
    FARE_MEMORY_ENABLED: "false",
    FARE_MEMORY_BOOT_WARMUP_ENABLED: "false",
    FARE_MEMORY_RETENTION_ENABLED: "false",
    FARE_MEMORY_REVALIDATION_WORKER_ENABLED: "false",
    PYTHONUTF8: "1",
  };
}

async function seedDatabase(dbUrl) {
  const result = await runProcess(
    pythonCommand,
    ["scripts/hotel_demo_seed.py", "seed", "--db-url", dbUrl],
    { cwd: backendRoot, env: demoEnvironment(dbUrl, { profile: "happy_path" }), timeoutMs: 180_000 },
  );
  const report = lastJsonLine(result.stdout);
  assertCondition(result.code === 0 && report?.result === "passed", `seed_failed:${sanitize(result.stderr || result.stdout)}`);
  assertCondition(report.dataset_id === datasetId, "seed_dataset_mismatch");
  assertCondition(report.external_calls_observed === 0, "seed_external_calls_observed");
  return report;
}

async function resetDatabase(dbUrl) {
  const result = await runProcess(
    pythonCommand,
    ["scripts/hotel_demo_seed.py", "reset", "--db-url", dbUrl, "--confirm-demo-db"],
    {
      cwd: backendRoot,
      env: {
        ...demoEnvironment(dbUrl, { profile: "happy_path" }),
        HOTEL_PROFILE: "local_fixture",
      },
      timeoutMs: 180_000,
    },
  );
  const report = lastJsonLine(result.stdout);
  assertCondition(result.code === 0 && report?.result === "passed", `reset_failed:${sanitize(result.stderr || result.stdout)}`);
  assertCondition(report.dataset_id === datasetId, "reset_dataset_mismatch");
  return report;
}

async function login(api, email) {
  const response = await api.post("auth/login", { data: { email, password: demoPassword } });
  const body = await response.json();
  assertCondition(response.ok() && typeof body.access_token === "string", `login_failed:${response.status()}`);
  return body;
}

async function apiJson(api, token, method, endpoint, body) {
  const response = await api.fetch(endpoint.replace(/^\/+/, ""), {
    method,
    headers: { Authorization: `Bearer ${token}` },
    data: body,
  });
  const parsed = await response.json().catch(() => null);
  assertCondition(response.ok(), `api_${method.toLowerCase()}_failed:${response.status()}:${endpoint}`);
  return parsed;
}

async function setupPage(browser, auth, label, consoleErrors, requestLog, appUrl) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1200 }, locale: "es-ES" });
  await context.addInitScript(({ accessToken, refreshToken }) => {
    window.localStorage.setItem("viru_token", accessToken);
    if (refreshToken) window.localStorage.setItem("viru_refresh_token", refreshToken);
    window.localStorage.setItem("viru_dashboard_login_required", "false");
    window.localStorage.setItem("viru-theme", "light");
  }, {
    accessToken: auth.access_token ?? auth.accessToken,
    refreshToken: auth.refresh_token ?? auth.refreshToken,
  });
  const page = await context.newPage();
  // The authenticated dashboard emits best-effort UX telemetry. Keep this
  // isolated E2E deterministic and prevent synthetic events from becoming
  // external user references in the disposable demo database.
  await page.route("**/api/v1/ux/events**", (route) => route.fulfill({ status: 204, body: "" }));
  await page.route("**/api/v1/ux/errors**", (route) => route.fulfill({ status: 204, body: "" }));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push({ user: label, message: sanitize(message.text()) });
  });
  page.on("requestfailed", (request) => {
    if (request.url().includes("/api/v1/")) {
      requestLog.push({ user: label, method: request.method(), url: redactUrl(request.url()), failed: true });
    }
  });
  page.on("response", (response) => {
    if (response.url().includes("/api/v1/")) {
      requestLog.push({ user: label, method: response.request().method(), url: redactUrl(response.url()), status: response.status() });
    }
  });
  return { context, page };
}

async function waitForHotelSearch(page) {
  try {
    await page.locator('[data-testid="hotel-city-input"]').waitFor({ state: "visible", timeout: 60_000 });
    await page.locator('[data-testid="hotel-search-submit"]').waitFor({ state: "visible", timeout: 15_000 });
  } catch (error) {
    const diagnostic = await page.evaluate(() => ({
      url: window.location.href,
      title: document.title,
      bodyText: document.body.innerText.slice(0, 800),
    })).catch(() => ({ url: page.url(), title: "", bodyText: "" }));
    throw new Error(`hotel_shell_not_ready:${JSON.stringify(diagnostic)}:${sanitize(error?.message || error)}`);
  }
}

async function searchCity(page, city) {
  const cityInput = page.locator('[data-testid="hotel-city-input"]');
  await cityInput.fill(city);
  const searchResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/v1/hotels/search"
      && response.request().method() === "GET"
      && response.status() === 200,
    { timeout: 60_000 },
  );
  await page.locator('[data-testid="hotel-search-submit"]').click();
  await searchResponse;
  const results = page.locator(".hotel-result-card");
  await results.first().waitFor({ state: "visible", timeout: 60_000 });
  return results;
}

async function runOwnerFlow(page, appUrl) {
  let step = "open";
  const waitForStep = async (promise, name) => {
    step = name;
    try {
      return await promise;
    } catch (error) {
      throw new Error(`owner_${name}:${sanitize(error?.message || error)}`);
    }
  };

  await waitForStep(page.goto(`${appUrl}/hoteles`, { waitUntil: "domcontentloaded", timeout: 60_000 }), "open");
  await waitForStep(waitForHotelSearch(page), "shell");
  const results = await waitForStep(searchCity(page, "Malaga"), "search");
  assertCondition(await results.count() === 1, "owner_expected_one_malaga_result");
  const firstResult = results.first();
  assertCondition((await firstResult.innerText()).includes("Hotel Sol Madrid"), "owner_target_hotel_missing");

  await waitForStep(firstResult.locator(".hotel-result-main").click(), "select");
  // The detail hook requests detail, rates and parity concurrently. The visible
  // rate row is the stable browser contract; waiting on one response can race
  // with the hook's allSettled update even when the API returned 200.
  await waitForStep(page.locator(".hotel-rate-row").first().waitFor({ state: "visible", timeout: 60_000 }), "rate_ui");

  const trackButton = firstResult.getByRole("button", { name: /Seguir precio|Follow price/ });
  assertCondition(await trackButton.count() === 1, "owner_track_button_missing");
  assertCondition(await trackButton.isEnabled(), "owner_track_button_disabled");
  const trackResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/v1/hotels/v2/tracked-offers"
      && response.request().method() === "POST",
    { timeout: 60_000 },
  );
  await waitForStep(trackButton.click(), "track_click");
  const confirmation = page.getByRole("dialog");
  await waitForStep(confirmation.waitFor({ state: "visible", timeout: 60_000 }), "track_confirmation_visible");
  const confirmTracking = confirmation.getByRole("button", { name: /Confirmar seguimiento|Confirm tracking/ });
  assertCondition(await confirmTracking.count() === 1, "owner_track_confirmation_missing");
  await waitForStep(confirmTracking.click(), "track_confirm_click");
  const tracked = await waitForStep(trackResponse, "track_response");
  assertCondition(tracked.status() === 200 || tracked.status() === 201, `owner_track_status_${tracked.status()}`);
  const trackedOffer = page.locator(".hotel-tracked-offer-item").first();
  await waitForStep(trackedOffer.waitFor({ state: "visible", timeout: 60_000 }), "track_ui");

  const pauseButton = trackedOffer.getByRole("button", { name: /Pausar seguimiento|Pause tracking/ });
  assertCondition(await pauseButton.count() === 1, "owner_pause_tracking_missing");
  const pauseResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname.includes("/api/v1/hotels/tracked-offers/")
      && response.request().method() === "PATCH",
    { timeout: 60_000 },
  );
  await waitForStep(pauseButton.click(), "pause_click");
  const paused = await waitForStep(pauseResponse, "pause_response");
  assertCondition(paused.status() === 200, `owner_pause_status_${paused.status()}`);
  const resumeButton = trackedOffer.getByRole("button", { name: /Reanudar seguimiento|Resume tracking/ });
  await waitForStep(resumeButton.waitFor({ state: "visible", timeout: 60_000 }), "resume_visible");
  const resumeResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname.includes("/api/v1/hotels/tracked-offers/")
      && response.request().method() === "PATCH",
    { timeout: 60_000 },
  );
  await waitForStep(resumeButton.click(), "resume_click");
  const resumed = await waitForStep(resumeResponse, "resume_response");
  assertCondition(resumed.status() === 200, `owner_resume_status_${resumed.status()}`);
  const deleteButton = trackedOffer.getByRole("button", { name: /Eliminar seguimiento|Delete tracking/ });
  await waitForStep(deleteButton.click(), "delete_confirmation_open");
  const cancelDelete = trackedOffer.getByRole("button", { name: /Cancelar|Cancel/ });
  await waitForStep(cancelDelete.click(), "delete_confirmation_cancel");

  const watchButton = firstResult.getByRole("button", { name: /Guardar hotel|Save hotel/ });
  assertCondition(await watchButton.count() === 1, "owner_watch_button_missing");
  const watchResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/v1/hotels/watchlist"
      && response.request().method() === "POST",
    { timeout: 60_000 },
  );
  await waitForStep(watchButton.click(), "watch_click");
  const watched = await waitForStep(watchResponse, "watch_response");
  assertCondition(watched.status() === 200, `owner_watch_status_${watched.status()}`);
  await waitForStep(page.locator(".hotel-watchlist-item").filter({ hasText: "Malaga" }).waitFor({ state: "visible", timeout: 60_000 }), "watch_ui");

  const threshold = page.locator('.hotel-alerts-form input[inputmode="decimal"]').first();
  await waitForStep(threshold.fill("120"), "alert_fill");
  const alertResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/v1/hotels/alert-rules"
      && response.request().method() === "POST",
    { timeout: 60_000 },
  );
  await waitForStep(page.getByRole("button", { name: /Crear alerta|Create alert/ }).click(), "alert_click");
  const alerted = await waitForStep(alertResponse, "alert_response");
  assertCondition(alerted.status() === 200, `owner_alert_status_${alerted.status()}`);
  await waitForStep(page.locator(".hotel-alert-rule-item").first().waitFor({ state: "visible", timeout: 60_000 }), "alert_ui");

  await page.screenshot({ path: path.join(outputDir, "owner-flow-light.png"), fullPage: true });
  return {
    targetCity: "Malaga",
    resultCount: await results.count(),
    targetVisible: true,
    trackedOfferVisible: await page.locator(".hotel-tracked-offer-item").count() > 0,
    trackingPauseAndResumeWorked: true,
    trackingDeleteRequiredConfirmation: true,
    watchlistVisible: await page.locator(".hotel-watchlist-item").filter({ hasText: "Malaga" }).count() > 0,
    alertRuleVisible: await page.locator(".hotel-alert-rule-item").count() > 0,
  };
}

async function runObserverIsolation(page, appUrl) {
  await page.goto(`${appUrl}/hoteles`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await waitForHotelSearch(page);
  const observerWatchlist = page.locator(".hotel-watchlist-panel");
  const observerTracked = page.locator(".hotel-tracked-offers-panel");
  await observerWatchlist.waitFor({ state: "visible", timeout: 30_000 });
  await observerTracked.waitFor({ state: "visible", timeout: 30_000 });
  const watchlistBeforeSelection = await observerWatchlist.innerText();
  const trackedBeforeSelection = await observerTracked.innerText();

  const results = await searchCity(page, "Malaga");
  await results.first().locator(".hotel-result-main").click();
  await page.waitForTimeout(700);
  const alertPanel = page.locator(".hotel-alerts-panel");
  await alertPanel.waitFor({ state: "visible", timeout: 30_000 });
  const watchlistAfterSelection = await observerWatchlist.innerText();
  const trackedAfterSelection = await observerTracked.innerText();

  await page.goto(`${appUrl}/notifications`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.locator("#signals-inbox-list").waitFor({ state: "visible", timeout: 60_000 });
  const inboxText = await page.locator("body").innerText();

  await page.screenshot({ path: path.join(outputDir, "observer-isolation-light.png"), fullPage: true });
  return {
    targetAbsentFromWatchlist: !watchlistBeforeSelection.includes("Malaga")
      && !watchlistAfterSelection.includes("Malaga"),
    targetAbsentFromTrackedOffers: !trackedBeforeSelection.includes("Malaga")
      && !trackedAfterSelection.includes("Malaga"),
    targetAlertRulesVisible: await alertPanel.locator(".hotel-alert-rule-item").count(),
    targetAbsentFromInbox: !inboxText.includes("Malaga"),
  };
}

async function runMyHotelsReturn(page, appUrl) {
  await page.goto(`${appUrl}/hoteles?panel=mis-hoteles`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  const panel = page.locator(".hotel-my-hotels-panel");
  await panel.waitFor({ state: "visible", timeout: 60_000 });

  const tracked = panel.locator(".hotel-tracked-offers-panel");
  const saved = panel.locator(".hotel-watchlist-panel");
  const alerts = panel.locator(".hotel-my-hotels-alerts");
  await tracked.waitFor({ state: "visible", timeout: 60_000 });
  await saved.waitFor({ state: "visible", timeout: 60_000 });
  await alerts.waitFor({ state: "visible", timeout: 60_000 });
  const canonicalPanelUrl = new URL(page.url()).searchParams.get("panel") === "mis-hoteles";
  const trackedVisible = await tracked.count() === 1;
  const alertsVisible = await alerts.count() === 1;
  const savedVisible = await saved.count() === 1;

  const explore = panel.getByRole("button", { name: /Explorar hoteles|Explore hotels/ });
  const review = alerts.getByRole("button", { name: /Revisar|Review/ }).first();
  assertCondition(await explore.count() === 1, "my_hotels_explore_action_missing");
  assertCondition(await review.count() === 1, "my_hotels_review_action_missing");
  await page.screenshot({ path: path.join(outputDir, "owner-my-hotels-light.png"), fullPage: true });

  await review.click();
  await page.waitForURL((url) => url.searchParams.get("panel") === "detail", { timeout: 60_000 });
  await page.locator(".hotel-rate-row").first().waitFor({ state: "visible", timeout: 60_000 });
  const reviewOpenedHotel = new URL(page.url()).searchParams.get("panel") === "detail";

  await page.goto(`${appUrl}/hoteles?panel=mis-hoteles`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await panel.waitFor({ state: "visible", timeout: 60_000 });
  await explore.click();
  await page.waitForURL((url) => !url.searchParams.has("panel"), { timeout: 60_000 });
  await waitForHotelSearch(page);
  const exploreReturnedToSearch = new URL(page.url()).searchParams.get("panel") === null;

  return {
    panelVisible: true,
    trackedVisible,
    alertsVisible,
    savedVisible,
    canonicalPanelUrl,
    reviewOpenedHotel,
    exploreReturnedToSearch,
  };
}

async function cleanupCreatedRows(api, token, baseline) {
  const currentAlerts = await apiJson(api, token, "GET", "/hotels/alert-rules");
  const currentTracked = await apiJson(api, token, "GET", "/hotels/tracked-offers");
  const currentWatchlist = await apiJson(api, token, "GET", "/hotels/watchlist");
  const baselineIds = (rows) => new Set(rows.map((row) => row.id));
  const removed = { alerts: 0, trackedOffers: 0, watchlist: 0 };

  for (const row of currentAlerts.filter((item) => !baselineIds(baseline.alerts).has(item.id))) {
    await apiJson(api, token, "DELETE", `/hotels/alert-rules/${row.id}`);
    removed.alerts += 1;
  }
  for (const row of currentTracked.filter((item) => !baselineIds(baseline.tracked).has(item.id))) {
    await apiJson(api, token, "DELETE", `/hotels/tracked-offers/${row.id}`);
    removed.trackedOffers += 1;
  }
  for (const row of currentWatchlist.filter((item) => !baselineIds(baseline.watchlist).has(item.id))) {
    await apiJson(api, token, "DELETE", `/hotels/watchlist/${row.id}`);
    removed.watchlist += 1;
  }
  return removed;
}

async function writeBlockedReport(failure, extra = {}) {
  const report = {
    result: "blocked",
    runner: "qa_hotels_h44_browser",
    dataset_id: datasetId,
    app_env: "local_fixture",
    db_isolation_kind: "sqlite_temp_workspace",
    provider_mode: "mock",
    external_calls_expected: 0,
    external_calls_observed: null,
    external_calls_observation: "not_observed",
    privacy: { status: "passed", violations: [] },
    cleanup: { temporary_database_removed: false, reset: "not_started" },
    ...extra,
    failure: sanitize(failure),
  };
  await mkdir(outputDir, { recursive: true });
  const reportPath = path.join(outputDir, "report.json");
  const serialized = JSON.stringify(report);
  if (/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/.test(serialized) || /(?:authorization|bearer|password|secret|api[_-]?key)\s*[:=]/i.test(serialized)) {
    report.privacy = { status: "failed", violations: ["credential-marker"] };
  }
  await import("node:fs/promises").then(({ writeFile }) => writeFile(reportPath, `${JSON.stringify(report, null, 2)}\\n`, "utf8"));
  console.log(`H44 browser report: ${path.relative(repoRoot, reportPath)}`);
}

async function main() {
  let profileMetadata = null;
  await mkdir(outputDir, { recursive: true });
  try {
    profileMetadata = await loadProfileManifest();
  } catch (error) {
    await writeBlockedReport(sanitize(error?.message || error), { fault_profile: faultProfile });
    process.exitCode = 1;
    return;
  }
  if (faultProfile !== "happy_path") {
    await writeBlockedReport("browser_runner_supports_happy_path_only", {
      fault_profile: faultProfile,
      fault_profile_manifest_version: profileMetadata.manifestVersion,
      fault_profile_expected_status: profileMetadata.profile.expected_status,
      fault_profile_expected_external_calls: profileMetadata.profile.expected_external_calls,
    });
    process.exitCode = 1;
    return;
  }
  const configuredFrontend = configuredBaseUrl ? new URL(configuredBaseUrl) : null;
  const configuredBackend = configuredApiBaseUrl ? new URL(configuredApiBaseUrl) : null;
  const frontendPort = configuredFrontend?.port ? Number(configuredFrontend.port) : await reservePort();
  const backendPort = configuredBackend?.port ? Number(configuredBackend.port) : await reservePort();
  const effectiveBaseUrl = configuredFrontend?.origin || `http://127.0.0.1:${frontendPort}`;
  const effectiveApiBase = configuredBackend?.origin
    ? `${configuredBackend.origin}${configuredBackend.pathname.replace(/\/$/, "")}`
    : `http://127.0.0.1:${backendPort}/api/v1`;
  const dbPath = path.join(os.tmpdir(), `viru-h44-browser-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.db`);
  const dbUrl = dbUrlFor(dbPath);
  const report = {
    result: "blocked",
    runner: "qa_hotels_h44_browser",
    dataset_id: datasetId,
    fault_profile: faultProfile,
    fault_profile_manifest_version: profileMetadata.manifestVersion,
    fault_profile_expected_status: profileMetadata.profile.expected_status,
    fault_profile_expected_external_calls: profileMetadata.profile.expected_external_calls,
    app_env: "local_fixture",
    db_isolation_kind: "sqlite_temp_workspace",
    provider_mode: "mock",
    external_calls_expected: 0,
    external_calls_observed: null,
    external_calls_observation: "seed_observed;mock_api_provider;browser_telemetry_intercepted;api_egress_not_observed",
    user_scope: "synthetic_demo_users_only",
    browser_engine: "chromium",
    base_url: redactUrl(effectiveBaseUrl),
    api_base: redactUrl(effectiveApiBase),
    scenarios: {},
    cleanup: { rows_deleted: {}, reset: "pending", temporary_database_removed: false },
    privacy: { status: "pending", violations: [] },
    console_errors: [],
    request_failures: [],
  };
  let backendProcess = null;
  let frontendProcess = null;
  let browser = null;
  let api = null;
  let ownerContext = null;
  let observerContext = null;
  let dbSeeded = false;
  let baselineOwner = null;
  let ownerAuth = null;

  try {
    const seedReport = await seedDatabase(dbUrl);
    dbSeeded = true;
    report.seed = {
      rows_by_table: seedReport.rows_by_table,
      external_calls_observed: seedReport.external_calls_observed,
    };

    const serverEnv = demoEnvironment(dbUrl, { profile: faultProfile });
    backendProcess = startProcess(
      pythonCommand,
      ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(backendPort)],
      { cwd: backendRoot, env: serverEnv },
    );
    await waitForHttp(`http://127.0.0.1:${backendPort}/health`);

    frontendProcess = startProcess(
      process.execPath,
      [path.join(frontendRoot, "scripts", "dev-server.mjs"), "--hostname", "127.0.0.1", "--port", String(frontendPort)],
      {
        cwd: frontendRoot,
        env: {
          ...process.env,
          NEXT_PUBLIC_API_URL: effectiveApiBase,
          NEXT_PUBLIC_LOCAL_API_ORIGIN: `http://127.0.0.1:${backendPort}`,
          VIRU_ROUTE_WARMUP: "0",
          NEXT_DIST_DIR: `.next-h44-${frontendPort}`,
        },
      },
    );
    await waitForHttp(`${effectiveBaseUrl}/hoteles`);

    api = await request.newContext({ baseURL: `${effectiveApiBase.replace(/\/$/, "")}/` });
    ownerAuth = await login(api, demoUsers.owner);
    const observerAuth = await login(api, demoUsers.observer);
    baselineOwner = {
      alerts: await apiJson(api, ownerAuth.access_token, "GET", "/hotels/alert-rules"),
      tracked: await apiJson(api, ownerAuth.access_token, "GET", "/hotels/tracked-offers"),
      watchlist: await apiJson(api, ownerAuth.access_token, "GET", "/hotels/watchlist"),
    };

    browser = await chromium.launch({ headless: true });
    const consoleErrors = [];
    const requestLog = [];
      ownerContext = await setupPage(browser, ownerAuth, "owner", consoleErrors, requestLog, effectiveBaseUrl);
    observerContext = await setupPage(browser, observerAuth, "observer", consoleErrors, requestLog, effectiveBaseUrl);
    report.scenarios.owner = await runOwnerFlow(ownerContext.page, effectiveBaseUrl);
    report.scenarios.owner_my_hotels = await runMyHotelsReturn(ownerContext.page, effectiveBaseUrl);
    report.scenarios.observer_isolation = await runObserverIsolation(observerContext.page, effectiveBaseUrl);
    report.console_errors = consoleErrors;
    report.request_failures = requestLog.filter((item) => item.failed);

    assertCondition(report.scenarios.owner.targetVisible, "owner_target_not_visible");
    assertCondition(report.scenarios.owner.trackedOfferVisible, "owner_tracking_not_visible");
    assertCondition(report.scenarios.owner.trackingPauseAndResumeWorked, "owner_tracking_pause_resume_failed");
    assertCondition(report.scenarios.owner.trackingDeleteRequiredConfirmation, "owner_tracking_delete_confirmation_failed");
    assertCondition(report.scenarios.owner.watchlistVisible, "owner_watchlist_not_visible");
    assertCondition(report.scenarios.owner.alertRuleVisible, "owner_alert_not_visible");
    assertCondition(report.scenarios.owner_my_hotels.panelVisible, "my_hotels_panel_not_visible");
    assertCondition(report.scenarios.owner_my_hotels.trackedVisible, "my_hotels_tracking_not_visible");
    assertCondition(report.scenarios.owner_my_hotels.alertsVisible, "my_hotels_alerts_not_visible");
    assertCondition(report.scenarios.owner_my_hotels.savedVisible, "my_hotels_saved_not_visible");
    assertCondition(report.scenarios.owner_my_hotels.canonicalPanelUrl, "my_hotels_url_not_canonical");
    assertCondition(report.scenarios.owner_my_hotels.reviewOpenedHotel, "my_hotels_review_did_not_open_hotel");
    assertCondition(report.scenarios.owner_my_hotels.exploreReturnedToSearch, "my_hotels_explore_did_not_return_to_search");
    assertCondition(report.scenarios.observer_isolation.targetAbsentFromWatchlist, "observer_watchlist_leak");
    assertCondition(report.scenarios.observer_isolation.targetAbsentFromTrackedOffers, "observer_tracking_leak");
    assertCondition(report.scenarios.observer_isolation.targetAlertRulesVisible === 0, "observer_alert_rule_leak");
    assertCondition(report.scenarios.observer_isolation.targetAbsentFromInbox, "observer_inbox_leak");
    assertCondition(report.console_errors.length === 0, "browser_console_errors");
    assertCondition(report.request_failures.length === 0, "browser_request_failures");

    report.result = "passed";
  } catch (error) {
    report.failure = sanitize(error?.message || error);
    report.process_logs = {
      backend: sanitizeProcessLogs(backendProcess?.getLogs?.()),
      frontend: sanitizeProcessLogs(frontendProcess?.getLogs?.()),
    };
  } finally {
    if (ownerContext) await ownerContext.context.close().catch(() => undefined);
    if (observerContext) await observerContext.context.close().catch(() => undefined);
    if (browser) await browser.close().catch(() => undefined);
    if (api && ownerAuth && baselineOwner) {
      try {
        report.cleanup.rows_deleted = await cleanupCreatedRows(api, ownerAuth.access_token, baselineOwner);
      } catch (error) {
        report.cleanup.cleanup_error = sanitize(error?.message || error);
      }
    }
    if (api) await api.dispose().catch(() => undefined);
    await stopProcess(frontendProcess);
    await stopProcess(backendProcess);
    if (dbSeeded) {
      try {
        const resetReport = await resetDatabase(dbUrl);
        report.cleanup.reset = resetReport.result;
      } catch (error) {
        report.cleanup.reset = "failed";
        report.cleanup.reset_error = sanitize(error?.message || error);
      }
    }
    const cleanupPaths = [dbPath, `${dbPath}.h44-demo.json`, `${dbPath}-wal`, `${dbPath}-shm`, `${dbPath}-journal`];
    for (const cleanupPath of cleanupPaths) await unlink(cleanupPath).catch(() => undefined);
    const remainingPaths = [];
    for (const cleanupPath of cleanupPaths) {
      try {
        await import("node:fs/promises").then(({ access }) => access(cleanupPath));
        remainingPaths.push(cleanupPath);
      } catch (error) {
        if (error?.code !== "ENOENT") remainingPaths.push(cleanupPath);
      }
    }
    report.cleanup.temporary_database_removed = remainingPaths.length === 0;
    if (remainingPaths.length > 0) report.cleanup.remaining_paths = remainingPaths.map((item) => path.basename(item));
  }

  if (report.result === "passed" && report.cleanup.reset !== "passed") {
    report.result = "blocked";
    report.failure = report.cleanup.reset_error || "database_reset_failed";
  }
  if (report.result === "passed" && !report.cleanup.temporary_database_removed) {
    report.result = "blocked";
    report.failure = report.failure || "temporary_database_cleanup_failed";
  }

  const serialized = JSON.stringify(report);
  const privacyViolations = [];
  if (/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/.test(serialized)) privacyViolations.push("jwt-marker");
  if (/(?:authorization|bearer|password|secret|api[_-]?key)\s*[:=]/i.test(serialized)) privacyViolations.push("credential-marker");
  if (/[?&](?:token|password|secret|access_token|api[_-]?key)=/i.test(serialized)) privacyViolations.push("sensitive-query-marker");
  if (/\b[\w.+-]+@[\w.-]+\.[A-Z]{2,}\b/i.test(serialized)) privacyViolations.push("email-marker");
  if (privacyViolations.length > 0) {
    report.result = "blocked";
    report.failure = `privacy_validation_failed:${privacyViolations.join(",")}`;
  }
  report.privacy = { status: privacyViolations.length === 0 ? "passed" : "failed", violations: privacyViolations };
  await mkdir(outputDir, { recursive: true });
  await import("node:fs/promises").then(({ writeFile }) => writeFile(
    path.join(outputDir, "report.json"),
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8",
  ));
  console.log(`H44 browser report: ${path.relative(repoRoot, path.join(outputDir, "report.json"))}`);
  if (report.result !== "passed" || report.cleanup.reset !== "passed" || report.privacy.status !== "passed") process.exitCode = 1;
}

await main();
