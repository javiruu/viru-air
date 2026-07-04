import { findCountryByIata } from "@/modules/shared/airports";
import type { DashboardHistoryRow, DashboardWatch } from "@/modules/dashboard/next-best-action-types";
import type { ResumeSearchSnapshot } from "@/modules/quick-search/resume-search";

const FOUND_FOR_YOU_MAX_AGE_HOURS = 24;
const CHEAP_PRICE_HARD_LIMIT = 25;
const CHEAP_PRICE_SOFT_LIMIT = 35;
const RELATIVE_DEAL_RATIO = 0.72;
const FOUND_FOR_YOU_DISMISSED_KEY = "viru_found_for_you_dismissed_key";

export type DashboardFoundForYou = {
  key: string;
  watchId: string;
  routeLabel: string;
  origin: string;
  destination: string;
  travelDate: string;
  currentPrice: number;
  currency: string;
  destinationCountry: string | null;
  matchedCountry: string | null;
};

type Candidate = DashboardFoundForYou & {
  score: number;
};

function routeLabel(origin: string, destination: string): string {
  return `${origin} -> ${destination}`;
}

function hoursSince(now: Date, iso: string): number | null {
  const value = new Date(iso).getTime();
  if (Number.isNaN(value)) return null;
  return Math.max(0, (now.getTime() - value) / (1000 * 60 * 60));
}

function groupHistoryByWatch(rows: DashboardHistoryRow[]): Map<string, DashboardHistoryRow[]> {
  const grouped = new Map<string, DashboardHistoryRow[]>();
  for (const row of rows) {
    const existing = grouped.get(row.watch_id);
    if (existing) {
      existing.push(row);
      continue;
    }
    grouped.set(row.watch_id, [row]);
  }
  for (const watchRows of grouped.values()) {
    watchRows.sort((left, right) => new Date(left.captured_at_utc).getTime() - new Date(right.captured_at_utc).getTime());
  }
  return grouped;
}

function affinityScore(watch: DashboardWatch, snapshot: ResumeSearchSnapshot | null): number {
  if (!snapshot) return 0;
  let score = 0;
  if (snapshot.origin === watch.origin_iata) score += 3;
  if (snapshot.destination === watch.destination_iata) score += 4;
  const watchedCountry = findCountryByIata(watch.destination_iata)?.name ?? "";
  const snapshotCountry = findCountryByIata(snapshot.destination)?.name ?? "";
  if (watchedCountry && snapshotCountry && watchedCountry === snapshotCountry) score += 2;
  return score;
}

export function getFoundForYouSuggestion(args: {
  watches: DashboardWatch[];
  historyRows: DashboardHistoryRow[];
  resumeSnapshot: ResumeSearchSnapshot | null;
  dismissedKey?: string | null;
  now?: Date;
}): DashboardFoundForYou | null {
  const now = args.now ?? new Date();
  const rowsByWatch = groupHistoryByWatch(args.historyRows);
  const candidates: Candidate[] = [];

  for (const watch of args.watches) {
    const rows = rowsByWatch.get(watch.id) ?? [];
    if (rows.length < 2) continue;
    const latest = rows.at(-1);
    if (!latest) continue;
    const latestHours = hoursSince(now, latest.captured_at_utc);
    if (latestHours == null || latestHours > FOUND_FOR_YOU_MAX_AGE_HOURS) continue;

    const avgPrice = rows.reduce((sum, row) => sum + row.raw_price, 0) / rows.length;
    const destinationCountry = findCountryByIata(watch.destination_iata)?.name ?? "";
    const interestCountry = args.resumeSnapshot ? findCountryByIata(args.resumeSnapshot.destination)?.name ?? "" : "";
    const affinity = affinityScore(watch, args.resumeSnapshot);
    const isVeryCheap = latest.raw_price <= CHEAP_PRICE_HARD_LIMIT;
    const isGoodRelativeDeal = latest.raw_price <= CHEAP_PRICE_SOFT_LIMIT && latest.raw_price <= avgPrice * RELATIVE_DEAL_RATIO;
    if (!isVeryCheap && !isGoodRelativeDeal) continue;
    if (affinity <= 0) continue;

    const candidateKey = `${watch.id}:${latest.captured_at_utc}:${latest.raw_price}`;
    if (args.dismissedKey && args.dismissedKey === candidateKey) continue;
    candidates.push({
      key: candidateKey,
      watchId: watch.id,
      routeLabel: routeLabel(watch.origin_iata, watch.destination_iata),
      origin: watch.origin_iata,
      destination: watch.destination_iata,
      travelDate: watch.travel_date_local,
      currentPrice: latest.raw_price,
      currency: latest.raw_currency,
      destinationCountry: destinationCountry || null,
      matchedCountry:
        destinationCountry && interestCountry && destinationCountry === interestCountry
          ? destinationCountry
          : null,
      score: affinity * 10 + Math.max(0, 40 - latest.raw_price),
    });
  }

  candidates.sort((left, right) => right.score - left.score);
  return candidates[0] ?? null;
}

export function loadDismissedFoundForYouKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(FOUND_FOR_YOU_DISMISSED_KEY);
}

export function dismissFoundForYouKey(key: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(FOUND_FOR_YOU_DISMISSED_KEY, key);
}
