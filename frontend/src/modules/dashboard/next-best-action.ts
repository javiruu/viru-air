import type {
  DashboardHistoryRow,
  DashboardNextAction,
  DashboardNotificationSummary,
  DashboardWatch,
} from "@/modules/dashboard/next-best-action-types";
export type {
  DashboardHistoryRow,
  DashboardNextAction,
  DashboardNotificationSummary,
  DashboardWatch,
} from "@/modules/dashboard/next-best-action-types";

const MONTH_WINDOW_DAYS = 30;
const STRONG_DROP_MIN_EUR = 10;
const FRESH_SIGNAL_MAX_HOURS = 24;
const STALE_WATCH_MIN_HOURS = 24;

type WatchSignalBase = {
  key: string;
  routeLabel: string;
  watchId: string;
  origin: string;
  destination: string;
  travelDate: string;
};

type Candidate = {
  priority: number;
  score: number;
  action: DashboardNextAction;
};

function toRouteLabel(origin: string, destination: string): string {
  return `${origin} -> ${destination}`;
}

function getWatchSignalBase(watch: DashboardWatch): WatchSignalBase {
  const routeLabel = toRouteLabel(watch.origin_iata, watch.destination_iata);
  return {
    key: `${watch.id}:${watch.travel_date_local}`,
    routeLabel,
    watchId: watch.id,
    origin: watch.origin_iata,
    destination: watch.destination_iata,
    travelDate: watch.travel_date_local,
  };
}

function getHoursBetween(now: Date, value: string): number | null {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return Math.max(0, (now.getTime() - parsed.getTime()) / (1000 * 60 * 60));
}

function isUrgentAction(kind: DashboardNextAction["kind"]): boolean {
  return kind === "strong_drop" || kind === "new_low";
}

function groupRowsByWatch(rows: DashboardHistoryRow[]): Map<string, DashboardHistoryRow[]> {
  const grouped = new Map<string, DashboardHistoryRow[]>();
  for (const row of rows) {
    const current = grouped.get(row.watch_id);
    if (current) {
      current.push(row);
      continue;
    }
    grouped.set(row.watch_id, [row]);
  }
  for (const rowsForWatch of grouped.values()) {
    rowsForWatch.sort(
      (left, right) =>
        new Date(left.captured_at_utc).getTime() - new Date(right.captured_at_utc).getTime(),
    );
  }
  return grouped;
}

