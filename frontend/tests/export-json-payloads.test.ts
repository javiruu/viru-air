import assert from "node:assert/strict";
import test from "node:test";

import { buildQuickSearchCanonicalPayload } from "../src/modules/quick-search/api/buildQuickSearchRequest";
import {
  buildQuickSearchExportPagePayload,
  buildQuickSearchExportPayload,
  QUICK_SEARCH_EXPORT_PAGE_SIZE,
  type QuickSearchExportCriteria,
} from "../src/modules/quick-search/exportQuickSearchJson";
import type { SearchResult } from "../src/modules/quick-search/types";
import { buildWatchlistExportPayload } from "../src/modules/watchlist/exportWatchlistJson";
import type { HistoryRow, Watch } from "../src/modules/watchlist/types";

test("watchlist JSON export groups every saved flight with its snapshots", () => {
  const items: Watch[] = [
    {
      id: "watch-1",
      origin_iata: "MAD",
      destination_iata: "DUB",
      travel_date_local: "2026-04-20",
      target_price: 80,
      status: "active",
      watchers_count: 2,
      group_id: "trip-1",
    },
  ];
  const historyRows: HistoryRow[] = [
    {
      watchId: "watch-1",
      origin: "MAD",
      destination: "DUB",
      travelDate: "2026-04-20",
      capturedAt: "2026-01-01T09:00:00Z",
      price: 61,
      currency: "EUR",
      departureTime: "08:15",
      provider: "ryanair",
    },
    {
      watchId: "watch-1",
      origin: "MAD",
      destination: "DUB",
      travelDate: "2026-04-20",
      capturedAt: "2026-01-02T09:00:00Z",
      price: 53,
      currency: "EUR",
      departureTime: "08:15",
      provider: "ryanair",
    },
  ];

  const payload = buildWatchlistExportPayload({
    items,
    historyRows,
    exportedAt: "2026-01-03T10:00:00Z",
  });

  assert.equal(payload.schema_version, "watchlist-export.v1");
  assert.equal(payload.totals.flights, 1);
  assert.equal(payload.totals.snapshots, 2);
  assert.equal(payload.flights[0]?.watch.id, "watch-1");
  assert.equal(payload.flights[0]?.snapshot_summary.min_price, 53);
  assert.equal(payload.flights[0]?.snapshot_summary.latest_price, 53);
  assert.equal(payload.flights[0]?.snapshots[0]?.departure_time_local, "08:15");
  assert.equal(payload.flights[0]?.latest_snapshot?.captured_at_utc, "2026-01-02T09:00:00Z");
});

test("quick-search JSON export preserves criteria, backend meta, and all result details", () => {
  const criteria: QuickSearchExportCriteria = {
    origin: "MAD",
    destination: "DUB",
    origin_scope_iata: ["MAD"],
    destination_scope_iata: ["DUB"],
    travel_date: "2026-04-20",
    return_date: null,
    trip_type: "one_way",
    adults: 1,
    departure_window: { after: "06:00", before: "12:00" },
    flexibility: { days_before: 1, days_after: 2, apply_to_return: false },
    route_scope: { include_nearby_origins: true, include_nearby_destinations: false, radius_km: 150 },
    constraints: {
      include_stops: true,
      max_stops: 1,
      buffer_min: "45",
      strict_filters: false,
      exclude_origins: ["BCN"],
      exclude_destinations: [],
    },
    visible_filters: {
      price_min: "30",
      price_max: "120",
      duration_max: "240",
      sort_by: "price",
    },
  };
  const results: SearchResult[] = [
    {
      result_id: "result-1",
      origin: "MAD",
      destination: "DUB",
      travel_date: "2026-04-20",
      departure_time_local: "08:15",
      price: 53,
      price_total: 53,
      currency: "EUR",
      source: "ryanair",
      duration_total_min: 165,
      stop_count: 0,
      ranking_score: 91,
      freshness_ts: "2026-01-02T09:00:00Z",
      stale_data: false,
      legs: [
        {
          origin_iata: "MAD",
          destination_iata: "DUB",
          dep_ts: "2026-04-20T08:15:00",
          arr_ts: "2026-04-20T10:00:00",
          flight_num: "FR123",
          price: 53,
        },
      ],
    },
  ];

  const payload = buildQuickSearchExportPayload({
    exportedAt: "2026-01-03T10:00:00Z",
    criteria,
    results,
    meta: {
      pagination: {
        page: 1,
        page_size: QUICK_SEARCH_EXPORT_PAGE_SIZE,
        sort_by: "price",
        total_results: 1,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
      generated_at: "2026-01-03T09:59:00Z",
    },
    filters: { applied: { direct: true }, relaxed: [], warnings: [], discarded: 0 },
    jobId: "job-1",
    pagesFetched: 1,
  });

  assert.equal(payload.schema_version, "quick-search-export.v1");
  assert.equal(payload.search.criteria.departure_window.after, "06:00");
  assert.equal(payload.search.result_count, 1);
  assert.equal(payload.search.backend_total_results, 1);
  assert.equal(payload.results[0]?.departure_time_local, "08:15");
  assert.equal(payload.results[0]?.legs[0]?.flight_num, "FR123");
  assert.equal(payload.results[0]?.raw_result.result_id, "result-1");
});

test("quick-search export page payload requests the backend maximum page size", () => {
  const basePayload = buildQuickSearchCanonicalPayload({
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date: "2026-04-20",
    date: "2026-04-20",
    flex_days_before: 0,
    flex_days_after: 0,
    radius_km: 150,
    include_stops: false,
    include_nearby_origins: false,
    include_nearby_destinations: false,
    max_stops: 0,
    exclude_origins: [],
    exclude_destinations: [],
    strict_filters: true,
    soft_filters_weight: 0.6,
    page: 3,
    page_size: 10,
    sort_by: "ranking",
  });

  const exportPayload = buildQuickSearchExportPagePayload(basePayload, 2, "freshness");

  assert.equal(exportPayload.pagination.page, 2);
  assert.equal(exportPayload.pagination.page_size, QUICK_SEARCH_EXPORT_PAGE_SIZE);
  assert.equal(exportPayload.pagination.sort_by, "freshness");
  assert.equal(exportPayload.origin.seed_iata, "MAD");
});
