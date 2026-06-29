import type { SearchResult } from "../types";

export type QuickSearchSaveResultPayload = {
  readonly job_id?: string | null;
  readonly result_id: string | null;
  readonly origin_iata: string;
  readonly destination_iata: string;
  readonly travel_date: string;
  readonly price_total: number;
  readonly currency: string;
  readonly freshness_status: string | null;
  readonly requires_revalidation: boolean | null;
  readonly validation_status: string | null;
  readonly duration_total: number | null;
  readonly stop_count: number | null;
  readonly minutes_buffer: number | null;
  readonly distance_km_ground: number | null;
  readonly ranking_score: number | null;
  readonly freshness_ts: string | null;
  readonly deeplink_url: string | null;
  readonly itinerary_type: string | null;
  readonly group_id?: string | null;
};

type BuildQuickSearchSaveResultPayloadOptions = {
  readonly jobId?: string | null;
  readonly fallbackDeepLinkUrl?: string | null;
  readonly groupId?: string | null;
};

export function buildQuickSearchSaveResultPayload(
  result: SearchResult,
  options: BuildQuickSearchSaveResultPayloadOptions = {},
): QuickSearchSaveResultPayload {
  return {
    job_id: options.jobId,
    result_id: result.result_id ?? null,
    origin_iata: result.origin,
    destination_iata: result.destination,
    travel_date: result.travel_date,
    price_total: result.price_total ?? result.price,
    currency: result.currency,
    freshness_status: result.freshness?.status ?? null,
    requires_revalidation: result.freshness?.requires_revalidation ?? result.stale_data ?? null,
    validation_status: result.freshness?.validation_status ?? null,
    duration_total: result.duration_total_min ?? result.duration_total ?? null,
    stop_count: result.stop_count ?? null,
    minutes_buffer: result.minutes_buffer ?? null,
    distance_km_ground: result.distance_km_ground ?? null,
    ranking_score: result.ranking_score ?? null,
    freshness_ts: result.freshness_ts ?? null,
    deeplink_url: result.deeplink_url ?? options.fallbackDeepLinkUrl ?? null,
    itinerary_type: result.itinerary_type ?? null,
    group_id: options.groupId,
  };
}
