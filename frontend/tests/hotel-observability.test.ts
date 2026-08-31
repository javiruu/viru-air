import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {
  buildHotelObservabilityPath,
  buildHotelObservabilitySummary,
  getHotelCircuitTone,
  getHotelHealthTone,
  getHotelLeaseTone,
  getHotelMetricBarWidth,
  getHotelRunTone,
  getHotelOutcomesForMetric,
} from "../src/modules/admin/hotelObservability";

const PAGE = path.join(process.cwd(), "src", "app", "(private)", "admin", "hotels-observability", "page.tsx");

test("hotel observability builds bounded admin query parameters", () => {
  assert.equal(
    buildHotelObservabilityPath({ days: 31, provider: "local", metricName: "hotel_delivery", outcome: "retried" }),
    "/admin/hotels/observability?days=31&provider=local&metric_name=hotel_delivery&outcome=retried",
  );
});

test("hotel observability summary aggregates rows without private dimensions", () => {
  const summary = buildHotelObservabilitySummary([
    { metric_date: "2026-08-09", metric_name: "sweep_run", provider: "local", outcome: "completed", count: 4, updated_at: "2026-08-09T10:00:00" },
    { metric_date: "2026-08-09", metric_name: "hotel_delivery", provider: "local", outcome: "retried", count: 2, updated_at: "2026-08-09T10:00:00" },
    { metric_date: "2026-08-08", metric_name: "hotel_delivery", provider: "mock", outcome: "failed", count: 1, updated_at: "2026-08-08T10:00:00" },
  ]);

  assert.deepEqual(summary, {
    total: 7,
    dates: 2,
    providers: 2,
    metricNames: 2,
    latestDate: "2026-08-09",
    attentionCount: 3,
  });
});

test("hotel observability outcomes follow the selected metric", () => {
  assert.deepEqual(getHotelOutcomesForMetric("alert_event"), ["created"]);
  assert.deepEqual(getHotelOutcomesForMetric("hotel_delivery"), ["delivered", "retried", "failed"]);
});

test("hotel health keeps observed states distinct from optimistic success", () => {
  assert.equal(getHotelHealthTone("ok"), "success");
  assert.equal(getHotelHealthTone("degraded"), "warning");
  assert.equal(getHotelHealthTone("not_configured"), "warning");
  assert.equal(getHotelHealthTone("critical"), "error");
  assert.equal(getHotelHealthTone("unknown"), "info");
});

test("hotel run diagnostics map statuses to safe tones", () => {
  assert.equal(getHotelRunTone("completed"), "success");
  assert.equal(getHotelRunTone("partial"), "warning");
  assert.equal(getHotelRunTone("failed"), "error");
  assert.equal(getHotelRunTone("unknown"), "info");
});

test("hotel lease states map to honest tones", () => {
  assert.equal(getHotelLeaseTone("done"), "success");
  assert.equal(getHotelLeaseTone("expired"), "warning");
  assert.equal(getHotelLeaseTone("failed"), "error");
  assert.equal(getHotelLeaseTone("unknown"), "info");
});

test("hotel provider controls map circuit states to safe tones", () => {
  assert.equal(getHotelCircuitTone("closed"), "success");
  assert.equal(getHotelCircuitTone("open"), "error");
  assert.equal(getHotelCircuitTone("half_open"), "warning");
  assert.equal(getHotelCircuitTone("unknown"), "info");
});

test("hotel observability bars remain bounded and the page exposes semantic table states", () => {
  assert.equal(getHotelMetricBarWidth(2, 4), 50);
  assert.equal(getHotelMetricBarWidth(0, 4), 0);
  assert.equal(getHotelMetricBarWidth(100, 0), 0);

  const source = fs.readFileSync(PAGE, "utf8");
  assert.match(source, /<table className="hotel-observability-table" aria-busy=\{loading\}>/);
  assert.match(source, /role="alert"/);
  assert.match(source, /admin\.hotelObservability\.footnote/);
  assert.match(source, /requestVersion/);
  assert.match(source, /mounted\.current/);
  assert.match(source, /hotel-observability-auth-error/);
  assert.match(source, /admin\/hotels\/health/);
  assert.match(source, /admin\/hotels\/runs/);
  assert.match(source, /admin\/hotels\/provider-controls/);
  assert.match(source, /admin\/hotels\/sweep-leases/);
  assert.match(source, /admin\/hotels\/provider-outcomes/);
  assert.match(source, /outcomesTitle/);
  assert.match(source, /providerOutcome/);
  assert.match(source, /leasesTitle/);
  assert.match(source, /controlsTitle/);
  assert.match(source, /runsTitle/);
  assert.match(source, /healthTitle/);
  assert.match(source, /setAuthAttempt/);
  assert.doesNotMatch(source, /user_id|hotel_id|email/);
});
