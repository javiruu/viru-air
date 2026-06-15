import assert from "node:assert/strict";
import test from "node:test";

import { getQuickSearchFreshnessPresentation } from "../src/modules/quick-search/freshnessPresentation";

const FIXED_NOW = Date.parse("2026-06-01T09:00:00Z");

test("getQuickSearchFreshnessPresentation renders fresh copy with relative time", () => {
  const freshness = getQuickSearchFreshnessPresentation({
    freshness: {
      status: "fresh",
      observed_at: "2026-06-01T08:56:00Z",
    },
    now: FIXED_NOW,
  });

  assert.equal(freshness.label, "Precio verificado hace 4 min");
  assert.equal(freshness.shortLabel, "Verificado 4 min");
  assert.equal(freshness.tone, "fresh");
});

test("getQuickSearchFreshnessPresentation renders warm copy", () => {
  const freshness = getQuickSearchFreshnessPresentation({
    freshness: {
      status: "warm",
      observed_at: "2026-06-01T08:22:00Z",
    },
    now: FIXED_NOW,
  });

  assert.equal(freshness.label, "Visto hace 38 min. Revalida antes de decidir.");
  assert.equal(freshness.shortLabel, "Visto 38 min");
  assert.equal(freshness.tone, "warn");
});

test("getQuickSearchFreshnessPresentation renders stale and provider fallback states", () => {
  const stale = getQuickSearchFreshnessPresentation({
    freshness: { status: "stale" },
    now: FIXED_NOW,
  });
  const providerFallback = getQuickSearchFreshnessPresentation({
    freshness: {
      status: "provider_error_fresh",
      observed_at: "2026-06-01T08:50:00Z",
    },
    now: FIXED_NOW,
  });

  assert.equal(stale.label, "Precio historico. Puede haber cambiado.");
  assert.equal(stale.isStaleLike, true);
  assert.equal(providerFallback.label, "Proveedor sin respuesta. Conservamos la ultima senal.");
  assert.equal(providerFallback.tone, "warn");
});
