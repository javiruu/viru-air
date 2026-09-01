import assert from "node:assert/strict";
import test from "node:test";

import { getHeroOpportunityMetrics } from "@/modules/dashboard/hero-opportunity-metrics";

test("dashboard hero exposes the latest snapshot price and its historical delta", () => {
  const metrics = getHeroOpportunityMetrics(
    { latest_snapshot: { raw_price: 64.5, raw_currency: "EUR" } },
    { latest_price: 64.5, delta_pct: -12.34 },
  );

  assert.deepEqual(metrics, { latestPrice: 64.5, currency: "EUR", deltaPct: -12.34 });
});

test("dashboard hero keeps data unavailable only when the API has no observation", () => {
  const metrics = getHeroOpportunityMetrics(null, { latest_price: null, delta_pct: null });

  assert.deepEqual(metrics, { latestPrice: null, currency: null, deltaPct: null });
});
