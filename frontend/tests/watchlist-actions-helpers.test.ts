import assert from "node:assert/strict";
import test from "node:test";

import {
  filterWatchesBySelection,
  mapLatestWatchSnapshotsToHistoryRows,
  mapSnapshotsToHistoryRows,
  mergeWatchDetailPriceHistoryRows,
  resolveCurrentWatchDetail,
} from "@/modules/watchlist/watchlistActions.helpers";
import { createEmptyCommunityPricing } from "@/modules/watchlist/watchlistApiCompatibility";
import type { HistoryRow, Snapshot, WatchDetail, Watch } from "@/modules/watchlist/types";

const WATCHES: Watch[] = [
  {
    id: "w1",
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date_local: "2026-07-10",
    status: "active",
    target_price: null,
    community_pricing: createEmptyCommunityPricing(),
  },
  {
    id: "w2",
    origin_iata: "MAD",
    destination_iata: "BCN",
    travel_date_local: "2026-07-10",
    status: "active",
    target_price: null,
    community_pricing: createEmptyCommunityPricing(),
  },
];

test("mapSnapshotsToHistoryRows maps only snapshots linked to existing watch ids", () => {
  const snapshots: Array<Snapshot & { watch_id: string }> = [
    {
      watch_id: "w1",
      captured_at_utc: "2026-05-01T10:00:00Z",
      raw_price: 100,
      raw_currency: "EUR",
      departure_time_local: "10:00",
      provider: "easyjet-public",
    },
    {
      watch_id: "missing",
      captured_at_utc: "2026-05-02T10:00:00Z",
      raw_price: 110,
      raw_currency: "EUR",
      departure_time_local: "10:00",
    },
  ];

  const rows = mapSnapshotsToHistoryRows(WATCHES, snapshots);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].watchId, "w1");
  assert.equal(rows[0].origin, "MAD");
  assert.equal(rows[0].destination, "DUB");
  assert.equal(rows[0].provider, "easyjet-public");
});

test("mapLatestWatchSnapshotsToHistoryRows exposes the persisted save-result price before batch history returns", () => {
  const rows = mapLatestWatchSnapshotsToHistoryRows([
    {
      ...WATCHES[0],
      latest_snapshot: {
        captured_at_utc: "2026-05-01T10:00:00Z",
        raw_price: 47,
        raw_currency: "EUR",
        departure_time_local: "10:00",
        provider: "quick-search",
      },
    },
  ]);

  assert.deepEqual(rows.map((row) => [row.watchId, row.price, row.currency]), [
    ["w1", 47, "EUR"],
  ]);
});

test("mapSnapshotsToHistoryRows collapses same-refresh legacy snapshots to one canonical point", () => {
  const snapshots: Array<Snapshot & { watch_id: string }> = [
    {
      watch_id: "w1",
      captured_at_utc: "2026-05-01T10:00:00.123456",
      raw_price: 120,
      raw_currency: "EUR",
      departure_time_local: "10:00",
      provider: "vueling-public",
    },
    {
      watch_id: "w1",
      captured_at_utc: "2026-05-01T10:00:00.654321",
      raw_price: 99,
      raw_currency: "EUR",
      departure_time_local: "12:00",
      provider: "wizzair-public",
    },
    {
      watch_id: "w1",
      captured_at_utc: "2026-05-01T10:00:00.999999",
      raw_price: 101,
      raw_currency: "EUR",
      departure_time_local: "08:30",
      provider: "ryanair-public",
    },
    {
      watch_id: "w1",
      captured_at_utc: "2026-05-01T10:05:00.000001",
      raw_price: 88,
      raw_currency: "EUR",
      departure_time_local: "09:45",
      provider: "easyjet-public",
    },
  ];

  const rows = mapSnapshotsToHistoryRows(WATCHES, snapshots);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].price, 99);
  assert.equal(rows[0].capturedAt, "2026-05-01T10:00:00.654321");
  assert.equal(rows[0].departureTime, "12:00");
  assert.equal(rows[0].provider, "wizzair-public");
  assert.equal(rows[1].price, 88);
  assert.equal(rows[1].capturedAt, "2026-05-01T10:05:00.000001");
  assert.equal(rows[1].provider, "easyjet-public");
});

test("mergeWatchDetailPriceHistoryRows adds selected watch backfill points without duplicating current history", () => {
  const rows: HistoryRow[] = [
    {
      watchId: "w1",
      origin: "MAD",
      destination: "DUB",
      travelDate: "2026-07-10",
      capturedAt: "2026-05-02T10:00:00Z",
      price: 88,
      currency: "EUR",
      departureTime: "09:45",
      provider: "easyjet-public",
    },
  ];
  const detail: WatchDetail = {
    ...WATCHES[0],
    latest_snapshot: null,
    price_history: [
      {
        captured_at_utc: "2026-05-01T10:00:00Z",
        raw_price: 99,
        raw_currency: "EUR",
        departure_time_local: "12:00",
        provider: "historical_backfill",
        is_stale: true,
        source_kind: "historical_backfill",
      },
      {
        captured_at_utc: "2026-05-02T10:00:00.123456",
        raw_price: 90,
        raw_currency: "EUR",
        departure_time_local: "10:00",
        provider: "historical_backfill",
        is_stale: true,
        source_kind: "historical_backfill",
      },
    ],
  };

  const merged = mergeWatchDetailPriceHistoryRows(rows, detail);
  const backfill = merged.find((row) => row.sourceKind === "historical_backfill");

  assert.equal(merged.length, 2);
  assert.equal(merged.filter((row) => row.capturedAt.startsWith("2026-05-02T10:00:00")).length, 1);
  assert.equal(backfill?.isStale, true);
  assert.equal(backfill?.capturedAt, "2026-05-01T10:00:00Z");
});

test("filterWatchesBySelection filters by origin, destination and optional dates", () => {
  const strict = filterWatchesBySelection(WATCHES, "MAD", "DUB", ["2026-07-10"]);
  assert.deepEqual(strict.map((w) => w.id), ["w1"]);

  const noDateFilter = filterWatchesBySelection(WATCHES, "MAD", "DUB", []);
  assert.deepEqual(noDateFilter.map((w) => w.id), ["w1"]);
});

test("resolveCurrentWatchDetail rejects detail from the previously selected watch", () => {
  const previousDetail: WatchDetail = {
    ...WATCHES[1],
    latest_snapshot: null,
    fare_profile: {
      travelers: 1,
      extras: [{ kind: "fast_track", selected: true }],
    },
  };

  assert.equal(resolveCurrentWatchDetail(WATCHES[0], previousDetail), null);
  assert.equal(resolveCurrentWatchDetail(WATCHES[1], previousDetail), previousDetail);
});
