import type { QuickSearchCanonicalPayload } from "@/modules/quick-search/api/buildQuickSearchRequest";
import type { QuickSearchSortBy, SearchFilters, SearchResponse, SearchResult } from "@/modules/quick-search/types";

export const QUICK_SEARCH_EXPORT_PAGE_SIZE = 100;

export type QuickSearchExportCriteria = {
  origin: string;
  destination: string;
  origin_scope_iata: string[];
  destination_scope_iata: string[];
  travel_date: string;
  return_date: string | null;
  trip_type: "one_way" | "round_trip";
  adults: number;
  departure_window: {
    after: string | null;
    before: string | null;
  };
  flexibility: {
    days_before: number;
    days_after: number;
    apply_to_return: boolean;
  };
  route_scope: {
    include_nearby_origins: boolean;
    include_nearby_destinations: boolean;
    radius_km: number;
  };
  constraints: {
    include_stops: boolean;
    max_stops: number;
    buffer_min: string | null;
    strict_filters: boolean;
    exclude_origins: string[];
    exclude_destinations: string[];
  };
  visible_filters: {
    price_min: string | null;
    price_max: string | null;
    duration_max: string | null;
    sort_by: QuickSearchSortBy;
  };
};

type QuickSearchExportResult = {
  export_index: number;
  result_id: string | null;
  origin_iata: string;
  destination_iata: string;
  travel_date: string;
  departure_time_local: string | null;
  price: number;
  price_total: number | null;
  currency: string;
  source: string;
  duration_total: number | null;
  duration_total_min: number | null;
  stop_count: number | null;
  minutes_buffer: number | null;
  distance_km_ground: number | null;
  ranking_score: number | null;
  freshness_ts: string | null;
  stale_data: boolean;
  freshness: SearchResult["freshness"] | null;
  ai_preferred: boolean;
  ai_preferred_reason: string | null;
  deeplink_url: string | null;
  itinerary_type: string | null;
  legs: NonNullable<SearchResult["legs"]>;
  raw_result: SearchResult;
};

export type QuickSearchExportPayload = {
  schema_version: "quick-search-export.v1";
  exported_at: string;
  export_scope: "quick_search_all_results";
  search: {
    job_id: string | null;
    criteria: QuickSearchExportCriteria;
    backend_meta: SearchResponse["meta"] | null;
    filters: SearchFilters | null;
    result_count: number;
    backend_total_results: number;
    pages_fetched: number;
    export_page_size: number;
  };
  results: QuickSearchExportResult[];
};

export function buildQuickSearchExportPagePayload(
  payload: QuickSearchCanonicalPayload,
  page: number,
  sortBy: QuickSearchSortBy,
): QuickSearchCanonicalPayload {
  return {
    ...payload,
    pagination: {
      ...payload.pagination,
      page,
      page_size: QUICK_SEARCH_EXPORT_PAGE_SIZE,
      sort_by: sortBy,
    },
  };
}

export function buildQuickSearchExportPayload(input: {
  exportedAt: string;
  criteria: QuickSearchExportCriteria;
  results: SearchResult[];
  meta: SearchResponse["meta"] | null;
  filters: SearchFilters | null;
  jobId: string | null;
  pagesFetched: number;
}): QuickSearchExportPayload {
  const backendTotalResults = Math.max(
    input.results.length,
    Number(input.meta?.pagination?.total_results ?? input.results.length),
  );
  return {
    schema_version: "quick-search-export.v1",
    exported_at: input.exportedAt,
    export_scope: "quick_search_all_results",
    search: {
      job_id: input.jobId,
      criteria: input.criteria,
      backend_meta: input.meta,
      filters: input.filters,
      result_count: input.results.length,
      backend_total_results: backendTotalResults,
      pages_fetched: input.pagesFetched,
      export_page_size: QUICK_SEARCH_EXPORT_PAGE_SIZE,
    },
    results: input.results.map<QuickSearchExportResult>((result, index) => ({
      export_index: index + 1,
      result_id: result.result_id ?? null,
      origin_iata: result.origin,
      destination_iata: result.destination,
      travel_date: result.travel_date,
      departure_time_local: result.departure_time_local,
      price: result.price,
      price_total: result.price_total ?? null,
      currency: result.currency,
      source: result.source,
      duration_total: result.duration_total ?? null,
      duration_total_min: result.duration_total_min ?? null,
      stop_count: result.stop_count ?? null,
      minutes_buffer: result.minutes_buffer ?? null,
      distance_km_ground: result.distance_km_ground ?? null,
      ranking_score: result.ranking_score ?? null,
      freshness_ts: result.freshness_ts ?? null,
      stale_data: Boolean(result.stale_data),
      freshness: result.freshness ?? null,
      ai_preferred: Boolean(result.ai_preferred),
      ai_preferred_reason: result.ai_preferred_reason ?? null,
      deeplink_url: result.deeplink_url ?? null,
      itinerary_type: result.itinerary_type ?? null,
      legs: result.legs ?? [],
      raw_result: result,
    })),
  };
}
