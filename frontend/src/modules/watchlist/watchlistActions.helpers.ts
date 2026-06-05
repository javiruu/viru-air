import type { HistoryRow, Snapshot, Watch } from "@/modules/watchlist/types";

function toRefreshBucket(capturedAtUtc: string): string {
  const normalized = capturedAtUtc.trim();
  const [withoutFraction] = normalized.split(".");
  return withoutFraction.length >= 19 ? withoutFraction.slice(0, 19) : normalized;
}

function compareSnapshotPriority(
  candidate: Snapshot & { watch_id: string },
  current: Snapshot & { watch_id: string },
): number {
  if (candidate.raw_price !== current.raw_price) {
    return candidate.raw_price - current.raw_price;
  }
  const candidateDeparture = candidate.departure_time_local ?? "99:99";
  const currentDeparture = current.departure_time_local ?? "99:99";
  return candidateDeparture.localeCompare(currentDeparture);
}

export function mapSnapshotsToHistoryRows(
  rows: Watch[],
  snapshots: Array<Snapshot & { watch_id: string }>,
): HistoryRow[] {
  const watchMap = new Map(rows.map((watch) => [watch.id, watch]));
  const dedupedSnapshots = new Map<string, Snapshot & { watch_id: string }>();
  snapshots.forEach((snapshot) => {
    const key = [snapshot.watch_id, toRefreshBucket(snapshot.captured_at_utc)].join("|");
    const current = dedupedSnapshots.get(key);
    if (!current || compareSnapshotPriority(snapshot, current) < 0) {
      dedupedSnapshots.set(key, snapshot);
    }
  });
  return Array.from(dedupedSnapshots.values())
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
