export type QuickSearchQueryParams = {
  origin_iata: string | string[];
  destination_iata: string | string[];
  travel_date: string;
  date: string;
  flex_days_before: number;
  flex_days_after: number;
  radius_km: number;
  include_stops: boolean;
  include_nearby_origins: boolean;
  include_nearby_destinations: boolean;
  depart_after?: string;
  depart_before?: string;
  max_stops: number;
  exclude_origins: string[];
  exclude_destinations: string[];
  strict_filters: boolean;
  soft_filters_weight: number;
};

export type QuickSearchContractIssueCode =
  | "missing_origin"
  | "missing_destination"
  | "missing_travel_date"
  | "invalid_radius"
  | "invalid_flex_days"
  | "invalid_soft_filters_weight"
  | "invalid_max_stops";

export type QuickSearchContractIssue = {
  code: QuickSearchContractIssueCode;
  message: string;
};

export type QuickSearchPreparedRequest = {
  params: QuickSearchQueryParams;
  issues: QuickSearchContractIssue[];
};

export type QuickSearchCanonicalPayload = {
  origin: {
    seed_iata: string;
    include_nearby: boolean;
    radius_km: number;
    max_candidates: number;
  };
  destination: {
    seed_iata: string;
    include_nearby: boolean;
    radius_km: number;
    max_candidates: number;
  };
  travel: {
    date: string;
    flex_before: number;
    flex_after: number;
  };
  constraints: {
    departure_window: {
      after?: string;
      before?: string;
    };
    exclude_origins: string[];
    exclude_destinations: string[];
    strict_filters: boolean;
    include_stops: boolean;
    max_stops: number;
    soft_filters_weight: number;
  };
};

function clampInt(value: number, min: number, max: number, fallback: number): number {
  if (!Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, Math.trunc(value)));
}

function normalizeIataValue(value: string | string[]): string | string[] {
  if (Array.isArray(value)) {
    return value.map((item) => item.trim().toUpperCase()).filter(Boolean);
  }
  return value.trim().toUpperCase();
}

export function prepareQuickSearchRequest(input: QuickSearchQueryParams): QuickSearchPreparedRequest {
  const normalized: QuickSearchQueryParams = {
    ...input,
    origin_iata: normalizeIataValue(input.origin_iata),
    destination_iata: normalizeIataValue(input.destination_iata),
    travel_date: input.travel_date?.trim?.() || "",
    date: input.date?.trim?.() || input.travel_date?.trim?.() || "",
    flex_days_before: clampInt(input.flex_days_before, 0, 7, 0),
    flex_days_after: clampInt(input.flex_days_after, 0, 7, 0),
    radius_km: clampInt(input.radius_km, 10, 500, 150),
    include_stops: Boolean(input.include_stops),
    include_nearby_origins: Boolean(input.include_nearby_origins),
    include_nearby_destinations: Boolean(input.include_nearby_destinations),
    max_stops: clampInt(input.max_stops, 0, 4, 0),
    exclude_origins: (input.exclude_origins || []).map((item) => item.trim().toUpperCase()).filter(Boolean),
    exclude_destinations: (input.exclude_destinations || []).map((item) => item.trim().toUpperCase()).filter(Boolean),
    strict_filters: Boolean(input.strict_filters),
    soft_filters_weight: Number.isFinite(input.soft_filters_weight)
      ? Math.min(1, Math.max(0, input.soft_filters_weight))
      : 0.6,
    depart_after: input.depart_after || undefined,
    depart_before: input.depart_before || undefined,
  };

  if (!normalized.include_stops) {
    normalized.max_stops = 0;
  }

  const issues: QuickSearchContractIssue[] = [];
  const hasOrigin = Array.isArray(normalized.origin_iata)
    ? normalized.origin_iata.length > 0
    : normalized.origin_iata.length > 0;
  const hasDestination = Array.isArray(normalized.destination_iata)
    ? normalized.destination_iata.length > 0
    : normalized.destination_iata.length > 0;

  if (!hasOrigin) issues.push({ code: "missing_origin", message: "origin_iata is required" });
  if (!hasDestination) issues.push({ code: "missing_destination", message: "destination_iata is required" });
  if (!normalized.travel_date) issues.push({ code: "missing_travel_date", message: "travel_date is required" });
  if (!Number.isFinite(input.radius_km)) issues.push({ code: "invalid_radius", message: "radius_km must be numeric" });
  if (!Number.isFinite(input.flex_days_before) || !Number.isFinite(input.flex_days_after)) {
    issues.push({ code: "invalid_flex_days", message: "flex_days_before/flex_days_after must be numeric" });
  }
  if (!Number.isFinite(input.soft_filters_weight)) {
    issues.push({ code: "invalid_soft_filters_weight", message: "soft_filters_weight must be numeric" });
  }
  if (!Number.isFinite(input.max_stops)) {
    issues.push({ code: "invalid_max_stops", message: "max_stops must be numeric" });
  }

  return { params: normalized, issues };
}

export function toQuickSearchQuery(params: QuickSearchQueryParams): string {
  const query = new URLSearchParams();
  const originValue = Array.isArray(params.origin_iata) ? params.origin_iata.join(",") : params.origin_iata;
  const destinationValue = Array.isArray(params.destination_iata)
    ? params.destination_iata.join(",")
    : params.destination_iata;

  query.set("origin_iata", originValue);
  query.set("destination_iata", destinationValue);
  query.set("travel_date", params.travel_date);
  query.set("date", params.date);
  if (params.flex_days_before > 0) query.set("flex_days_before", String(params.flex_days_before));
  if (params.flex_days_after > 0) query.set("flex_days_after", String(params.flex_days_after));
  query.set("radius_km", String(params.radius_km));
  query.set("include_stops", String(params.include_stops));
  query.set("include_nearby_origins", String(params.include_nearby_origins));
  query.set("include_nearby_destinations", String(params.include_nearby_destinations));
  if (params.depart_after) query.set("depart_after", params.depart_after);
  if (params.depart_before) query.set("depart_before", params.depart_before);
  query.set("max_stops", String(params.max_stops));
  if (params.exclude_origins.length > 0) query.set("exclude_origins", params.exclude_origins.join(","));
  if (params.exclude_destinations.length > 0) query.set("exclude_destinations", params.exclude_destinations.join(","));
  query.set("strict_filters", String(params.strict_filters));
  query.set("soft_filters_weight", String(params.soft_filters_weight));
  return query.toString();
}

function toSeedIata(value: string | string[]): string {
  if (Array.isArray(value)) {
    return value[0] || "";
  }
  return value;
}

export function buildQuickSearchCanonicalPayload(params: QuickSearchQueryParams): QuickSearchCanonicalPayload {
  return {
    origin: {
      seed_iata: toSeedIata(params.origin_iata),
      include_nearby: params.include_nearby_origins,
      radius_km: params.radius_km,
      max_candidates: 6,
    },
    destination: {
      seed_iata: toSeedIata(params.destination_iata),
      include_nearby: params.include_nearby_destinations,
      radius_km: params.radius_km,
      max_candidates: 6,
    },
    travel: {
      date: params.travel_date,
      flex_before: params.flex_days_before,
      flex_after: params.flex_days_after,
    },
    constraints: {
      departure_window: {
        after: params.depart_after,
        before: params.depart_before,
      },
      exclude_origins: params.exclude_origins,
      exclude_destinations: params.exclude_destinations,
      strict_filters: params.strict_filters,
      include_stops: params.include_stops,
      max_stops: params.max_stops,
      soft_filters_weight: params.soft_filters_weight,
    },
  };
}
