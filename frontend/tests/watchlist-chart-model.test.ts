import assert from "node:assert/strict";
import test from "node:test";

import { t } from "../src/i18n";
import { buildWatchlistChartModel } from "../src/modules/watchlist/chartModel";
import type { HistoryRow } from "../src/modules/watchlist/types";

const chartPad = { left: 34, right: 30, top: 28, bottom: 34 };

function historyRow(capturedAt: string, price: number): HistoryRow {
  return {
    watchId: "watch-agp-tsf",
    origin: "AGP",
    destination: "TSF",
    travelDate: "2026-07-15",
    capturedAt,
    price,
    currency: "EUR",
    departureTime: null,
    provider: "ryanair",
  };
}

test("watchlist chart model keeps abrupt price changes inside the plot area", () => {
  const model = buildWatchlistChartModel({
    groupedByDate: {
      "2026-07-15": [
        historyRow("2026-07-01T08:00:00.000Z", 45.95),
        historyRow("2026-07-02T08:00:00.000Z", 43.95),
        historyRow("2026-07-03T08:00:00.000Z", 47.1),
        historyRow("2026-07-04T08:00:00.000Z", 138.4),
      ],
    },
    selectedDates: ["2026-07-15"],
    chartHeight: 260,
    chartWidth: 720,
    chartPad,
    lineColors: ["#D95D39"],
  });

  assert.ok(model);
  const points = model[0]?.points ?? [];
  assert.equal(points.length, 4);
  assert.ok(points.every((point) => point.y > chartPad.top));
  assert.ok(points.every((point) => point.y < 260 - chartPad.bottom));
  assert.ok(model[0]?.areaPoints.includes("226"));
});

test("watchlist provider coverage keys resolve in both locales", () => {
  const keys = [
    "watchlist.providerCoverage.kicker",
    "watchlist.providerCoverage.heading",
    "watchlist.providerCoverage.summary",
    "watchlist.providerCoverage.observed",
    "watchlist.providerCoverage.latest",
    "watchlist.providerCoverage.ready",
    "watchlist.providerCoverage.readyDetail",
  ];

  keys.forEach((key) => {
    assert.notEqual(t("es", key, { count: 2, observed: 1, total: 5, value: "hace 2 horas" }), key);
    assert.notEqual(t("en", key, { count: 2, observed: 1, total: 5, value: "2 hours ago" }), key);
  });
});
