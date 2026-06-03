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
  provider: string;
  check_in: string;
  check_out: string;
  guests: number;
  room_label: string | null;
  meal_plan: string | null;
  cancellation_policy: string | null;
  currency: string;
  amount: number;
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

