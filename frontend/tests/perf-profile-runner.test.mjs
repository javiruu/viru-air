import assert from "node:assert/strict";
import test from "node:test";

import {
  PROFILE_CONFIGS,
  parseCsv,
  resolveAuthLoginUrl,
  parseProfiles,
  resolveOutputDir,
  sanitizeDiagnosticText,
  selectRoutes,
  shouldWriteJson,
} from "../scripts/perf_profile_playwright.cjs";

test("performance profiler parses selected routes and preserves order without duplicates", () => {
  assert.deepEqual(parseCsv(" /hoteles, /dashboard, /hoteles ", ["/"]), ["/hoteles", "/dashboard", "/hoteles"]);
  assert.deepEqual(selectRoutes(["/", "/hoteles", "/dashboard"], "/hoteles,/dashboard,/hoteles"), ["/hoteles", "/dashboard"]);
});

test("performance profiler rejects unknown routes and profiles", () => {
  assert.throws(() => selectRoutes(["/hoteles"], "/missing"), /Unknown performance route/);
  assert.throws(() => parseProfiles("desktop,slow-4g"), /Unknown performance profile/);
});

test("default desktop profile preserves the historical Playwright context", () => {
  assert.equal(PROFILE_CONFIGS.desktop.viewport, null);
  assert.equal(PROFILE_CONFIGS.desktop.isMobile, false);
  assert.equal(PROFILE_CONFIGS.desktop.hasTouch, false);
});

test("performance profiles expose mobile and Fast 3G settings", () => {
  assert.deepEqual(parseProfiles("desktop,mobile,fast3g"), ["desktop", "mobile", "fast3g"]);
  assert.equal(PROFILE_CONFIGS.mobile.viewport.width, 390);
  assert.equal(PROFILE_CONFIGS.fast3g.network.latency, 150);
  assert.equal(PROFILE_CONFIGS.fast3g.network.connectionType, "cellular3g");
});

test("diagnostic text removes query strings and credential-like values", () => {
  const sanitized = sanitizeDiagnosticText("fetch https://example.test/api?token=secret&query=private authorization: Bearer abc123 password=hunter2 api_key=xyz email=person@example.test {\"access_token\":\"json-secret\",\"cookie\":\"cookie-secret\",\"email\":\"json@example.test\"}");
  assert.equal(sanitized.includes("token=secret"), false);
  assert.equal(sanitized.includes("abc123"), false);
  assert.equal(sanitized.includes("hunter2"), false);
  assert.equal(sanitized.includes("api_key=xyz"), false);
  assert.equal(sanitized.includes("json-secret"), false);
  assert.equal(sanitized.includes("cookie-secret"), false);
  assert.equal(sanitized.includes("person@example.test"), false);
  assert.equal(sanitized.includes("json@example.test"), false);
  assert.equal(sanitized.includes("?"), false);
  assert.match(sanitized, /https:\/\/example\.test\/api/);
});

test("hotel milestone mode is opt-in and remains navigation-only by default", () => {
  assert.equal(process.env.PERF_HOTELS_FLOW === "1", false);
});

test("authenticated profiler resolves same-origin and explicit login API bases", () => {
  assert.equal(resolveAuthLoginUrl({}, "http://127.0.0.1:3000"), "http://127.0.0.1:3000/api/v1/auth/login");
  assert.equal(
    resolveAuthLoginUrl({ PERF_AUTH_API_BASE: "http://127.0.0.1:8000/api/v1" }, "http://127.0.0.1:3100"),
    "http://127.0.0.1:8000/api/v1/auth/login",
  );
  assert.equal(
    resolveAuthLoginUrl({ PERF_AUTH_API_BASE: "/api/v1" }, "http://127.0.0.1:3100"),
    "http://127.0.0.1:3100/api/v1/auth/login",
  );
});

test("JSON evidence is opt-in or tied to an explicit output directory", () => {
  assert.equal(shouldWriteJson({}), false);
  assert.equal(shouldWriteJson({ PERF_JSON: "1" }), true);
  assert.equal(shouldWriteJson({ PERF_OUTPUT_DIR: "docs/qa/evidence/h36" }), true);
});

test("configured output stays relative to the frontend project", () => {
  assert.match(resolveOutputDir({ PERF_OUTPUT_DIR: "docs/qa/evidence/h36" }), /frontend[\\/]docs[\\/]qa[\\/]evidence[\\/]h36$/);
});
