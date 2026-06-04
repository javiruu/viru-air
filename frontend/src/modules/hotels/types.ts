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
  currency: string;
  provider: string | null;
  check_in: string;
  check_out: string;
  guests: number;
  has_tracking: boolean;
};

export type HotelAreaResolveOut = {
  area_label: string;
  latitude: number;
  longitude: number;
  country_code: string;
  confidence: string;
  source: string;
};

