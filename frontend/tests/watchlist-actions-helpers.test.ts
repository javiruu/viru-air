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
});

test("filterWatchesBySelection filters by origin, destination and optional dates", () => {
  const strict = filterWatchesBySelection(WATCHES, "MAD", "DUB", ["2026-07-10"]);
  assert.deepEqual(strict.map((w) => w.id), ["w1"]);

  const noDateFilter = filterWatchesBySelection(WATCHES, "MAD", "DUB", []);
  assert.deepEqual(noDateFilter.map((w) => w.id), ["w1"]);
});
