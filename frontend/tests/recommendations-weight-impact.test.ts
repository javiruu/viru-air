import assert from "node:assert/strict";
import test from "node:test";

import {
  getWeightImpactLines,
  getWeightPrioritySummary,
} from "../src/modules/recommendations/weightImpact";

test("getWeightImpactLines computes deltas against baseline", () => {
  const lines = getWeightImpactLines({
    price: 0.5,
    speed: 0.2,
    climate: 0.1,
    trend: 0.1,
    novelty: 0.1,
  });
  const byKey = Object.fromEntries(lines.map((line) => [line.key, line.deltaPoints]));
  assert.equal(byKey.price, 10);
  assert.equal(byKey.climate, -10);
});

test("getWeightPrioritySummary computes relative priority", () => {
  const summary = getWeightPrioritySummary({
    price: 0.4,
    speed: 0.2,
    climate: 0.25,
    trend: 0.1,
    novelty: 0.05,
  });
  assert.ok(summary);
  assert.equal(summary?.primary, "price");
  assert.equal(summary?.secondary, "climate");
  assert.equal(summary?.percentMore, 60);
});
