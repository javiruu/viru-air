import { normalizeQuickSearchResults } from "@/modules/quick-search/api/normalizeQuickSearchResponse";
import { parseNumericInput } from "@/modules/quick-search/searchCriteria";
import type { QuickSearchSortBy, SearchResult } from "@/modules/quick-search/types";

type QuickSearchVisibleResultsArgs = {
  results: SearchResult[];
  priceMin: string;
  priceMax: string;
  durationMax: string;
  sortBy: QuickSearchSortBy;
};

export function deriveQuickSearchVisibleResults({
  results,
  priceMin,
  priceMax,
  durationMax,
  sortBy,
}: QuickSearchVisibleResultsArgs): SearchResult[] {
  const normalizedResults = normalizeQuickSearchResults(results);
  const min = parseNumericInput(priceMin, { min: 0 });
  const max = parseNumericInput(priceMax, { min: 0 });
  const durMax = parseNumericInput(durationMax, { min: 1 });

  let list = normalizedResults.filter((item) => {
    if (min !== null && item.price_total !== undefined && item.price_total < min) return false;
    if (max !== null && item.price_total !== undefined && item.price_total > max) return false;
    if (durMax !== null && item.duration_total_min != null && item.duration_total_min > durMax) return false;
    return true;
  });

  list = list.slice().sort((a, b) => {
    if (sortBy === "price") return (a.price_total ?? 0) - (b.price_total ?? 0);
    if (sortBy === "duration") return (a.duration_total ?? 99999) - (b.duration_total ?? 99999);
    if (sortBy === "freshness") {
      const aTs = a.freshness_ts ? new Date(a.freshness_ts).getTime() : 0;
      const bTs = b.freshness_ts ? new Date(b.freshness_ts).getTime() : 0;
      return bTs - aTs;
    }
    return (b.ranking_score ?? 0) - (a.ranking_score ?? 0);
  });

  return list;
}
