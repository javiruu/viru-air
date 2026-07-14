/**
 * Shared utilities for URL search param state between /quick-search and /watchlist.
 *
 * Provides:
 * - Sanitization/validation helpers for common param types (IATA, ISO date, etc.)
 * - A function to build a watchlist navigation URL from quick-search form state
 * - A function to read watchlist navigation params from the URL
 * - A function to build a quick-search URL from form state for persistence
 */

// ── Param name constants (shared contract) ───────────────────────────

/** Shared param names used by both QuickSearch and Watchlist. */
export const PARAM_ORIGIN = "origin";
export const PARAM_DESTINATION = "destination";
export const PARAM_TRAVEL_DATE = "travelDate";

export const WL_PARAM_ORIGIN = PARAM_ORIGIN;
export const WL_PARAM_DESTINATION = PARAM_DESTINATION;
export const WL_PARAM_TRAVEL_DATE = PARAM_TRAVEL_DATE;
export const WL_PARAM_WATCH_ID = "watchId";
export const WL_PARAM_VIEW = "view";
export const WL_PARAM_RANGE = "range";

export const QS_PARAM_ORIGIN = PARAM_ORIGIN;
export const QS_PARAM_DESTINATION = PARAM_DESTINATION;
export const QS_PARAM_ADDITIONAL_ORIGINS = "origins";
export const QS_PARAM_ADDITIONAL_DESTINATIONS = "destinations";
export const QS_PARAM_TRAVEL_DATE = PARAM_TRAVEL_DATE;
export const QS_PARAM_RETURN_DATE = "returnDate";
export const QS_PARAM_IS_RETURN = "isReturn";
export const QS_PARAM_ADULTS = "adults";
export const QS_PARAM_FLEX_BEFORE = "flexB";
export const QS_PARAM_FLEX_AFTER = "flexA";
export const QS_PARAM_RADIUS = "radius";
export const QS_PARAM_STRICT = "strict";

// ── Sanitization helpers ─────────────────────────────────────────────

/** Validates a 3-letter IATA code, returns uppercase or empty string. */
export function sanitizeIata(raw: string | null | undefined): string {
  if (!raw) return "";
  const trimmed = raw.trim().toUpperCase();
  return /^[A-Z]{3}$/.test(trimmed) ? trimmed : "";
}

/** Validates an ISO date string (YYYY-MM-DD), returns it or empty string. */
export function sanitizeIsoDate(raw: string | null | undefined): string {
  if (!raw) return "";
  const trimmed = raw.trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(trimmed) ? trimmed : "";
}

export function sanitizeWatchId(raw: string | null | undefined): string {
  if (!raw) return "";
  const trimmed = raw.trim();
  return /^[A-Za-z0-9_-]{6,80}$/.test(trimmed) ? trimmed : "";
}

/** Validates an ISO month string (YYYY-MM), returns it or empty string. */
export function sanitizeIsoMonth(raw: string | null | undefined): string {
  if (!raw) return "";
  const trimmed = raw.trim();
  return /^\d{4}-\d{2}$/.test(trimmed) ? trimmed : "";
}

/** Parses a positive integer param, returns the number or null. */
export function sanitizePositiveInt(
  raw: string | null | undefined,
  min = 1,
  max = 999,
): number | null {
  if (!raw) return null;
  const n = Number(raw.trim());
  return Number.isFinite(n) && Number.isInteger(n) && n >= min && n <= max ? n : null;
}

/** Parses a clamped integer param with default. */
export function sanitizeClampedInt(
  raw: string | null | undefined,
  min: number,
  max: number,
  fallback: number,
): number {
  if (!raw) return fallback;
  const n = Number(raw.trim());
  if (!Number.isFinite(n) || !Number.isInteger(n)) return fallback;
  return Math.max(min, Math.min(max, n));
}

/** Parses a "0"|"1" boolean flag. */
export function sanitizeFlag(raw: string | null | undefined): boolean | null {
  if (raw === "1" || raw?.toLowerCase() === "true") return true;
  if (raw === "0" || raw?.toLowerCase() === "false") return false;
  return null;
}

/**
 * Validates a view mode param ("chart" | "calendar").
 */
