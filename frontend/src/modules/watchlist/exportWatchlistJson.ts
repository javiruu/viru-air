import type { HistoryRow, Watch } from "@/modules/watchlist/types";

type WatchlistExportSnapshot = {
  captured_at_utc: string;
  raw_price: number;
  raw_currency: string;
  departure_time_local: string | null;
  provider: string | null;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
};

type WatchlistExportFlight = {
  watch: {
    id: string;
    origin_iata: string;
    destination_iata: string;
    travel_date_local: string;
    target_price: number | null;
    status: string;
    watchers_count: number | null;
    group_id: string | null;
  };
  route: string;
  snapshot_summary: {
    snapshot_count: number;
    min_price: number | null;
    max_price: number | null;
    avg_price: number | null;
    latest_price: number | null;
    currency: string | null;
    first_captured_at_utc: string | null;
    latest_captured_at_utc: string | null;
  };
  latest_snapshot: WatchlistExportSnapshot | null;
  snapshots: WatchlistExportSnapshot[];
};

export type WatchlistExportPayload = {
  schema_version: "watchlist-export.v1";
  exported_at: string;
  export_scope: "watchlist_all_saved_flights";
  totals: {
    flights: number;
    snapshots: number;
  };
  flights: WatchlistExportFlight[];
};

function summarizePrices(snapshots: WatchlistExportSnapshot[]) {
  const prices = snapshots.map((snapshot) => snapshot.raw_price).filter((price) => Number.isFinite(price));
  if (prices.length === 0) {
    return {
      min_price: null,
      max_price: null,
      avg_price: null,
      latest_price: null,
    };
  }
  const total = prices.reduce((sum, price) => sum + price, 0);
  const latestSnapshot = snapshots[snapshots.length - 1] ?? null;
  return {
    min_price: Math.min(...prices),
    max_price: Math.max(...prices),
    avg_price: total / prices.length,
    latest_price: latestSnapshot?.raw_price ?? null,
  };
}

function toExportSnapshot(row: HistoryRow): WatchlistExportSnapshot {
  return {
    captured_at_utc: row.capturedAt,
    raw_price: row.price,
    raw_currency: row.currency,
    departure_time_local: row.departureTime,
    provider: row.provider,
    origin_iata: row.origin,
    destination_iata: row.destination,
    travel_date_local: row.travelDate,
  };
}

export function buildWatchlistExportPayload(input: {
  items: Watch[];
  historyRows: HistoryRow[];
  exportedAt: string;
}): WatchlistExportPayload {
  const snapshotsByWatch = new Map<string, HistoryRow[]>();
  for (const row of input.historyRows) {
    const existing = snapshotsByWatch.get(row.watchId);
    if (existing) {
      existing.push(row);
    } else {
      snapshotsByWatch.set(row.watchId, [row]);
    }
  }

  const flights = input.items.map<WatchlistExportFlight>((watch) => {
    const snapshots = (snapshotsByWatch.get(watch.id) ?? [])
      .slice()
      .sort((left, right) => left.capturedAt.localeCompare(right.capturedAt))
      .map(toExportSnapshot);
    const latestSnapshot = snapshots[snapshots.length - 1] ?? null;
    const priceSummary = summarizePrices(snapshots);
    return {
      watch: {
        id: watch.id,
        origin_iata: watch.origin_iata,
        destination_iata: watch.destination_iata,
        travel_date_local: watch.travel_date_local,
        target_price: watch.target_price ?? null,
        status: watch.status,
        watchers_count: watch.watchers_count ?? null,
        group_id: watch.group_id ?? null,
      },
      route: `${watch.origin_iata}-${watch.destination_iata}`,
      snapshot_summary: {
        snapshot_count: snapshots.length,
        ...priceSummary,
        currency: latestSnapshot?.raw_currency ?? null,
        first_captured_at_utc: snapshots[0]?.captured_at_utc ?? null,
        latest_captured_at_utc: latestSnapshot?.captured_at_utc ?? null,
      },
      latest_snapshot: latestSnapshot,
      snapshots,
    };
  });

  return {
    schema_version: "watchlist-export.v1",
    exported_at: input.exportedAt,
    export_scope: "watchlist_all_saved_flights",
    totals: {
      flights: input.items.length,
      snapshots: input.historyRows.length,
    },
    flights,
  };
}
