import {
  QuickSearchFreshness,
  QuickSearchFreshnessStatus,
  SearchResponse,
  SearchResponseRaw,
  SearchResult,
  SearchResultRaw,
} from "@/modules/quick-search/types";

function toFiniteNumber(value: unknown, fallback: number | null = null): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function toOptionalString(value: unknown, fallback: string | null = null): string | null {
  if (typeof value === "string") return value;
  return fallback;
}

function toRequiredString(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) return value;
  return fallback;
}

function toOptionalBoolean(value: unknown, fallback = false): boolean {
  if (typeof value === "boolean") return value;
  return fallback;
}

function toFreshnessStatus(value: unknown): QuickSearchFreshnessStatus | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim().toLowerCase();
  switch (normalized) {
    case "fresh":
    case "warm":
    case "stale":
    case "expired":
    case "negative_fresh":
    case "negative_stale":
    case "provider_error_fresh":
    case "provider_error_stale":
      return normalized;
    default:
      return null;
  }
}

function isFreshnessStale(status: QuickSearchFreshnessStatus | null | undefined): boolean {
  return status === "stale"
    || status === "expired"
    || status === "negative_stale"
    || status === "provider_error_stale";
}

function normalizeFreshness(value: unknown): QuickSearchFreshness | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const raw = value as Record<string, unknown>;
  const status = toFreshnessStatus(raw.status);
  const observedAt = toOptionalString(raw.observed_at);
  const expiresAt = toOptionalString(raw.expires_at);
  const ageSeconds = toFiniteNumber(raw.age_seconds);
  const confidenceScore = toFiniteNumber(raw.confidence_score);
  const source = toOptionalString(raw.source);
  const requiresRevalidation = toOptionalBoolean(raw.requires_revalidation);
  const validationStatus = toOptionalString(raw.validation_status);

  if (
    status === null
    && observedAt === null
    && expiresAt === null
    && ageSeconds === null
    && confidenceScore === null
    && source === null
    && requiresRevalidation === false
    && validationStatus === null
  ) {
    return null;
  }

  return {
    status,
    observed_at: observedAt,
    expires_at: expiresAt,
    age_seconds: ageSeconds,
    confidence_score: confidenceScore,
    source,
    requires_revalidation: requiresRevalidation,
    validation_status: validationStatus,
  };
}

function extractRankingScore(item: SearchResultRaw): number | null {
  const directScore = toFiniteNumber(item.ranking_score);
  if (directScore !== null) return directScore;
  const numericBreakdownScore = toFiniteNumber(item.score);
  if (numericBreakdownScore !== null) return numericBreakdownScore;
  if (item.score && typeof item.score === "object") {
    const finalScore = toFiniteNumber(item.score.final_score);
    if (finalScore !== null) {
      return finalScore;
    }
  }
  return null;
}

function normalizeProviderStatus(
  providerStatus: SearchResponseRaw["meta"] extends infer T
    ? T extends { provider_status?: infer P }
      ? P | undefined
      : never
    : never,
) {
  if (!providerStatus || typeof providerStatus !== "object") {
    return providerStatus;
  }
  const overallStatus =
    providerStatus.overall_status
    ?? providerStatus.overall
    ?? (providerStatus.total_outage
      ? "total_outage"
      : providerStatus.partial_results_served
        ? "partial_degraded"
        : "ok");

  return {
    ...providerStatus,
    availability: providerStatus.availability ?? { status: "ok" as const },
    fares: providerStatus.fares ?? { status: "ok" as const },
    overall: overallStatus,
    overall_status: overallStatus,
    partial_results_served: Boolean(providerStatus.partial_results_served),
    total_outage: Boolean(providerStatus.total_outage),
    providers: Array.isArray(providerStatus.providers) ? providerStatus.providers : [],
  };
}

