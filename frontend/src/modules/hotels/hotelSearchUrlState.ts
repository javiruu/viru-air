import type { HotelAreaResolveOut } from "./types";

export type HotelSearchMode = "name" | "area";
export type HotelReturnPanel = "search" | "detail" | "mis-hoteles";

export type HotelSearchUrlState = {
  panel: HotelReturnPanel;
  mode: HotelSearchMode;
  query: string;
  city: string;
  areaQuery: string;
  areaResolved: HotelAreaResolveOut | null;
  checkIn: string;
  checkOut: string;
  guests: number;
  radiusKm: number;
  useProvider: boolean;
  hasSearched: boolean;
  selectedHotelId: string | null;
};

export type HotelSearchUrlInput = Pick<
  HotelSearchUrlState,
  | "mode"
  | "query"
  | "city"
  | "areaQuery"
  | "areaResolved"
  | "checkIn"
  | "checkOut"
  | "guests"
  | "radiusKm"
  | "useProvider"
  | "hasSearched"
  | "selectedHotelId"
> & {
  panel?: HotelReturnPanel;
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const AREA_CONFIDENCES = new Set(["low", "medium", "high"]);
const AREA_SOURCES = new Set(["internal", "nominatim", "url"]);

function clean(value: string | null): string {
  return value?.trim() ?? "";
}

function readBoundedInteger(value: string | null, fallback: number, min: number, max: number): number {
  const normalized = clean(value);
  if (!normalized) return fallback;
  const parsed = Number(normalized);
  if (!Number.isInteger(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function isRealIsoDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year
    && parsed.getUTCMonth() === month - 1
    && parsed.getUTCDate() === day;
}

function readDate(value: string | null): string {
  const normalized = clean(value);
  return isRealIsoDate(normalized) ? normalized : "";
}

function readBoolean(value: string | null): boolean {
  return value === "1" || value === "true";
}

function readAreaCountry(value: string | null): string {
  const normalized = clean(value).toUpperCase();
  return /^[A-Z]{2}$/.test(normalized) ? normalized : "ES";
}

function readAreaConfidence(value: string | null): string {
  const normalized = clean(value).toLowerCase();
  return AREA_CONFIDENCES.has(normalized) ? normalized : "medium";
}

function readAreaSource(value: string | null): string {
  const normalized = clean(value).toLowerCase();
  return AREA_SOURCES.has(normalized) ? normalized : "url";
}

export function readHotelSearchUrlState(params: Pick<URLSearchParams, "get">): HotelSearchUrlState {
  const mode: HotelSearchMode = params.get("mode") === "area" ? "area" : "name";
  const areaLabel = clean(params.get("area"));
  const areaLatitudeRaw = clean(params.get("area_lat"));
  const areaLongitudeRaw = clean(params.get("area_lng"));
  const areaLatitude = Number(areaLatitudeRaw);
  const areaLongitude = Number(areaLongitudeRaw);
  const hasResolvedArea =
    areaLabel.length > 0
    && areaLatitudeRaw.length > 0
    && areaLongitudeRaw.length > 0
    && Number.isFinite(areaLatitude)
    && areaLatitude >= -90
    && areaLatitude <= 90
    && Number.isFinite(areaLongitude)
    && areaLongitude >= -180
    && areaLongitude <= 180;

  const selectedHotelId = clean(params.get("hotel_id")) || null;
  const panel = params.get("panel") === "mis-hoteles"
    ? "mis-hoteles"
    : params.get("panel") === "detail" || selectedHotelId
      ? "detail"
      : "search";

  return {
    panel,
    mode,
    query: clean(params.get("q")),
    city: clean(params.get("city")),
    areaQuery: areaLabel,
    areaResolved: hasResolvedArea
      ? {
          area_label: areaLabel,
          latitude: areaLatitude,
          longitude: areaLongitude,
          country_code: readAreaCountry(params.get("area_country")),
          confidence: readAreaConfidence(params.get("area_confidence")),
          source: readAreaSource(params.get("area_source")),
        }
      : null,
    checkIn: readDate(params.get("check_in")),
    checkOut: readDate(params.get("check_out")),
    guests: readBoundedInteger(params.get("guests"), 2, 1, 20),
    radiusKm: readBoundedInteger(params.get("radius"), 10, 1, 50),
    useProvider: readBoolean(params.get("provider")),
    hasSearched: readBoolean(params.get("searched")),
    selectedHotelId,
  };
}

export function canonicalizeHotelSearchQuery(query: string): string {
  const params = new URLSearchParams(query);
  params.sort();
  return params.toString();
}

export function buildHotelSearchQuery(input: HotelSearchUrlInput): string {
  const params = new URLSearchParams();
  const query = clean(input.query);
  const city = clean(input.city);
  const areaQuery = clean(input.areaQuery);

  if (input.panel === "mis-hoteles") params.set("panel", "mis-hoteles");
  if (input.mode === "area") params.set("mode", "area");
  if (query) params.set("q", query);
  if (city) params.set("city", city);
  if (input.mode === "area" && areaQuery) params.set("area", areaQuery);
  if (input.mode === "area" && input.areaResolved) {
    params.set("area_lat", String(input.areaResolved.latitude));
    params.set("area_lng", String(input.areaResolved.longitude));
    params.set("area_country", input.areaResolved.country_code);
    params.set("area_confidence", input.areaResolved.confidence);
    params.set("area_source", input.areaResolved.source);
  }
  if (input.checkIn) params.set("check_in", input.checkIn);
  if (input.checkOut) params.set("check_out", input.checkOut);
  if (input.guests !== 2) params.set("guests", String(input.guests));
  if (input.radiusKm !== 10) params.set("radius", String(input.radiusKm));
  if (input.useProvider) params.set("provider", "1");
  if (input.hasSearched) params.set("searched", "1");
  if (input.selectedHotelId) {
    params.set("hotel_id", input.selectedHotelId);
    if (input.panel !== "mis-hoteles") params.set("panel", "detail");
  }

  return params.toString();
}

export function buildRestoredHotelSearchQuery(query: Record<string, unknown>): string | null {
  if (query.schema !== "hotel-search-v1") return null;
  const paramsValue = query.params;
  if (!paramsValue || typeof paramsValue !== "object" || Array.isArray(paramsValue)) return null;

  const rawParams = new URLSearchParams();
  Object.entries(paramsValue as Record<string, unknown>).forEach(([key, value]) => {
    if (typeof value === "string") rawParams.set(key, value);
  });

  const state = readHotelSearchUrlState(rawParams);
  if (state.mode === "area" && !isHotelDateRangeValid(state.checkIn, state.checkOut)) return null;
  const safeCheckIn = state.checkIn && state.checkOut && isHotelDateRangeValid(state.checkIn, state.checkOut)
    ? state.checkIn
    : "";
  const safeCheckOut = safeCheckIn ? state.checkOut : "";

  return buildHotelSearchQuery({
    panel: "search",
    mode: state.mode,
    query: state.query,
    city: state.city,
    areaQuery: state.areaQuery,
    areaResolved: state.areaResolved,
    checkIn: safeCheckIn,
    checkOut: safeCheckOut,
    guests: state.guests,
    radiusKm: state.radiusKm,
    useProvider: state.useProvider,
    hasSearched: false,
    selectedHotelId: null,
  });
}

export function isHotelDateRangeValid(checkIn: string, checkOut: string): boolean {
  return Boolean(isRealIsoDate(checkIn) && isRealIsoDate(checkOut) && checkOut > checkIn);
}

export function hasHotelSearchIntent(state: HotelSearchUrlState): boolean {
  if (state.mode === "area") {
    return Boolean(state.areaResolved && isHotelDateRangeValid(state.checkIn, state.checkOut) && state.guests > 0);
  }
  return Boolean(state.query || state.city);
}
