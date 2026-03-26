import assert from "node:assert/strict";
import test from "node:test";

import { buildRankingReasons } from "../src/modules/recommendations/rankingExplainers";

test("buildRankingReasons returns positive reasons for cheap and downward trend", () => {
  const reasons = buildRankingReasons({
    price: 45,
    avg_price: 60,
    trend: "down",
    weather: { precip_probability: 20 },
  });
  assert.equal(reasons.length, 3);
  assert.equal(reasons[0]?.key, "recommendations.reasons.priceBelowAvg");
  assert.equal(reasons[1]?.key, "recommendations.reasons.trendDown");
  assert.equal(reasons[2]?.key, "recommendations.reasons.weatherStable");
});

test("buildRankingReasons returns negative reasons for expensive unstable options", () => {
  const reasons = buildRankingReasons({
    price: 80,
    avg_price: 60,
    trend: "up",
    weather: { precip_probability: 70 },
  });
  assert.equal(reasons[0]?.key, "recommendations.reasons.priceAboveAvg");
  assert.equal(reasons[1]?.key, "recommendations.reasons.trendUp");
  assert.equal(reasons[2]?.key, "recommendations.reasons.weatherUnstable");
});
