import type { SearchResult } from "./types";
import type { QuickSearchSideParams } from "./state/useQuickSearchSide";

// ── Types ────────────────────────────────────────────────────────────

export type DualSearchParamsInput = {
  origin: string | string[];
  destination: string | string[];
  travelDate: string;
  travelDates?: string[];
  flexDaysBefore: number;
  flexDaysAfter: number;
  radiusKm: number;
  includeStops: boolean;
  includeNearbyOrigins: boolean;
  includeNearbyDestinations: boolean;
  departAfter: string;
  departBefore: string;
  maxStops: number;
  excludeOrigins: string[];
  excludeDestinations: string[];
  strictFilters: boolean;
};

// ── buildDualSearchParams ────────────────────────────────────────────

/**
 * Builds a {@link QuickSearchSideParams} object from the shared filter state.
 *
 * Keeps the dual submit branch in `QuickSearchView` focused on orchestration
 * instead of field-by-field mapping.
 */
export function buildDualSearchParams(
  input: DualSearchParamsInput,
): QuickSearchSideParams {
  return {
    originIata: input.origin,
    destinationIata: input.destination,
    travelDate: input.travelDate,
    travelDates: input.travelDates,
    flexDaysBefore: input.flexDaysBefore,
    flexDaysAfter: input.flexDaysAfter,
    radiusKm: input.radiusKm,
    includeStops: input.includeStops,
    includeNearbyOrigins: input.includeNearbyOrigins,
    includeNearbyDestinations: input.includeNearbyDestinations,
    departAfter: input.departAfter || undefined,
    departBefore: input.departBefore || undefined,
    maxStops: input.maxStops,
    excludeOrigins: input.excludeOrigins,
    excludeDestinations: input.excludeDestinations,
    strictFilters: input.strictFilters,
  };
}

// ── findCombinationResult ────────────────────────────────────────────

/**
 * Returns the currently-selected result from a side, or the first result
 * as a fallback.  Used by the save-combination callback so the same logic
 * doesn't need to be duplicated for outbound and return.
 */
export function findCombinationResult(
  results: SearchResult[],
  selectedResultId: string | null,
): SearchResult | undefined {
  if (selectedResultId) {
    return results.find((r, i) => {
      const key =
        r.result_id ||
        `${r.origin}-${r.destination}-${r.travel_date}-${i}`;
      return key === selectedResultId;
    });
  }
  return results[0];
}
