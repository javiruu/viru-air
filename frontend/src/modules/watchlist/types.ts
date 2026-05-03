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
