export type DoorToDoorLocationType = "city" | "address" | "station" | "saved_location" | "airport" | "airport_only";
export type DoorToDoorConfidence = "live" | "cached" | "estimated" | "deeplink" | "unavailable";
export type DoorToDoorRiskLevel = "low" | "medium" | "high" | "unknown";
export type DoorToDoorSortBy = "best_balance" | "cheapest" | "lowest_risk" | "fastest" | "fewest_changes";
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
  source_type: "api" | "open_data" | "aggregator" | "deeplink" | "scraper" | "mock" | "maps" | "estimate";
  confidence: DoorToDoorConfidence;
  checked_at: string;
  expires_at?: string | null;
  booking_url?: string | null;
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
  risk_level: DoorToDoorRiskLevel;
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
    lowest_risk_option_id?: string | null;
    fastest_option_id?: string | null;
    fewest_changes_option_id?: string | null;
    history_id?: string | null;
    chosen_option_id?: string | null;
  };
  options: DoorToDoorOption[];
  warnings: Array<{ code: string; message: string; provider?: string | null }>;
};

export type DoorToDoorSuggestion = DoorToDoorLocation & {
  id: string;
  subtitle: string;
  source_type: "local_static" | "mock" | "api";
};

export type DoorToDoorSavedLocation = DoorToDoorLocation & {
  id: string;
  updated_at: string;
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
  risk_level?: DoorToDoorRiskLevel | null;
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
