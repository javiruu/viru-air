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
      sortBy: "ranking",
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
    ranking_score: 0.91,
    stale_data: false,
    itinerary_type: "direct",
    legs: [],
    ...overrides,
  };
}

test("useQuickSearchScreenState exposes degraded state and groups warnings", () => {
  const state = renderScreenState({
    results: [
      buildResult({ result_id: "res-1", ranking_score: 0.9 }),
      buildResult({ result_id: "res-2", destination: "LIS", ranking_score: 0.95 }),
    ],
    filtersWarningCodes: ["ryanair_unavailable_partial", "provider_error_partial", "ryanair_provider_unavailable_total"],
    searchMeta: { stale_data: true },
  });

  assert.equal(state.showDegradedState, true);
  assert.equal(state.visibleResults.length, 2);
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

test("useQuickSearchScreenState treats easyJet outage codes as provider outages", () => {
  const state = renderScreenState({
    filtersWarningCodes: ["easyjet_provider_unavailable_total"],
  });

  assert.equal(state.showDegradedState, true);
  assert.equal(state.emptyStateMainTitle, "emptyStateProviderTitle");
  assert.deepEqual(state.zeroResultCauses, ["emptyCauseProvider"]);
  assert.deepEqual(state.groupedCriticalWarnings, [{ message: "easyjet_provider_unavailable_total", count: 1 }]);
  assert.deepEqual(state.zeroResultActions, []);
});

test("useQuickSearchScreenState treats Iberia outage codes as provider outages", () => {
  const state = renderScreenState({
    filtersWarningCodes: ["iberia_provider_unavailable_total"],
  });

  assert.equal(state.showDegradedState, true);
  assert.equal(state.emptyStateMainTitle, "emptyStateProviderTitle");
  assert.deepEqual(state.zeroResultCauses, ["emptyCauseProvider"]);
  assert.deepEqual(state.groupedCriticalWarnings, [{ message: "iberia_provider_unavailable_total", count: 1 }]);
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
    ["try_plus_1_day", "open_nearby", "max_coverage", "open_more_options"],
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

test("useQuickSearchScreenState treats canonical provider outage signals as degraded even without legacy ryanair codes", () => {
  const state = renderScreenState({
    filtersWarningCodes: ["provider_total_outage"],
    searchMeta: {
      provider_status: {
        provider: "duffel",
        overall_status: "total_outage",
        partial_results_served: false,
        total_outage: true,
      },
    },
  });

  assert.equal(state.showDegradedState, true);
  assert.equal(state.emptyStateMainTitle, "emptyStateProviderTitle");
  assert.deepEqual(state.zeroResultCauses, ["emptyCauseProvider"]);
  assert.deepEqual(state.groupedCriticalWarnings, [{ message: "provider_total_outage", count: 1 }]);
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
    ["try_plus_1_day", "open_nearby", "max_coverage", "open_more_options"],
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

test("useQuickSearchScreenState applies visible result filters for price and duration", () => {
  const state = renderScreenState({
    results: [
      buildResult({ result_id: "cheap-fast", price_total: 45, duration_total_min: 80 }),
      buildResult({ result_id: "expensive", destination: "LIS", price_total: 170, duration_total_min: 85 }),
      buildResult({ result_id: "slow", destination: "OPO", price_total: 60, duration_total_min: 220 }),
      buildResult({ result_id: "second-fit", destination: "STN", price_total: 50, duration_total_min: 90 }),
    ],
    priceMax: "100",
    durationMax: "120",
  });

  assert.deepEqual(state.visibleResults.map((item) => item.result_id), ["cheap-fast", "second-fit"]);
});

test("useQuickSearchScreenState groups sources defensively when raw source values are malformed", () => {
  const state = renderScreenState({
    results: [
      buildResult({ result_id: "raw-1", source: 123 as unknown as string }),
      buildResult({ result_id: "raw-2", destination: "LIS", source: "" }),
    ],
  });

  assert.deepEqual(state.sourcesSummary.entries, [{ id: "unknown", label: "sourceUnknown", count: 2 }]);
  assert.equal(state.sourcesSummary.preview, "sourceUnknown (2)");
});

test("useQuickSearchScreenState groups multiple raw sources into provider-level labels", () => {
  const state = renderScreenState({
    results: [
      buildResult({ result_id: "ry-1", source: "ryanair-public-fares" }),
      buildResult({ result_id: "ry-2", destination: "LIS", source: "ryanair-public-fares" }),
      buildResult({ result_id: "wz-1", destination: "BCN", source: "wizzair-farechart" }),
      buildResult({ result_id: "ib-1", destination: "JFK", source: "iberia-public-availability" }),
    ],
  });

  assert.deepEqual(state.sourcesSummary.entries, [
    { id: "ryanair", label: "Ryanair", count: 2 },
    { id: "iberia", label: "Iberia", count: 1 },
    { id: "wizzair", label: "Wizz Air", count: 1 },
  ]);
  assert.equal(state.sourcesSummary.preview, "Ryanair (2), Iberia (1)");
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
