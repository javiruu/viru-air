export type DoorToDoorLocationType = "city" | "address" | "station" | "saved_location" | "airport" | "airport_only";
export type DoorToDoorConfidence = "live" | "cached" | "estimated" | "deeplink" | "unavailable";
export type DoorToDoorSortBy = "best_balance" | "cheapest" | "fastest" | "fewest_changes";
export type DoorToDoorLuggage = "backpack" | "cabin" | "checked";

export type DoorToDoorLocation = {
  type: DoorToDoorLocationType;
  label: string;
  lat?: number | null;
  lng?: number | null;
  place_id?: string | null;
};

export type DoorToDoorPreferences = {
  min_airport_buffer_minutes: number;
  max_price?: number | null;
  passengers: number;
  luggage: DoorToDoorLuggage;
  allow_bus: boolean;
  allow_train: boolean;
  allow_rideshare: boolean;
  allow_shuttle: boolean;
  allow_taxi: boolean;
  allow_car: boolean;
  public_transport_only: boolean;
  sort_by: DoorToDoorSortBy;
};

export type DoorToDoorSource = {
  provider: string;
  source_provider: string;
  source_type: "api" | "open_data" | "aggregator" | "deeplink" | "scraper" | "mock" | "maps" | "estimate" | "external_deeplink";
  confidence: DoorToDoorConfidence;
  checked_at: string;
  expires_at?: string | null;
  booking_url?: string | null;
};

export type DoorToDoorAction = {
  id: string;
  provider: "google_maps" | "blablacar" | "goopti" | "gtfs";
  label: string;
  url: string;
  kind: "directions" | "provider_search" | "booking";
  opens_external: boolean;
  source_status: "external_search" | "real_result";
  price_status: "external" | "confirmed" | "unavailable";
  availability_status: "external" | "confirmed" | "unavailable";
  trust_copy: string;
};

export type DoorToDoorLeg = {
  type: "ground" | "flight";
  mode: "bus" | "train" | "rideshare" | "shuttle" | "taxi" | "car" | "walking" | "flight";
  from: string;
  to: string;
  departure_at?: string | null;
  arrival_at?: string | null;
  duration_minutes?: number | null;
  distance_meters?: number | null;
  price_min?: number | null;
  price_max?: number | null;
  provider?: string | null;
  booking_url?: string | null;
  source_type?: DoorToDoorSource["source_type"] | null;
  confidence?: DoorToDoorConfidence | null;
  actions?: DoorToDoorAction[];
};

export type DoorToDoorOptionStatus = "real_result" | "real_deeplink" | "estimate_only";
export type DoorToDoorDeepLinkKind = "directions" | "provider_search" | "booking";

export type DoorToDoorDeepLink = {
  url: string;
  label: string;
  kind: DoorToDoorDeepLinkKind;
  opens_external: boolean;
};

export type DoorToDoorPrice = {
  amount: number | null;
  currency: string | null;
  status: "confirmed" | "unavailable" | "external" | "estimated";
};

export type DoorToDoorOption = {
  id: string;
  label: string;
  description: string;
  status: DoorToDoorOptionStatus;
  total_price_min?: number | null;
  total_price_max?: number | null;
  price_per_person_min?: number | null;
  price_per_person_max?: number | null;
  currency: string;
  total_duration_minutes?: number | null;
  score?: number | null;
  transfer_count: number;
  airport_buffer_minutes?: number | null;
  confidence: DoorToDoorConfidence;
  source_types: DoorToDoorSource["source_type"][];
  sources: DoorToDoorSource[];
  legs: DoorToDoorLeg[];
  is_recommended: boolean;
  is_extended: boolean;
  deep_link?: DoorToDoorDeepLink | null;
  price?: DoorToDoorPrice | null;
  trust_copy?: string | null;
};

export type DecisionReasonKind = "price" | "buffer" | "tight_buffer" | "transfers" | "duration" | "confidence" | "completeness";

export type DecisionReason = {
  kind: DecisionReasonKind;
  label: string;
};

export type DecisionBadgeKind = "fastest" | "longest_buffer" | "fewest_changes" | "best_estimated_price" | "most_complete";

export type DecisionBadge = {
  kind: DecisionBadgeKind;
  label: string;
};

export type OptionDeltaSummary = {
  option_id: string;
  option_label: string;
  delta_price: number | null;
  delta_duration_minutes: number | null;
  delta_buffer_minutes: number | null;
  delta_transfer_count: number | null;
};

export type DoorToDoorFlight = {
  origin_airport: string;
  destination_airport: string;
  departure_at: string;
  arrival_at: string;
  flight_time_confidence: DoorToDoorConfidence;
};

export type DoorToDoorResponse = {
  flight: DoorToDoorFlight;
  summary: {
    recommended_option_id?: string | null;
    cheapest_option_id?: string | null;
    fastest_option_id?: string | null;
    fewest_changes_option_id?: string | null;
    history_id?: string | null;
    chosen_option_id?: string | null;
  };
  options: DoorToDoorOption[];
  warnings: Array<{ code: string; message: string; provider?: string | null }>;
  map_capabilities?: Partial<Record<DoorToDoorMapCapabilityKey, Omit<DoorToDoorMapCapability, "key">>>;
};

export type DoorToDoorSuggestion = DoorToDoorLocation & {
  id: string;
  subtitle: string;
  source_type: "local_static" | "mock" | "api" | "open_data";
};

export type DoorToDoorSuggestionsMeta = {
  provider_status: "api_live" | "fallback_active" | "provider_error";
  degraded_reason: string | null;
  used_region_codes: string[];
};

export type DoorToDoorSuggestionsResponse = {
  items: DoorToDoorSuggestion[];
  meta: DoorToDoorSuggestionsMeta;
};

export type DoorToDoorSavedLocation = DoorToDoorLocation & {
  id: string;
  updated_at: string;
};

export type DoorToDoorSavedPlace = {
  id: string;
  label: string;
  note: string;
  created_at: string;
  watch_id: string | null;
};

export type DoorToDoorHistoryItem = {
  id: string;
  watch_id: string;
  origin_label: string;
  final_destination_label: string;
  created_at: string;
  recommended_option_id?: string | null;
  recommended_label?: string | null;
  total_price_min?: number | null;
  total_price_max?: number | null;
  chosen_option_id?: string | null;
};

export type DoorToDoorProviderStatus = {
  name: string;
  enabled: boolean;
  status:
    | "functional_api"
    | "functional_mock"
    | "functional_deeplink"
    | "functional_open_data"
    | "functional_scraper"
    | "functional_estimate"
    | "functional_maps"
    | "scraper_base_only"
    | "deeplink_stub"
    | "pure_stub"
    | "disabled";
  source_type: DoorToDoorSource["source_type"];
  production_ready: boolean;
  supports_search: boolean;
  supports_booking_url: boolean;
  has_tests: boolean;
  notes?: string | null;
};

export type DoorToDoorMapCapabilityKey =
  | "navigation"
  | "traffic"
  | "transit"
  | "alternatives"
  | "street_view_preview"
  | "saved_places"
  | "nearby_pois"
  | "offline"
  | "incidents"
  | "eco_route";

export type DoorToDoorCapabilityState = "available" | "partial" | "planned" | "unavailable";

export type DoorToDoorMapCapability = {
  key: DoorToDoorMapCapabilityKey;
  state: DoorToDoorCapabilityState;
  source_type: DoorToDoorSource["source_type"] | "none";
  confidence: DoorToDoorConfidence;
  last_checked_at?: string | null;
  why_missing?: string | null;
};
