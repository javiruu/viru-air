import { SearchResponse, SearchResponseRaw, SearchResult, SearchResultRaw } from "@/modules/quick-search/types";

function extractRankingScore(item: SearchResultRaw): number | null {
  if (typeof item.ranking_score === "number" && Number.isFinite(item.ranking_score)) {
    return item.ranking_score;
  }
  if (typeof item.score === "number" && Number.isFinite(item.score)) {
    return item.score;
  }
  if (item.score && typeof item.score === "object") {
    const finalScore = item.score.final_score;
    if (typeof finalScore === "number" && Number.isFinite(finalScore)) {
      return finalScore;
    }
  }
  return null;
}

export function normalizeQuickSearchResults(results: SearchResultRaw[]): SearchResult[] {
  return results.map((item, idx) => ({
    ...item,
    result_id: item.result_id ?? `${item.origin}-${item.destination}-${item.travel_date}-${idx}`,
    price_total: Number.isFinite(item.price_total) ? item.price_total : item.price,
    duration_total_min: item.duration_total_min ?? item.duration_total ?? null,
    stop_count: item.stop_count ?? null,
    risk_label: item.risk_label ?? null,
    minutes_buffer: item.minutes_buffer ?? null,
    distance_km_ground: item.distance_km_ground ?? null,
    ranking_score: extractRankingScore(item),
    freshness_ts: item.freshness_ts ?? null,
    stale_data: Boolean(item.stale_data),
    deeplink_url: item.deeplink_url ?? null,
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
