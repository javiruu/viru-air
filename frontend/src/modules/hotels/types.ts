export type HotelSearchOut = {
  id: string;
  canonical_name: string;
  city: string;
  country_code: string;
  stars: number | null;
};

export type HotelDetailOut = HotelSearchOut & {
  normalized_name: string;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  created_at: string;
  updated_at: string;
};

export type HotelRateOut = {
  id: string;
  hotel_id: string;
  tracked_offer_id: string | null;
  provider_run_id: string | null;
  provider: string;
  check_in: string;
  check_out: string;
  guests: number;
  room_label: string | null;
  meal_plan: string | null;
  cancellation_policy: string | null;
  currency: string;
  amount: number;
  availability_status: string;
  deep_link: string | null;
  collected_at: string;
};

export type HotelTrackingCandidate = {
  readonly hotel: HotelSearchOut;
  readonly rate: HotelRateOut;
};

export type HotelSavedSearchOut = {
  id: string;
  user_id: string;
  schema_version: "hotel-search-v1";
  fingerprint: string;
  query: Record<string, unknown>;
  label: string | null;
  status: "active" | "paused";
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
};

export type HotelWatchlistItemOut = {
  id: string;
  hotel_id: string;
  label: string | null;
  created_at: string;
};

export type HotelWatchlistEntry = {
  item: HotelWatchlistItemOut;
  hotel: HotelDetailOut | null;
  detailUnavailable: boolean;
};

export type HotelAlertRuleType = "price_below" | "price_above" | "percentage_drop" | "percentage_increase" | "provider_changed" | "availability_returned" | "parity_break";

export type HotelAlertRuleOut = {
  id: string;
  hotel_id: string;
  tracked_offer_id: string | null;
  rule_type: HotelAlertRuleType;
  threshold_amount: number | null;
  threshold_percent: number | null;
  compare_against: string;
  cooldown_minutes: number;
  evaluation_state: "clear" | "fired" | "suppressed" | "rearmed" | "invalid";
  last_fired_at: string | null;
  is_active: boolean;
};

export type HotelAlertEventOut = {
  id: string;
  rule_id: string | null;
  hotel_id: string;
  provider_run_id: string | null;
  event_type: string;
  message: string;
  trigger_value: number | null;
  event_fingerprint: string | null;
  snapshot_before_id: string | null;
  snapshot_after_id: string | null;
  baseline_snapshot_id: string | null;
  baseline_source: string | null;
  baseline_amount: number | null;
  baseline_currency: string | null;
  comparability_key: string | null;
  reason_code: string | null;
  eligibility_status: string | null;
  rule_version: string | null;
  evaluation_state: string | null;
  cooldown_until: string | null;
  created_at: string;
};

export type HotelCompSetOut = {
  id: string;
  name: string;
  anchor_hotel_id: string;
  created_at: string;
};

export type HotelCompSetMemberOut = {
  id: string;
  comp_set_id: string;
  hotel_id: string;
};

export type HotelCompSetDetailOut = HotelCompSetOut & {
  members: HotelCompSetMemberOut[];
};

export type HotelNearbySuggestionOut = {
  hotel_id: string;
  canonical_name: string;
  city: string;
  country_code: string;
  stars: number | null;
  distance_km: number;
};

export type HotelIngestOut = {
  provider_id: string;
  hotels_processed: number;
  rates_ingested: number;
  ambiguous_matches: number;
};

export type HotelParityOut = {
  check_in: string;
  check_out: string;
  guests: number;
  currency: string;
  provider_count: number;
  lowest_price: number | null;
  highest_price: number | null;
  average_price: number | null;
  spread_amount: number | null;
  spread_percent: number | null;
  is_parity_broken: boolean;
  status: string;
  label: string;
};

export type HotelsApiError = {
  status: number;
  message: string;
};

