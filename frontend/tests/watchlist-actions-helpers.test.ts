import assert from "node:assert/strict";
import test from "node:test";

import { filterWatchesBySelection, mapSnapshotsToHistoryRows } from "@/modules/watchlist/watchlistActions.helpers";
import type { Snapshot, Watch } from "@/modules/watchlist/types";

const WATCHES: Watch[] = [
  {
    id: "w1",
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date_local: "2026-07-10",
    status: "active",
    target_price: null,
  },
  {
    id: "w2",
    origin_iata: "MAD",
    destination_iata: "BCN",
    travel_date_local: "2026-07-10",
    status: "active",
    target_price: null,
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

test("filterWatchesBySelection filters by origin, destination and optional dates", () => {
  const strict = filterWatchesBySelection(WATCHES, "MAD", "DUB", ["2026-07-10"]);
  assert.deepEqual(strict.map((w) => w.id), ["w1"]);

  const noDateFilter = filterWatchesBySelection(WATCHES, "MAD", "DUB", []);
  assert.deepEqual(noDateFilter.map((w) => w.id), ["w1"]);
});