export function sanitizeViewMode(
  raw: string | null | undefined,
  fallback: "chart" | "calendar" = "chart",
): "chart" | "calendar" {
  if (raw === "chart" || raw === "calendar") return raw;
  return fallback;
}

/**
 * Validates a range param ("30" | "all").
 */
export function sanitizeRangeParam(
  raw: string | null | undefined,
  fallback: "30" | "all" = "30",
): "30" | "all" {
  if (raw === "30" || raw === "all") return raw;
  return fallback;
}

// ── QuickSearch → Watchlist navigation URL builder ───────────────────

export type QuickSearchWatchlistNav = {
  origin: string;
  destination: string;
  travelDate: string;
  watchId?: string;
};

/**
 * Builds the URL to navigate from QuickSearch to Watchlist with context params.
 * Only includes valid, non-empty params.
 */
export function buildWatchlistUrl(params: QuickSearchWatchlistNav): string {
  const search = new URLSearchParams();
  const origin = sanitizeIata(params.origin);
  const destination = sanitizeIata(params.destination);
  const travelDate = sanitizeIsoDate(params.travelDate);
  const watchId = sanitizeWatchId(params.watchId);

  if (watchId) search.set(WL_PARAM_WATCH_ID, watchId);
  if (origin) search.set(WL_PARAM_ORIGIN, origin);
  if (destination) search.set(WL_PARAM_DESTINATION, destination);
  if (travelDate) search.set(WL_PARAM_TRAVEL_DATE, travelDate);

  const qs = search.toString();
  return qs ? `/watchlist?${qs}` : "/watchlist";
}

/**
 * Reads navigation params from a URLSearchParams object.
 * Returns sanitized values — empty strings for missing/invalid params.
 */
export function readWatchlistNavigationParams(
  sp: URLSearchParams,
): QuickSearchWatchlistNav {
  return {
    origin: sanitizeIata(sp.get(WL_PARAM_ORIGIN)),
    destination: sanitizeIata(sp.get(WL_PARAM_DESTINATION)),
    travelDate: sanitizeIsoDate(sp.get(WL_PARAM_TRAVEL_DATE)),
    watchId: sanitizeWatchId(sp.get(WL_PARAM_WATCH_ID)),
  };
}

/**
 * Reads watchlist view state params from a URLSearchParams object.
 */
export function readWatchlistViewParams(sp: URLSearchParams): {
  view: "chart" | "calendar";
  range: "30" | "all";
} {
  return {
    view: sanitizeViewMode(sp.get(WL_PARAM_VIEW)),
    range: sanitizeRangeParam(sp.get(WL_PARAM_RANGE)),
  };
}

/**
 * Builds the watchlist URL search params string from current view state.
 */
export function buildWatchlistViewSearchParams(params: {
  origin?: string;
  destination?: string;
  travelDate?: string;
  watchId?: string;
  view?: "chart" | "calendar";
  range?: "30" | "all";
}): string {
  const search = new URLSearchParams();

  const origin = params.origin ? sanitizeIata(params.origin) : "";
  const destination = params.destination ? sanitizeIata(params.destination) : "";
  const travelDate = params.travelDate ? sanitizeIsoDate(params.travelDate) : "";
  const watchId = params.watchId ? sanitizeWatchId(params.watchId) : "";

  if (watchId) search.set(WL_PARAM_WATCH_ID, watchId);
  if (origin) search.set(WL_PARAM_ORIGIN, origin);
  if (destination) search.set(WL_PARAM_DESTINATION, destination);
  if (travelDate) search.set(WL_PARAM_TRAVEL_DATE, travelDate);
  if (params.view && params.view !== "chart") search.set(WL_PARAM_VIEW, params.view);
  if (params.range && params.range !== "30") search.set(WL_PARAM_RANGE, params.range);

  return search.toString();
}

// ── QuickSearch URL persistence ──────────────────────────────────────

export type QuickSearchUrlState = {
  origin: string;
  destination: string;
  additionalOrigins: string[];
  additionalDestinations: string[];
  travelDate: string;
  returnDate: string;
  isReturn: boolean;
  adults: number;
  flexBefore: number;
  flexAfter: number;
  radius: number;
  strict: boolean;
};

