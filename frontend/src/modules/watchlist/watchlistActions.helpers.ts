import type { HistoryRow, Snapshot, Watch } from "@/modules/watchlist/types";

export function mapSnapshotsToHistoryRows(
  rows: Watch[],
  snapshots: Array<Snapshot & { watch_id: string }>,
): HistoryRow[] {
  const watchMap = new Map(rows.map((watch) => [watch.id, watch]));
  return snapshots
    .map<HistoryRow | null>((snapshot) => {
      const watch = watchMap.get(snapshot.watch_id);
      if (!watch) return null;
      return {
        watchId: watch.id,
        origin: watch.origin_iata,
        destination: watch.destination_iata,
        travelDate: watch.travel_date_local,
        capturedAt: snapshot.captured_at_utc,
        price: snapshot.raw_price,
        currency: snapshot.raw_currency,
        departureTime: snapshot.departure_time_local,
      };
    })
    .filter((row): row is HistoryRow => Boolean(row));
}

export function filterWatchesBySelection(
  items: Watch[],
  selectedOrigin: string,
  selectedDestination: string,
  selectedDates: string[],
): Watch[] {
  return items.filter(
    (item) =>
      item.origin_iata === selectedOrigin &&
      item.destination_iata === selectedDestination &&
      (selectedDates.length === 0 || selectedDates.includes(item.travel_date_local)),
  );
}
