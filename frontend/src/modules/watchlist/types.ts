export type Watch = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
  target_price?: number | null;
  status: string;
};

export type Snapshot = {
  captured_at_utc: string;
  raw_price: number;
  raw_currency: string;
  departure_time_local: string | null;
};

export type WatchDetail = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
  target_price?: number | null;
  status: string;
  latest_snapshot: Snapshot | null;
};

export type PriceSummary = {
  watch_id: string;
  count: number;
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
  latest_price: number | null;
  delta_pct: number | null;
};

export type PriceCalendarDay = {
  date: string;
  min_price: number;
  max_price: number;
  avg_price: number;
  snapshot_count: number;
  is_daily_min: boolean;
  is_daily_max: boolean;
  freshness_state?: "fresh" | "mixed" | "stale" | null;
};

export type PriceCalendarResponse = {
  watch_id: string;
  currency: string;
  days: PriceCalendarDay[];
};

export type PriceCompareWatch = {
  watch_id: string;
  route: string;
  travel_date: string;
  currency: string;
  latest_price: number | null;
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
  snapshot_count: number;
  volatility_hint: "low" | "medium" | "high" | "insufficient_data";
};

export type PriceCompareResponse = {
  currency_mode: "single" | "mixed";
  watches: PriceCompareWatch[];
  points: Array<{
    watch_id: string;
    points: Array<{ date: string; avg_price: number; snapshot_count: number; currency: string }>;
  }>;
};

export type HistoryRow = {
  watchId: string;
  origin: string;
  destination: string;
  travelDate: string;
  capturedAt: string;
  price: number;
  currency: string;
  departureTime: string | null;
};

export type ViewMode = "chart" | "calendar";
export type ListSort = "freshness" | "price_asc" | "price_desc" | "delta";
export type RangeWindow = "all" | "7" | "14" | "30" | "90";

export type HoverPoint = {
  x: number;
  y: number;
  date: string;
  capturedAt: string;
  price: number;
  currency: string;
  departureTime: string | null;
  color: string;
};

export type CompatibleResponse = {
  seed_iata: string;
  travel_date: string;
  compatible_iata: string[];
  source: string;
};

export type WatchMapRouteView = {
  watchId: string;
  origin: string;
  destination: string;
  originCoordinates: [number, number];
  destinationCoordinates: [number, number];
  priceCurrent: number | null;
  priceTarget: number | null;
  currency: string;
  trend: "up" | "down" | "flat";
  isPrimary: boolean;
  isCompared: boolean;
  volatility: number | null;
  freshnessTs: string | null;
};

export type WatchMapMode = "single" | "compare";

export type WatchMapInsight = {
  type: "opportunity" | "stability" | "speed" | "neutral";
  text: string;
  relatedWatchIds: string[];
};
