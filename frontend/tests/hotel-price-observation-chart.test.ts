import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import { buildHotelPriceObservationChart } from "../src/modules/hotels/components/hotelPriceObservationChart";

test("hotel price chart only visualizes eligible total-price observations", () => {
  const chart = buildHotelPriceObservationChart(
    [
      { id: "excluded", observedAt: "2026-08-03T10:00:00Z", amount: 91, eligible: false, totalPrice: true },
      { id: "unknown", observedAt: "2026-08-02T10:00:00Z", amount: 94, eligible: true, totalPrice: false },
      { id: "valid-later", observedAt: "2026-08-04T10:00:00Z", amount: 108, eligible: true, totalPrice: true },
      { id: "valid-earlier", observedAt: "2026-08-01T10:00:00Z", amount: 101, eligible: true, totalPrice: true },
      { id: "missing", observedAt: "2026-08-05T10:00:00Z", amount: null, eligible: true, totalPrice: true },
    ],
    false,
  );

  assert.deepEqual(chart.points.map((point) => point.id), ["valid-earlier", "valid-later"]);
  assert.equal(chart.hasContinuousLine, false);
  assert.equal(chart.minAmount, 101);
  assert.equal(chart.maxAmount, 108);
});

test("hotel price chart joins only consecutive complete observations", () => {
  const chart = buildHotelPriceObservationChart(
    [
      { id: "first", observedAt: "2026-08-01T10:00:00Z", amount: 101, eligible: true, totalPrice: true },
      { id: "second", observedAt: "2026-08-02T10:00:00Z", amount: 98, eligible: true, totalPrice: true },
      { id: "third", observedAt: "2026-08-03T10:00:00Z", amount: 95, eligible: true, totalPrice: true },
    ],
    true,
  );

  assert.equal(chart.hasContinuousLine, true);
  assert.equal(chart.points.length, 3);
  assert.ok(chart.points[0].x < chart.points[1].x);
  assert.ok(chart.points[1].x < chart.points[2].x);
});

test("tracked-offer observations require backend gap detection before joining points", () => {
  const source = fs.readFileSync(
    path.resolve(__dirname, "../src/modules/hotels/components/HotelTrackedOfferSnapshots.tsx"),
    "utf8",
  );

  assert.match(source, /history\.capabilities\.gap_detection === "supported"/);
});
