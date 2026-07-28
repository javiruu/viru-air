import type { HistoryRow, Snapshot, Watch, WatchDetail } from "@/modules/watchlist/types";

type SnapshotWithWatchId = Snapshot & { watch_id: string };

function toRefreshBucket(capturedAtUtc: string): string {
  const normalized = capturedAtUtc.trim();
  const [withoutFraction] = normalized.split(".");
  return withoutFraction.length >= 19 ? withoutFraction.slice(0, 19) : normalized;
}

function compareSnapshotPriority(
  candidate: SnapshotWithWatchId,
  current: SnapshotWithWatchId,
): number {
  if (candidate.raw_price !== current.raw_price) {
    return candidate.raw_price - current.raw_price;
  }
  const candidateDeparture = candidate.departure_time_local ?? "99:99";
  const currentDeparture = current.departure_time_local ?? "99:99";
  const departureOrder = candidateDeparture.localeCompare(currentDeparture);
  if (departureOrder !== 0) return departureOrder;
  const candidateProvider = candidate.provider ?? "";
  const currentProvider = current.provider ?? "";
  return candidateProvider.localeCompare(currentProvider);
}

function compareHistoryPriority(candidate: HistoryRow, current: HistoryRow): number {
  if (candidate.price !== current.price) {
    return candidate.price - current.price;
  }
  const candidateDeparture = candidate.departureTime ?? "99:99";
  const currentDeparture = current.departureTime ?? "99:99";
  const departureOrder = candidateDeparture.localeCompare(currentDeparture);
  if (departureOrder !== 0) return departureOrder;
  const candidateProvider = candidate.provider ?? "";
  const currentProvider = current.provider ?? "";
  return candidateProvider.localeCompare(currentProvider);
}

function snapshotToHistoryRow(watch: Watch, snapshot: Snapshot): HistoryRow {
  return {
    watchId: watch.id,
    origin: watch.origin_iata,
    destination: watch.destination_iata,
    travelDate: watch.travel_date_local,
    capturedAt: snapshot.captured_at_utc,
    price: snapshot.raw_price,
    currency: snapshot.raw_currency,
    departureTime: snapshot.departure_time_local,
    provider: snapshot.provider ?? null,
    isStale: snapshot.is_stale,
    sourceKind: snapshot.source_kind,
  };
}

export function mapSnapshotsToHistoryRows(
  rows: Watch[],
  snapshots: SnapshotWithWatchId[],
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
      return snapshotToHistoryRow(watch, snapshot);
    })
    .filter((row): row is HistoryRow => Boolean(row));
}

export function mergeWatchDetailPriceHistoryRows(rows: HistoryRow[], detail: WatchDetail | null): HistoryRow[] {
  const detailHistory = detail?.price_history ?? [];
  if (detailHistory.length === 0 || !detail) return rows;

  const detailWatch: Watch = {
    id: detail.id,
    origin_iata: detail.origin_iata,
    destination_iata: detail.destination_iata,
    travel_date_local: detail.travel_date_local,
    target_price: detail.target_price,
    status: detail.status,
    watchers_count: detail.watchers_count,
    group_id: detail.group_id,
  };
  const merged = new Map<string, HistoryRow>();
  rows.forEach((row) => {
    merged.set([row.watchId, toRefreshBucket(row.capturedAt)].join("|"), row);
  });
  detailHistory.map((snapshot) => snapshotToHistoryRow(detailWatch, snapshot)).forEach((row) => {
    const key = [row.watchId, toRefreshBucket(row.capturedAt)].join("|");
    const current = merged.get(key);
    if (!current || compareHistoryPriority(row, current) < 0) {
      merged.set(key, row);
    }
  });

  return Array.from(merged.values());
}

export function resolveCurrentWatchDetail(selectedWatch: Watch, detail: WatchDetail | null): WatchDetail | null {
  return detail?.id === selectedWatch.id ? detail : null;
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
