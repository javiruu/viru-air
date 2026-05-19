export type QuickSearchLeg = {
  origin_iata: string;
  destination_iata: string;
  dep_ts: string;
  arr_ts: string;
  flight_num?: string | null;
  price?: number | null;
};

export type QuickSearchScoreBreakdown = {
  final_score?: number | null;
  price_component?: number | null;
  origin_seed_penalty?: number | null;
  destination_seed_penalty?: number | null;
  distance_penalty_total?: number | null;
  pair_category?: string | null;
  soft_filters_weight_applied?: number | null;
};

export type SearchResultRaw = {
  result_id?: string | null;
  origin: string;
  destination: string;
  travel_date: string;
  departure_time_local: string | null;
  price: number;
  price_total?: number;
  currency: string;
  source: string;
  duration_total?: number | null;
  duration_total_min?: number | null;
  stop_count?: number | null;
  risk_label?: string | null;
  minutes_buffer?: number | null;
  distance_km_ground?: number | null;
  ranking_score?: number | null;
  score?: QuickSearchScoreBreakdown | number | null;
  freshness_ts?: string | null;
  stale_data?: boolean;
  deeplink_url?: string | null;
  itinerary_type?: string | null;
  legs?: QuickSearchLeg[];
  segments?: {
    legs?: QuickSearchLeg[];
  };
};

export type SearchResult = Omit<SearchResultRaw, "score"> & {
  ranking_score?: number | null;
  legs?: QuickSearchLeg[];
};

export type SearchFilters = {
  applied?: Record<string, unknown>;
  relaxed?: string[];
  warnings?: string[];
  discarded?: number;
};

export type SearchResponseRaw = {
  job_id?: string;
  meta?: {
    query?: Record<string, unknown>;
    generated_at?: string;
    currency?: string;
    timezone?: string;
    stale_data?: boolean;
    freshness_ts?: string | null;
    total_candidates?: number;
    returned?: number;
    truncated?: boolean;
    rescue?: {
      attempted: boolean;
      applied_steps: string[];
      winning_step: string | null;
      pass_summaries: Array<{
        step: string;
        result_count: number;
        warnings: string[];
      }>;
    };
    query_signature?: string;
    planned_route_scope?: {
      winning_step?: string;
      origin_seed_pool_effective?: string[];
      destination_seed_pool_effective?: string[];
      origin_expanded_iata?: string[];
      destination_expanded_iata?: string[];
      origin_expanded_count?: number;
      destination_expanded_count?: number;
    };
    warnings?: Array<{ code: string; message: string }>;
    provider_status?: {
      provider: string;
      availability: { status: "ok" | "failed" };
      fares: { status: "ok" | "failed" };
      overall: "ok" | "partial_degraded" | "total_outage";
      partial_results_served: boolean;
      total_outage: boolean;
    };
  };
  results: SearchResultRaw[];
  filters?: SearchFilters;
};

export type SearchResponse = Omit<SearchResponseRaw, "results"> & {
  results: SearchResult[];
  filters?: SearchFilters;
};

export type QuickSearchCalendarDayHintBucket = "low" | "mid" | "high" | "none";
export type QuickSearchCalendarAggregationMode = "min" | "median" | "fixed_route";
export type QuickSearchCalendarScopeMode = "iata" | "country_mixed" | "country_country";
export type QuickSearchCalendarBucketMode = "monthly_terciles" | "guidelines";
export type QuickSearchCalendarGuidelineThresholds = {
  low_max: number;
  mid_max: number;
  currency: "EUR" | "USD" | "GBP";
};

export type QuickSearchCalendarDayHint = {
  date: string;
  min_price: number | null;
  bucket: QuickSearchCalendarDayHintBucket;
  no_data_reason?: string | null;
};

export type QuickSearchCalendarHintsResponse = {
  days: QuickSearchCalendarDayHint[];
  meta: {
    currency: string;
    cache_ttl_sec: number;
    cache_hit: boolean;
    partial: boolean;
    scope_mode?: QuickSearchCalendarScopeMode;
    ranked_airports?: {
      origin?: string[];
      destination?: string[];
      origin_count?: number;
      destination_count?: number;
    };
    ranked_routes_count?: number;
    aggregation_mode?: QuickSearchCalendarAggregationMode;
    bucket_mode?: QuickSearchCalendarBucketMode;
    guideline_thresholds_effective?: QuickSearchCalendarGuidelineThresholds | null;
  };
};

export type DeepLinkResponse = {
  status: string;
  url: string;
  fallback_url?: string;
  strategy?: string;
};

export type WeatherDay = {
  date: string;
  tempMax: number;
  tempMin: number;
  precipProb: number | null;
  description: string;
};

export type WeatherReport = {
  iata: string;
  name: string;
  city: string;
  country: string;
  days: WeatherDay[];
};

export type Pref = {
  default_radius_km: number;
  include_stops_default: boolean;
  include_nearby_origins_default: boolean;
  include_nearby_destinations_default: boolean;
  country_price_hint_mode_default: QuickSearchCalendarAggregationMode;
  calendar_hint_bucket_mode_default: QuickSearchCalendarBucketMode;
  calendar_hint_guideline_low_max_default: number;
  calendar_hint_guideline_mid_max_default: number;
  avoid_departure_before: string | null;
  depart_before_default: string | null;
  strict_filters_default: boolean;
  preferred_currency: string;
  language: string;
};

export type RegionPref = {
  language: string;
  region: string;
  time_format: string;
  decimal_separator: string;
  currency: string;
};

export type QuickSearchField =
  | "origin_iata"
  | "destination_iata"
  | "travel_date"
  | "price_min"
  | "price_max"
  | "duration_max"
  | "buffer_min";
export type QuickSearchFieldErrors = Partial<Record<QuickSearchField, string>>;
export type QuickSearchAutocompleteField = "origin" | "destination";
export type QuickSearchMode = "quick-search" | "recommendations";
export type QuickSearchTagTone = "low" | "med" | "high" | "fresh" | "stale";
export type QuickSearchExplainTag = { key: string; label: string; tone: QuickSearchTagTone };
export type QuickSearchTripType = "one_way" | "round_trip" | "round_trip_incomplete";
export type QuickSearchLoadingPhase = "idle" | "requesting" | "response_parsed" | "client_done" | "committed";
export type QuickSearchLoadingSubcheckStatus = "pending" | "active" | "done";
export type ZeroResultRelaxAction =
  | "disable_strict"
  | "increase_duration"
  | "open_radius_150"
  | "clear_exclusions"
  | "open_date_flex";
export type SummaryHighlightKey = "strict" | "duration" | "radius" | "exclusions" | "date_flex" | null;

export type RelaxUndoPayload =
  | { action: "disable_strict"; strictFilters: boolean }
  | { action: "increase_duration"; durationMax: string }
  | {
      action: "open_radius_150";
      includeNearbyOrigins: boolean;
      includeNearbyDestinations: boolean;
      radiusKm: number;
    }
  | {
      action: "clear_exclusions";
      excludeOrigins: string[];
      excludeDestinations: string[];
      excludeOriginInput: string;
      excludeDestinationInput: string;
    }
  | {
      action: "open_date_flex";
      daysBefore: number;
      daysAfter: number;
      applyFlexReturn: boolean;
    };

export type AirportIataEntry = {
  iata: string;
  name: string;
  municipality: string;
  country_code: string;
  iso_region: string;
  type: string;
};

export type CountryAirports = {
  code: string;
  name: string;
  airports: AirportIataEntry[];
};