export type HotelTrackedOfferOut = {
  id: string;
  user_id: string;
  hotel_id: string;
  area_label: string | null;
  origin_query: string | null;
  latitude: number | null;
  longitude: number | null;
  radius_km: number | null;
  check_in: string | null;
  check_out: string | null;
  guests: number;
  room_label: string | null;
  meal_plan: string | null;
  cancellation_policy: string | null;
  provider: string;
  initial_price: number | null;
  current_price: number | null;
  target_price: number | null;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type HotelAreaSearchResultOut = {
  hotel_id: string;
  canonical_name: string;
  city: string;
  country_code: string;
  stars: number | null;
  distance_km: number;
  lowest_price: number | null;
  price_basis?: "total_stay" | "unknown";
  currency: string;
  provider: string | null;
  check_in: string;
  check_out: string;
  guests: number;
  has_tracking: boolean;
};

export type HotelAreaSearchV2CapabilityState =
  | "supported"
  | "supported_with_caveat"
  | "partial"
  | "planned"
  | "unavailable";

export type HotelAreaSearchV2Result = {
  hotel_id: string;
  canonical_name: string;
  city: string;
  country_code: string;
  stars: number | null;
  distance_km: number;
  price: {
    amount: number | null;
    currency: string;
    basis: "total_stay" | "per_night" | "unknown";
    status: "observed" | "unavailable" | "not_comparable" | "stale";
    observed_at: string | null;
  };
  stay_context: {
    check_in: string;
    check_out: string;
    guests: number;
    rooms: number | null;
  };
  provider: string | null;
  has_tracking: boolean;
  explanation: {
    primary_reason: string;
    codes: string[];
  };
};

export type HotelAreaSearchV2Out = {
  data: HotelAreaSearchV2Result[];
  meta: {
    contract_version: "hotels.results.v2";
    request_id: string;
    generated_at: string;
    result_state: "success" | "empty" | "partial";
    query: Record<string, unknown>;
    pagination: {
      mode: "none";
      returned: number;
      total: number;
      has_next: boolean;
      next_cursor: string | null;
      previous_cursor: string | null;
      sort: string;
    };
    freshness: {
      state: "fresh" | "recent" | "cached" | "historical" | "stale" | "unknown";
      observed_at: string | null;
      age_seconds: number | null;
      expires_at: string | null;
      mixed: boolean;
      requires_revalidation: boolean;
    };
    providers: Array<{
      id: string;
      operation: string;
      status: "ok" | "empty" | "timeout" | "rate_limited" | "disabled" | "failed" | "not_configured";
      results_count: number;
      used_for_results: boolean;
      fallback_used: boolean;
      latency_ms: number | null;
    }>;
    capabilities: Record<string, Record<string, HotelAreaSearchV2CapabilityState>>;
    warnings: Array<{
      code: string;
      severity: "info" | "warning" | "error";
      message_key: string;
      provider: string | null;
      scope: "collection" | "result" | "field";
      result_ids: string[];
      meta: Record<string, unknown>;
    }>;
  };
};

export type HotelTrackedOfferV2State =
  | "active"
  | "pending_context"
  | "pending_first_observation"
  | "partial"
  | "paused"
  | "unavailable"
  | "expired"
  | "archived";

export type HotelV2WarningOut = {
  code: string;
  severity: "info" | "warning" | "error";
  message_key: string;
  provider: string | null;
  scope: "collection" | "result" | "field";
  result_ids: string[];
  meta: Record<string, unknown>;
};

export type HotelV2PriceOut = {
  amount: number | null;
  currency: string;
  basis: "total_stay" | "per_night" | "unknown";
  status: "observed" | "unavailable" | "not_comparable" | "stale";
  observed_at: string | null;
};

export type HotelV2FreshnessOut = {
  state: "fresh" | "recent" | "cached" | "historical" | "stale" | "expired" | "unknown";
  observed_at: string | null;
  age_seconds: number | null;
  expires_at: string | null;
  mixed: boolean;
  requires_revalidation: boolean;
  policy_version: string | null;
  provenance_kind: "provider_observed" | "provider_revalidated" | "cache_current" | "historical_snapshot" | "fixture_demo" | "derived" | "unknown";
};

export type HotelTrackedOfferV2Out = {
  id: string;
  hotel_id: string;
  state_version: number;
  state: HotelTrackedOfferV2State;
  stay_context: {
    check_in: string | null;
    check_out: string | null;
    guests: number;
    currency: string;
  };
  latest_observation: {
    snapshot_id: string;
    legacy_collected_at: string;
    observed_at: string | null;
    provider: string;
    room_label: string | null;
    meal_plan: string | null;
    cancellation_policy: string | null;
    availability_status: string;
    conditions_completeness: string | null;
    canonical_stay_offer_id: string | null;
    price: HotelV2PriceOut;
    freshness: HotelV2FreshnessOut;
  } | null;
  capabilities: Record<string, HotelAreaSearchV2CapabilityState>;
  warnings: HotelV2WarningOut[];
};

export type HotelTrackedOffersV2Out = {
  data: HotelTrackedOfferV2Out[];
  meta: {
    contract_version: "hotels.tracking.v2";
    request_id: string;
    generated_at: string;
    result_state: "success" | "empty" | "partial";
    query: Record<string, unknown>;
    pagination: {
      mode: "none";
      returned: number;
      total: number;
      has_next: boolean;
      next_cursor: string | null;
      previous_cursor: string | null;
      sort: string;
    };
    freshness: HotelV2FreshnessOut;
    capabilities: Record<string, HotelAreaSearchV2CapabilityState>;
    warnings: HotelV2WarningOut[];
  };
};

export type HotelTrackedOfferHistoryV2Out = {
  tracked_offer_id: string;
  series: {
    identity: {
      comparability_key: string | null;
      status: "comparable" | "legacy_comparison" | "not_comparable";
      check_in: string | null;
      check_out: string | null;
      guests: number;
      currency: string;
      provider_scope: string | null;
    };
    points: Array<{
      snapshot_id: string;
      observed_at: string;
      observation_time_source: "provider_observed" | "legacy_collected";
      provider: string;
      availability_status: string;
      conditions_completeness: string | null;
      canonical_stay_offer_id: string | null;
      price_semantics: "total" | "unknown";
      price: HotelV2PriceOut;
      eligibility: "eligible" | "excluded";
      excluded_reason: string | null;
    }>;
    gaps: Array<Record<string, unknown>>;
    segments: Array<Record<string, unknown>>;
  };
  aggregates: {
    sample_size_total: number;
    sample_size_eligible: number;
    min_price: number | null;
    max_price: number | null;
    median_price: number | null;
    average_price: number | null;
    currency: string;
    price_semantics: "total" | "unknown";
    exclusions: Record<string, number>;
  };
  comparisons: {
    vs_initial: null;
    vs_previous: null;
    vs_minimum: null;
  };
  freshness: HotelV2FreshnessOut;
  capabilities: Record<string, HotelAreaSearchV2CapabilityState>;
};

export type HotelTrackedOfferV2CreateOut = {
  tracking: HotelTrackedOfferV2Out;
  creation: {
    outcome: "created" | "existing";
    semantic_dedupe: boolean;
  };
};

export type HotelTrackedOfferV2LifecycleOut = {
  tracking: HotelTrackedOfferV2Out;
  outcome: "applied" | "existing" | "expired";
};

export type HotelAreaResolveOut = {
  area_label: string;
  latitude: number;
  longitude: number;
  country_code: string;
  confidence: string;
  source: string;
};

