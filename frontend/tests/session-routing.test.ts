import assert from "node:assert/strict";
import test from "node:test";

import {
  buildLoginRedirect,
  resolvePostAuthUrl,
  sanitizeReturnUrl,
} from "../src/modules/shared/navigation";
import { resolveBridgeRoute } from "../src/modules/shared/routeBridges";

test("sanitizeReturnUrl accepts internal relative paths", () => {
  assert.equal(sanitizeReturnUrl("/alerts?tab=events"), "/alerts?tab=events");
});

test("sanitizeReturnUrl rejects open redirects", () => {
  assert.equal(sanitizeReturnUrl("https://evil.example"), "/dashboard");
  assert.equal(sanitizeReturnUrl("//evil.example"), "/dashboard");
});

test("buildLoginRedirect preserves encoded returnUrl", () => {
  assert.equal(buildLoginRedirect("/watchlist?month=2026-04"), "/login?returnUrl=%2Fwatchlist%3Fmonth%3D2026-04");
});

test("resolvePostAuthUrl uses safe fallback", () => {
  assert.equal(resolvePostAuthUrl(null), "/dashboard");
  assert.equal(resolvePostAuthUrl("/quick-search"), "/quick-search");
});

test("route bridges map legacy paths", () => {
  assert.equal(resolveBridgeRoute("/history"), "/watchlist");
  assert.equal(resolveBridgeRoute("/preferences"), "/preferencias");
  assert.equal(resolveBridgeRoute("/suggestions"), "/soporte/feedback?type=idea");
  assert.equal(resolveBridgeRoute("/dashboard"), "/dashboard");
});