/**
 * Reads quick-search form state from URLSearchParams.
 */
export function readQuickSearchUrlState(sp: URLSearchParams): QuickSearchUrlState {
  const isReturnRaw = sanitizeFlag(sp.get(QS_PARAM_IS_RETURN));
  const readAdditionalIata = (param: string) => Array.from(new Set(
    (sp.get(param) ?? "").split(",").map((value) => sanitizeIata(value)).filter(Boolean),
  )).slice(0, 5);
  return {
    origin: sanitizeIata(sp.get(QS_PARAM_ORIGIN)),
    destination: sanitizeIata(sp.get(QS_PARAM_DESTINATION)),
    additionalOrigins: readAdditionalIata(QS_PARAM_ADDITIONAL_ORIGINS),
    additionalDestinations: readAdditionalIata(QS_PARAM_ADDITIONAL_DESTINATIONS),
    travelDate: sanitizeIsoDate(sp.get(QS_PARAM_TRAVEL_DATE)),
    returnDate: sanitizeIsoDate(sp.get(QS_PARAM_RETURN_DATE)),
    isReturn: isReturnRaw ?? false,
    adults: sanitizeClampedInt(sp.get(QS_PARAM_ADULTS), 1, 9, 1),
    flexBefore: sanitizeClampedInt(sp.get(QS_PARAM_FLEX_BEFORE), 0, 3, 0),
    flexAfter: sanitizeClampedInt(sp.get(QS_PARAM_FLEX_AFTER), 0, 3, 0),
    radius: sanitizeClampedInt(sp.get(QS_PARAM_RADIUS), 10, 500, 150),
    strict: sanitizeFlag(sp.get(QS_PARAM_STRICT)) ?? true,
  };
}

/**
 * Builds the quick-search URL search params string from current form state.
 * Only includes params that differ from defaults.
 */
export function buildQuickSearchSearchParams(state: {
  origin?: string;
  destination?: string;
  additionalOrigins?: readonly string[];
  additionalDestinations?: readonly string[];
  travelDate?: string;
  returnDate?: string;
  isReturn?: boolean;
  adults?: number;
  flexBefore?: number;
  flexAfter?: number;
  radius?: number;
  strict?: boolean;
}): string {
  const search = new URLSearchParams();

  const origin = state.origin ? sanitizeIata(state.origin) : "";
  if (origin) search.set(QS_PARAM_ORIGIN, origin);

  const destination = state.destination ? sanitizeIata(state.destination) : "";
  if (destination) search.set(QS_PARAM_DESTINATION, destination);

  const appendAdditionalIata = (param: string, values: readonly string[] | undefined, primary: string) => {
    const sanitized = Array.from(new Set(
      (values ?? []).map((value) => sanitizeIata(value)).filter((value) => value && value !== primary),
    )).slice(0, 5);
    if (sanitized.length > 0) search.set(param, sanitized.join(","));
  };
  appendAdditionalIata(QS_PARAM_ADDITIONAL_ORIGINS, state.additionalOrigins, origin);
  appendAdditionalIata(QS_PARAM_ADDITIONAL_DESTINATIONS, state.additionalDestinations, destination);

  const travelDate = state.travelDate ? sanitizeIsoDate(state.travelDate) : "";
  if (travelDate) search.set(QS_PARAM_TRAVEL_DATE, travelDate);

  const returnDate = state.returnDate ? sanitizeIsoDate(state.returnDate) : "";
  if (returnDate) search.set(QS_PARAM_RETURN_DATE, returnDate);

  if (state.isReturn) search.set(QS_PARAM_IS_RETURN, "1");

  if (state.adults && state.adults !== 1) search.set(QS_PARAM_ADULTS, String(state.adults));
  if (state.flexBefore) search.set(QS_PARAM_FLEX_BEFORE, String(state.flexBefore));
  if (state.flexAfter) search.set(QS_PARAM_FLEX_AFTER, String(state.flexAfter));
  if (state.radius && state.radius !== 150) search.set(QS_PARAM_RADIUS, String(state.radius));
  if (state.strict === false) search.set(QS_PARAM_STRICT, "0");

  return search.toString();
}