export function collectQuickSearchWarningCodes(response: SearchResponseRaw): string[] {
  const filterWarnings = Array.isArray(response.filters?.warnings)
    ? response.filters.warnings.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
  const structuredWarnings = Array.isArray(response.meta?.warnings_structured)
    ? response.meta.warnings_structured
        .map((item) => (item && typeof item.code === "string" ? item.code.trim() : ""))
        .filter((item): item is string => item.length > 0)
    : [];

  return Array.from(new Set([...filterWarnings, ...structuredWarnings]));
}

export function normalizeQuickSearchResults(results: SearchResultRaw[]): SearchResult[] {
  return results.map((item, idx) => {
    const normalizedFreshness = normalizeFreshness(item.freshness);

    return {
      ...item,
      freshness: normalizedFreshness,
      result_id:
        toOptionalString(item.result_id) ??
        `${toRequiredString(item.origin, "UNK")}-${toRequiredString(item.destination, "UNK")}-${toRequiredString(item.travel_date, "unknown-date")}-${idx}`,
      origin: toRequiredString(item.origin, "UNK"),
      destination: toRequiredString(item.destination, "UNK"),
      travel_date: toRequiredString(item.travel_date, ""),
      departure_time_local: toOptionalString(item.departure_time_local),
      price: toFiniteNumber(item.price, 0) ?? 0,
      price_total: toFiniteNumber(item.price_total, toFiniteNumber(item.price, 0) ?? 0) ?? 0,
      currency: toRequiredString(item.currency, "EUR"),
      source: toRequiredString(item.source, ""),
      duration_total: toFiniteNumber(item.duration_total),
      duration_total_min: toFiniteNumber(item.duration_total_min, toFiniteNumber(item.duration_total)),
      stop_count: toFiniteNumber(item.stop_count),
      minutes_buffer: toFiniteNumber(item.minutes_buffer),
      distance_km_ground: toFiniteNumber(item.distance_km_ground),
      ranking_score: extractRankingScore(item),
      freshness_ts: toOptionalString(item.freshness_ts) ?? normalizedFreshness?.observed_at ?? null,
      stale_data: Boolean(item.stale_data) || isFreshnessStale(normalizedFreshness?.status),
      ai_preferred: Boolean(item.ai_preferred),
      ai_preferred_reason: toOptionalString(item.ai_preferred_reason),
      deeplink_url: toOptionalString(item.deeplink_url),
      itinerary_type: item.itinerary_type ?? (item.stop_count && item.stop_count > 0 ? "self_connect" : "direct"),
      legs: item.legs ?? item.segments?.legs ?? [],
    };
  });
}

export function normalizeQuickSearchResponse(response: SearchResponseRaw): SearchResponse {
  const normalizedSearchCacheFreshness = normalizeFreshness(response.meta?.search_cache?.freshness);
  const normalizedMetaFreshnessTs =
    toOptionalString(response.meta?.freshness_ts) ?? normalizedSearchCacheFreshness?.observed_at ?? null;
  const normalizedMetaStaleData =
    Boolean(response.meta?.stale_data) || isFreshnessStale(normalizedSearchCacheFreshness?.status);

  return {
    ...response,
    meta: response.meta
      ? {
          ...response.meta,
          freshness_ts: normalizedMetaFreshnessTs,
          stale_data: normalizedMetaStaleData,
          search_cache: response.meta.search_cache
            ? {
                ...response.meta.search_cache,
                exact_hit: toOptionalBoolean(response.meta.search_cache.exact_hit),
                search_fingerprint: toOptionalString(response.meta.search_cache.search_fingerprint),
                provider: toOptionalString(response.meta.search_cache.provider),
                requires_revalidation: toOptionalBoolean(response.meta.search_cache.requires_revalidation),
                freshness: normalizedSearchCacheFreshness,
              }
            : response.meta.search_cache,
          provider_status: normalizeProviderStatus(response.meta.provider_status),
        }
      : response.meta,
    results: normalizeQuickSearchResults(response.results || []),
  };
}