export function getDashboardNextActionCandidates(args: {
  watches: DashboardWatch[];
  historyRows: DashboardHistoryRow[];
  notificationSummary: DashboardNotificationSummary | null;
  now?: Date;
}): DashboardNextAction[] {
  const { watches, historyRows, notificationSummary } = args;
  const now = args.now ?? new Date();

  if (watches.length === 0) {
    return [{ kind: "onboarding", key: "onboarding" }];
  }

  const rowsByWatch = groupRowsByWatch(historyRows);
  const candidates: Candidate[] = [];

  for (const watch of watches) {
    const signalBase = getWatchSignalBase(watch);
    const rows = rowsByWatch.get(watch.id) ?? [];
    const latest = rows.at(-1) ?? null;

    if (!latest) {
      candidates.push({
        priority: 6,
        score: Number.POSITIVE_INFINITY,
        action: {
          kind: "stale_watch",
          key: `stale:${signalBase.key}:missing`,
          routeLabel: signalBase.routeLabel,
          watchId: signalBase.watchId,
          origin: signalBase.origin,
          destination: signalBase.destination,
          travelDate: signalBase.travelDate,
          staleHours: null,
          lastUpdatedAt: null,
        },
      });
      continue;
    }

    const latestHours = getHoursBetween(now, latest.captured_at_utc);
    const latestIsFreshSignal = latestHours != null && latestHours <= FRESH_SIGNAL_MAX_HOURS;
    const previous = rows.at(-2) ?? null;

    if (latestIsFreshSignal && previous && previous.raw_currency === latest.raw_currency) {
      const dropAmount = previous.raw_price - latest.raw_price;
      if (dropAmount >= STRONG_DROP_MIN_EUR) {
        candidates.push({
          priority: 1,
          score: dropAmount,
          action: {
            kind: "strong_drop",
            key: `strong_drop:${signalBase.key}:${latest.captured_at_utc}:${dropAmount}`,
            routeLabel: signalBase.routeLabel,
            watchId: signalBase.watchId,
            origin: signalBase.origin,
            destination: signalBase.destination,
            travelDate: signalBase.travelDate,
            dropAmount,
            latestPrice: latest.raw_price,
            previousPrice: previous.raw_price,
            currency: latest.raw_currency,
          },
        });
      }
    }

    if (latestIsFreshSignal && rows.length >= 2) {
      const previousRows = rows.slice(0, -1);
      const previousLow = Math.min(...previousRows.map((row) => row.raw_price));
      if (latest.raw_price < previousLow) {
        candidates.push({
          priority: 2,
          score: previousLow - latest.raw_price,
          action: {
            kind: "new_low",
            key: `new_low:${signalBase.key}:${latest.captured_at_utc}:${latest.raw_price}`,
            routeLabel: signalBase.routeLabel,
            watchId: signalBase.watchId,
            origin: signalBase.origin,
            destination: signalBase.destination,
            travelDate: signalBase.travelDate,
            latestPrice: latest.raw_price,
            previousLowPrice: previousLow,
            currency: latest.raw_currency,
          },
        });
      }
    }

    if (latestIsFreshSignal) {
      const monthCutoffMs = now.getTime() - MONTH_WINDOW_DAYS * 24 * 60 * 60 * 1000;
      const monthRows = rows.filter((row) => {
        const parsed = new Date(row.captured_at_utc).getTime();
        return !Number.isNaN(parsed) && parsed >= monthCutoffMs;
      });
      if (monthRows.length >= 3) {
        const monthlyLow = Math.min(...monthRows.map((row) => row.raw_price));
        if (latest.raw_price === monthlyLow) {
          candidates.push({
            priority: 3,
            score: monthRows.length,
            action: {
              kind: "best_month",
              key: `best_month:${signalBase.key}:${latest.captured_at_utc}:${latest.raw_price}`,
              routeLabel: signalBase.routeLabel,
              watchId: signalBase.watchId,
              origin: signalBase.origin,
              destination: signalBase.destination,
              travelDate: signalBase.travelDate,
              latestPrice: latest.raw_price,
              currency: latest.raw_currency,
              monthlyObservationCount: monthRows.length,
            },
          });
        }
      }
    }

    if (latestHours == null || latestHours >= STALE_WATCH_MIN_HOURS) {
      candidates.push({
        priority: 6,
        score: latestHours ?? Number.POSITIVE_INFINITY,
        action: {
          kind: "stale_watch",
          key: `stale:${signalBase.key}:${latest.captured_at_utc}`,
          routeLabel: signalBase.routeLabel,
          watchId: signalBase.watchId,
          origin: signalBase.origin,
          destination: signalBase.destination,
          travelDate: signalBase.travelDate,
          staleHours: latestHours == null ? null : Math.floor(latestHours),
          lastUpdatedAt: latest.captured_at_utc,
        },
      });
    }
  }

  if (notificationSummary && notificationSummary.unread > 0) {
    candidates.push({
      priority: 4,
      score: notificationSummary.unread,
      action: {
        kind: "unread_alerts",
        key: `unread_alerts:${notificationSummary.unread}:${notificationSummary.price}:${notificationSummary.security}`,
        unreadCount: notificationSummary.unread,
      },
    });
  }

  if (candidates.length === 0) {
    return [{ kind: "calm", key: `calm:${watches.length}`, trackedCount: watches.length }];
  }

  candidates.sort((left, right) => {
    if (left.priority !== right.priority) {
      return left.priority - right.priority;
    }
    return right.score - left.score;
  });

  return candidates.map((candidate) => candidate.action);
}

export function pickDashboardNextBestAction(args: {
  watches: DashboardWatch[];
  historyRows: DashboardHistoryRow[];
  notificationSummary: DashboardNotificationSummary | null;
  now?: Date;
  seenActionKey?: string | null;
}): DashboardNextAction {
  const candidates = getDashboardNextActionCandidates(args);
  const seenActionKey = args.seenActionKey ?? null;

  if (!seenActionKey) {
    return candidates[0] ?? { kind: "calm", key: "calm:0", trackedCount: 0 };
  }

  const unseenCandidate = candidates.find((candidate) => {
    if (candidate.key !== seenActionKey) {
      return true;
    }
    return isUrgentAction(candidate.kind);
  });

  return unseenCandidate ?? candidates[0] ?? { kind: "calm", key: "calm:0", trackedCount: 0 };
}
