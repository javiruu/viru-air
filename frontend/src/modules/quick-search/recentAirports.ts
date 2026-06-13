import type { AirportIataEntry } from "@/modules/quick-search/types";

export const RECENT_AIRPORTS_STORAGE_KEY = "viru_recent_airports";
const RECENT_AIRPORTS_LIMIT = 6;

type StorageLike = Pick<Storage, "getItem" | "setItem">;

export type QuickSearchRecentAirportSuggestion = {
  iata: string;
  name: string;
};

function normalizeIata(value: string): string {
  return value.trim().toUpperCase();
}

function matchesRecentAirportQuery(entry: AirportIataEntry | undefined, iata: string, query: string): boolean {
  if (!query) return true;
  const normalizedQuery = query.trim().toUpperCase();
  if (!normalizedQuery) return true;

  const name = entry?.name?.toUpperCase() || "";
  const municipality = entry?.municipality?.toUpperCase() || "";

  return iata.includes(normalizedQuery) || name.includes(normalizedQuery) || municipality.includes(normalizedQuery);
}

export function dedupeRecentAirports(items: string[], limit = RECENT_AIRPORTS_LIMIT): string[] {
  const seen = new Set<string>();
  const next: string[] = [];

  for (const item of items) {
    const normalized = normalizeIata(item);
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    next.push(normalized);
    if (next.length >= limit) break;
  }

  return next;
}

export function readRecentAirports(storage?: StorageLike | null): string[] {
  try {
    const raw = storage?.getItem(RECENT_AIRPORTS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return dedupeRecentAirports(parsed.filter((item): item is string => typeof item === "string"));
  } catch {
    return [];
  }
}

export function writeRecentAirports(items: string[], storage?: StorageLike | null, limit = RECENT_AIRPORTS_LIMIT): string[] {
  const next = dedupeRecentAirports(items, limit);
  try {
    storage?.setItem(RECENT_AIRPORTS_STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Ignore storage write failures; UI can still use in-memory recents.
  }
  return next;
}

export function rememberRecentAirport(current: string[], iata: string, limit = RECENT_AIRPORTS_LIMIT): string[] {
  return dedupeRecentAirports([normalizeIata(iata), ...current], limit);
}

export function buildRecentAirportSuggestions(
  recentAirports: string[],
  airportsByIata: Map<string, AirportIataEntry>,
  query: string,
  limit = RECENT_AIRPORTS_LIMIT,
): QuickSearchRecentAirportSuggestion[] {
  const suggestions: QuickSearchRecentAirportSuggestion[] = [];

  for (const iataRaw of recentAirports) {
    const iata = normalizeIata(iataRaw);
    if (!iata) continue;
    const entry = airportsByIata.get(iata);
    if (!matchesRecentAirportQuery(entry, iata, query)) continue;
    suggestions.push({
      iata,
      name: entry?.municipality || entry?.name || iata,
    });
    if (suggestions.length >= limit) break;
  }

  return suggestions;
}
