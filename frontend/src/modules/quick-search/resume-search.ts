import { getToken } from "@/modules/shared/auth";
import { buildQuickSearchSearchParams } from "@/modules/shared/useRouteState";

const RESUME_SEARCH_STORAGE_KEY = "viru_resume_search_snapshot";
const RESUME_SEARCH_DISMISSED_KEY = "viru_resume_search_dismissed_key";
const RESUME_SEARCH_MAX_AGE_HOURS = 36;

export type ResumeSearchSnapshot = {
  key: string;
  ownerTokenHint: string | null;
  savedAt: string;
  href: string;
  summary: string;
  detail: string;
  origin: string;
  destination: string;
  travelDate: string;
  returnDate: string;
  isReturn: boolean;
  adults: number;
  daysBefore: number;
  daysAfter: number;
  radiusKm: number;
  strictFilters: boolean;
  departAfter: string;
  departBefore: string;
  includeStops: boolean;
  maxStops: number;
  bufferMin: string;
  includeNearbyOrigins: boolean;
  includeNearbyDestinations: boolean;
  excludeOrigins: string[];
  excludeDestinations: string[];
  priceMin: string;
  priceMax: string;
  durationMax: string;
  sortBy: "ranking" | "price" | "duration" | "freshness";
  resultsCount: number;
};

type SnapshotInput = Omit<ResumeSearchSnapshot, "key" | "ownerTokenHint" | "savedAt" | "href" | "summary" | "detail">;

function tokenHint(): string | null {
  const token = getToken();
  if (!token) return null;
  return token.slice(0, 24);
}

function safeJsonParse(raw: string | null): ResumeSearchSnapshot | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ResumeSearchSnapshot;
  } catch {
    return null;
  }
}

function hasMeaningfulIntent(input: SnapshotInput): boolean {
  if (!input.origin || !input.destination) return false;
  if (input.travelDate) return true;
  if (input.resultsCount > 0) return true;
  if (input.isReturn || input.daysBefore > 0 || input.daysAfter > 0) return true;
  if (input.includeNearbyOrigins || input.includeNearbyDestinations) return true;
  if (input.excludeOrigins.length > 0 || input.excludeDestinations.length > 0) return true;
  if (input.includeStops || input.priceMin || input.priceMax || input.durationMax) return true;
  return false;
}

function isExpired(savedAt: string, now: Date): boolean {
  const savedTime = new Date(savedAt).getTime();
  if (Number.isNaN(savedTime)) return true;
  const maxAgeMs = RESUME_SEARCH_MAX_AGE_HOURS * 60 * 60 * 1000;
  return now.getTime() - savedTime > maxAgeMs;
}

function buildKey(input: SnapshotInput): string {
  return [
    input.origin,
    input.destination,
    input.travelDate,
    input.returnDate,
    input.isReturn ? "rt" : "ow",
    input.daysBefore,
    input.daysAfter,
    input.radiusKm,
    input.includeNearbyOrigins ? "near-o" : "direct-o",
    input.includeNearbyDestinations ? "near-d" : "direct-d",
    input.excludeOrigins.join(","),
    input.excludeDestinations.join(","),
    input.includeStops ? `stops-${input.maxStops}-${input.bufferMin}` : "direct",
    input.sortBy,
    input.resultsCount,
  ].join("|");
}

function buildHref(input: SnapshotInput): string {
  const query = buildQuickSearchSearchParams({
    origin: input.origin,
    destination: input.destination,
    travelDate: input.travelDate,
    returnDate: input.returnDate,
    isReturn: input.isReturn,
    adults: input.adults,
    flexBefore: input.daysBefore,
    flexAfter: input.daysAfter,
    radius: input.radiusKm,
    strict: input.strictFilters,
  });
  return `/quick-search?resume=1${query ? `&${query}` : ""}`;
}

export function buildResumeSearchSnapshot(args: SnapshotInput & { summary: string; detail: string; now?: Date }): ResumeSearchSnapshot | null {
  const input: SnapshotInput = {
    origin: args.origin,
    destination: args.destination,
    travelDate: args.travelDate,
    returnDate: args.returnDate,
    isReturn: args.isReturn,
    adults: args.adults,
    daysBefore: args.daysBefore,
    daysAfter: args.daysAfter,
    radiusKm: args.radiusKm,
    strictFilters: args.strictFilters,
    departAfter: args.departAfter,
    departBefore: args.departBefore,
    includeStops: args.includeStops,
    maxStops: args.maxStops,
    bufferMin: args.bufferMin,
    includeNearbyOrigins: args.includeNearbyOrigins,
    includeNearbyDestinations: args.includeNearbyDestinations,
    excludeOrigins: args.excludeOrigins,
    excludeDestinations: args.excludeDestinations,
    priceMin: args.priceMin,
    priceMax: args.priceMax,
    durationMax: args.durationMax,
    sortBy: args.sortBy,
    resultsCount: args.resultsCount,
  };
  if (!hasMeaningfulIntent(input)) return null;
  const now = args.now ?? new Date();
  return {
    ...input,
    key: buildKey(input),
    ownerTokenHint: tokenHint(),
    savedAt: now.toISOString(),
    href: buildHref(input),
    summary: args.summary,
    detail: args.detail,
  };
}

export function saveResumeSearchSnapshot(snapshot: ResumeSearchSnapshot | null): void {
  if (typeof window === "undefined") return;
  if (!snapshot) {
    window.localStorage.removeItem(RESUME_SEARCH_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(RESUME_SEARCH_STORAGE_KEY, JSON.stringify(snapshot));
}

export function loadResumeSearchSnapshot(now: Date = new Date()): ResumeSearchSnapshot | null {
  if (typeof window === "undefined") return null;
  const snapshot = safeJsonParse(window.localStorage.getItem(RESUME_SEARCH_STORAGE_KEY));
  if (!snapshot) return null;
  if (snapshot.ownerTokenHint !== tokenHint()) return null;
  if (isExpired(snapshot.savedAt, now)) return null;
  const dismissedKey = window.localStorage.getItem(RESUME_SEARCH_DISMISSED_KEY);
  if (dismissedKey && dismissedKey === snapshot.key) return null;
  return snapshot;
}

export function dismissResumeSearchSnapshot(snapshotKey: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(RESUME_SEARCH_DISMISSED_KEY, snapshotKey);
}

export function clearDismissedResumeSearch(snapshotKey: string): void {
  if (typeof window === "undefined") return;
  const dismissedKey = window.localStorage.getItem(RESUME_SEARCH_DISMISSED_KEY);
  if (dismissedKey !== snapshotKey) return;
  window.localStorage.removeItem(RESUME_SEARCH_DISMISSED_KEY);
}
