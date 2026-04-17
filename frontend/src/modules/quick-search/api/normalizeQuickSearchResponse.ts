import { SearchResponse, SearchResponseRaw, SearchResult, SearchResultRaw } from "@/modules/quick-search/types";

function toFiniteNumber(value: unknown, fallback: number | null = null): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function toOptionalString(value: unknown, fallback: string | null = null): string | null {
  if (typeof value === "string") return value;
  return fallback;
}

function toRequiredString(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) return value;
  return fallback;
}

function extractRankingScore(item: SearchResultRaw): number | null {
  const directScore = toFiniteNumber(item.ranking_score);
  if (directScore !== null) return directScore;
  const numericBreakdownScore = toFiniteNumber(item.score);
  if (numericBreakdownScore !== null) return numericBreakdownScore;
  if (item.score && typeof item.score === "object") {
    const finalScore = toFiniteNumber(item.score.final_score);
    if (finalScore !== null) {
      return finalScore;
    }
  }
  return null;
}

export function normalizeQuickSearchResults(results: SearchResultRaw[]): SearchResult[] {
  return results.map((item, idx) => ({
    ...item,
    result_id:
      toOptionalString(item.result_id) ??
      `${toRequiredString(item.origin, "UNK")}-${toRequiredString(item.destination, "UNK")}-${toRequiredString(item.travel_date, "unknown-date")}-${idx}`,
    origin: toRequiredString(item.origin, "UNK"),
    destination: toRequiredString(item.destination, "UNK"),
    travel_date: toRequiredString(item.travel_date, ""),
    departure_time_local: toOptionalString(item.departure_time_local),
    price: toFiniteNumber(item.price, 0) ?? 0,
    price_total: toFiniteNumber(item.price_total, toFiniteNumber(item.price, 0) ?? 0) ?? 0,
    currency: toRequiredString(item.currency, "EUR"),
    source: toRequiredString(item.source, ""),
    duration_total: toFiniteNumber(item.duration_total),
    duration_total_min: toFiniteNumber(item.duration_total_min, toFiniteNumber(item.duration_total)),
    stop_count: toFiniteNumber(item.stop_count),
    risk_label: item.risk_label ?? null,
    minutes_buffer: toFiniteNumber(item.minutes_buffer),
    distance_km_ground: toFiniteNumber(item.distance_km_ground),
    ranking_score: extractRankingScore(item),
    freshness_ts: toOptionalString(item.freshness_ts),
    stale_data: Boolean(item.stale_data),
    deeplink_url: toOptionalString(item.deeplink_url),
    itinerary_type: item.itinerary_type ?? (item.stop_count && item.stop_count > 0 ? "self_connect" : "direct"),
    legs: item.legs ?? item.segments?.legs ?? [],
  }));
}

export function normalizeQuickSearchResponse(response: SearchResponseRaw): SearchResponse {
  return {
    ...response,
    results: normalizeQuickSearchResults(response.results || []),
  };
}
