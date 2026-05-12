import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { getQuickSearchVisualState } from "../src/modules/quick-search/state/getQuickSearchVisualState";
import { useQuickSearchScreenState } from "../src/modules/quick-search/state/useQuickSearchScreenState";
import type { SearchResult } from "../src/modules/quick-search/types";

function renderScreenState(overrides: Partial<Parameters<typeof useQuickSearchScreenState>[0]> = {}) {
  let snapshot: ReturnType<typeof useQuickSearchScreenState> | undefined;

  function Harness() {
    snapshot = useQuickSearchScreenState({
      results: [],
      priceMin: "",
      priceMax: "",
      durationMax: "",
      riskFilter: "all",
      sortBy: "ranking",
      showHighRisk: false,
      filtersNotice: [],
      filtersWarningCodes: [],
      filtersMeta: null,
      isDegraded: false,
      searchMeta: null,
      weatherMessage: "",
      strictFilters: false,
      includeStops: true,
      radiusActive: true,
      radiusKm: 150,
      excludeOriginsCount: 0,
      excludeDestinationsCount: 0,
      departAfter: "07:00",
      departBefore: "22:00",
      daysBefore: 1,
      daysAfter: 1,
      emptyCausesExpanded: false,
      t: ((key: string) => key) as Parameters<typeof useQuickSearchScreenState>[0]["t"],
      tWarn: (key: string) => key,
      ...overrides,
    });
    return null;
  }

  renderToStaticMarkup(<Harness />);
  assert.ok(snapshot);
  return snapshot;
}

function buildResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return {
    origin: "MAD",
    destination: "DUB",
    travel_date: "2026-05-12",
    departure_time_local: "09:30",
    price: 49,
    price_total: 49,
    currency: "EUR",
    source: "ryanair",
    duration_total: 120,
    duration_total_min: 120,
    risk_label: "low",
    ranking_score: 0.91,
    stale_data: false,
    itinerary_type: "direct",
    legs: [],
    ...overrides,
  };
}

test("useQuickSearchScreenState exposes degraded state, groups warnings and hides high-risk results by default", () => {
  const state = renderScreenState({
    results: [
      buildResult({ result_id: "low-1", risk_label: "low", ranking_score: 0.9 }),
      buildResult({ result_id: "high-1", destination: "LIS", risk_label: "high", ranking_score: 0.95 }),
    ],
    filtersWarningCodes: ["ryanair_unavailable_partial", "provider_error_partial", "ryanair_provider_unavailable_total"],
    searchMeta: { stale_data: true },
  });

  assert.equal(state.showDegradedState, true);
  assert.equal(state.visibleResults.length, 1);
  assert.equal(state.visibleResults[0]?.result_id, "low-1");
  assert.equal(state.hiddenHighRiskResults.length, 1);
  assert.deepEqual(state.groupedNeutralWarnings, [
    { message: "ryanair_unavailable_partial", count: 1 },
    { message: "provider_error_partial", count: 1 },
  ]);
  assert.deepEqual(state.groupedCriticalWarnings, [{ message: "ryanair_provider_unavailable_total", count: 1 }]);
  assert.equal(state.infoItemsCount, 3);
});

test("useQuickSearchScreenState prioritizes provider outage copy when no results can be confirmed", () => {
  const state = renderScreenState({
    filtersWarningCodes: ["ryanair_provider_unavailable_total"],
  });

  assert.equal(state.emptyStateMainTitle, "emptyStateProviderTitle");
  assert.deepEqual(state.zeroResultCauses, ["emptyCauseProvider"]);
  assert.deepEqual(state.zeroResultActions, []);
});

test("useQuickSearchScreenState surfaces partial provider outage without hiding relax options", () => {
  const state = renderScreenState({
    filtersWarningCodes: ["ryanair_availability_failed_partial"],
    strictFilters: true,
    durationMax: "180",
  });

  assert.equal(state.showDegradedState, true);
  assert.equal(state.emptyStateMainTitle, "emptyStateProviderPartialTitle");
  assert.equal(state.zeroResultCauses[0], "emptyCauseProvider");
  assert.deepEqual(
    state.zeroResultActions.map((action) => action.id),
    ["disable_strict", "increase_duration"],
  );
});

