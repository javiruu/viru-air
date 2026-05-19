import { QUICK_SEARCH_RADIUS_DEFAULT, clampQuickSearchRadius } from "@/modules/quick-search/filterUtils";
import { Pref } from "@/modules/quick-search/types";

export type QuickSearchPreferenceDefaults = {
  radiusKm: number;
  includeStops: boolean;
  departAfter: string;
  departBefore: string;
  includeNearbyOrigins: boolean;
  includeNearbyDestinations: boolean;
  strictFilters: boolean;
  countryPriceHintMode: "min" | "median" | "fixed_route";
};

export function resolveQuickSearchPreferenceDefaults(
  pref: Pref,
  fallbackRadiusKm = QUICK_SEARCH_RADIUS_DEFAULT,
): QuickSearchPreferenceDefaults {
  return {
    radiusKm: clampQuickSearchRadius(pref.default_radius_km ?? fallbackRadiusKm),
    includeStops: Boolean(pref.include_stops_default),
    departAfter: pref.avoid_departure_before ?? "",
    departBefore: pref.depart_before_default ?? "",
    includeNearbyOrigins: Boolean(pref.include_nearby_origins_default),
    includeNearbyDestinations: Boolean(pref.include_nearby_destinations_default),
    strictFilters: pref.strict_filters_default !== false,
    countryPriceHintMode: pref.country_price_hint_mode_default || "min",
  };
}