test("useQuickSearchScreenState exposes contextual inline partial notice from provider_status", () => {
  const state = renderScreenState({
    searchMeta: {
      provider_status: {
        provider: "ryanair",
        availability: { status: "failed" },
        fares: { status: "ok" },
        overall: "partial_degraded",
        partial_results_served: true,
        total_outage: false,
      },
    },
    t: ((key: string) => key) as Parameters<typeof useQuickSearchScreenState>[0]["t"],
  });

  assert.equal(state.providerPartialInlineNotice, "providerPartialAvailabilityNotice");
});

test("useQuickSearchScreenState derives zero-result causes and relax actions from visible constraints", () => {
  const collapsed = renderScreenState({
    strictFilters: true,
    includeStops: false,
    radiusActive: false,
    radiusKm: 50,
    durationMax: "180",
    departAfter: "07:00",
    departBefore: "10:00",
    excludeOriginsCount: 1,
    excludeDestinationsCount: 2,
    t: ((key: string) => `copy:${key}`) as Parameters<typeof useQuickSearchScreenState>[0]["t"],
  });

  assert.equal(collapsed.emptyStateMainTitle, "copy:emptyStateMainTitle");
  assert.equal(collapsed.zeroResultCauses.length, 6);
  assert.equal(collapsed.visibleZeroResultCauses.length, 3);
  assert.equal(collapsed.canExpandZeroResultCauses, true);
  assert.deepEqual(
    collapsed.zeroResultActions.map((action) => action.id),
    ["disable_strict", "increase_duration", "open_radius_150", "clear_exclusions"],
  );

  const expanded = renderScreenState({
    strictFilters: true,
    includeStops: false,
    radiusActive: false,
    radiusKm: 50,
    durationMax: "180",
    departAfter: "07:00",
    departBefore: "10:00",
    excludeOriginsCount: 1,
    excludeDestinationsCount: 2,
    emptyCausesExpanded: true,
    t: ((key: string) => `copy:${key}`) as Parameters<typeof useQuickSearchScreenState>[0]["t"],
  });

  assert.equal(expanded.visibleZeroResultCauses.length, expanded.zeroResultCauses.length);
});

test("useQuickSearchScreenState applies visible result filters for price, duration and risk", () => {
  const state = renderScreenState({
    results: [
      buildResult({ result_id: "cheap-fast-low", price_total: 45, duration_total_min: 80, risk_label: "low" }),
      buildResult({ result_id: "expensive-low", destination: "LIS", price_total: 170, duration_total_min: 85, risk_label: "low" }),
      buildResult({ result_id: "slow-low", destination: "OPO", price_total: 60, duration_total_min: 220, risk_label: "low" }),
      buildResult({ result_id: "medium-risk", destination: "STN", price_total: 50, duration_total_min: 90, risk_label: "medium" }),
    ],
    priceMax: "100",
    durationMax: "120",
    riskFilter: "low",
  });

  assert.deepEqual(state.visibleResults.map((item) => item.result_id), ["cheap-fast-low"]);
});

test("useQuickSearchScreenState groups sources defensively when raw source values are malformed", () => {
  const state = renderScreenState({
    results: [
      buildResult({ result_id: "raw-1", source: 123 as unknown as string }),
      buildResult({ result_id: "raw-2", destination: "LIS", source: "" }),
    ],
  });

  assert.deepEqual(state.sourcesSummary.entries, [["sourceUnknown", 2]]);
  assert.equal(state.sourcesSummary.preview, "sourceUnknown (2)");
});

test("getQuickSearchVisualState keeps loading dominant while the visual hold is active", () => {
  const visualState = getQuickSearchVisualState({
    searchState: "empty",
    showLoader: false,
    loadingVisualHold: true,
    visibleResultsCount: 0,
  });

  assert.equal(visualState, "loading");
});

test("getQuickSearchVisualState resolves final success states after loading finishes", () => {
  assert.equal(
    getQuickSearchVisualState({
      searchState: "success",
      showLoader: false,
      loadingVisualHold: false,
      visibleResultsCount: 2,
    }),
    "success_with_results",
  );

  assert.equal(
    getQuickSearchVisualState({
      searchState: "success",
      showLoader: false,
      loadingVisualHold: false,
      visibleResultsCount: 0,
    }),
    "success_empty",
  );
});
