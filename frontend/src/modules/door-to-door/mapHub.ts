import type {
  DoorToDoorMapCapability,
  DoorToDoorMapCapabilityKey,
  DoorToDoorProviderStatus,
  DoorToDoorResponse,
  DoorToDoorSavedPlace,
} from "@/modules/door-to-door/types";

const CAPABILITY_KEYS: DoorToDoorMapCapabilityKey[] = [
  "navigation",
  "traffic",
  "transit",
  "alternatives",
  "street_view_preview",
  "saved_places",
  "nearby_pois",
  "offline",
  "incidents",
  "eco_route",
];

export function buildMapCapabilities(response: DoorToDoorResponse | null, providers: DoorToDoorProviderStatus[]): DoorToDoorMapCapability[] {
  const providerByName = new Map(providers.map((provider) => [provider.name, provider]));
  const input = response?.map_capabilities ?? {};
  const hasGoogleRoutes = providerByName.get("google_routes")?.enabled || false;
  const hasGooglePlaces = providerByName.get("google_places")?.enabled || false;
  const hasGtfsTransit = providerByName.get("gtfs_transit")?.enabled || false;
  const hasDeeplink = providers.some((provider) => provider.enabled && provider.source_type === "deeplink");
  const warningCodes = new Set((response?.warnings ?? []).map((warning) => warning.code));
  const hasCoverageWarnings = warningCodes.has("NO_COVERAGE") || warningCodes.has("GOOGLE_ROUTES_UNAVAILABLE") || warningCodes.has("PROVIDER_PARTIAL_COVERAGE");

  const defaults: Record<DoorToDoorMapCapabilityKey, Omit<DoorToDoorMapCapability, "key">> = {
    navigation: hasGoogleRoutes
      ? { state: "available", source_type: "maps", confidence: "live", why_missing: null }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "google_routes_disabled" },
    traffic: hasGoogleRoutes
      ? {
          state: hasCoverageWarnings ? "partial" : "partial",
          source_type: "maps",
          confidence: "cached",
          why_missing: hasCoverageWarnings ? "live_traffic_degraded" : "live_traffic_not_wired",
        }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "traffic_layer_pending" },
    transit: hasGtfsTransit
      ? { state: "partial", source_type: "open_data", confidence: "cached", why_missing: "fares_and_booking_pending" }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "gtfs_provider_disabled" },
    alternatives: response?.options?.length
      ? { state: "available", source_type: "api", confidence: "cached", why_missing: null }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "route_candidates_pending" },
    street_view_preview: hasGoogleRoutes
      ? { state: "partial", source_type: "maps", confidence: "cached", why_missing: "immersive_preview_pending" }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "street_view_not_connected" },
    saved_places: { state: "partial", source_type: "api", confidence: "cached", why_missing: "shared_lists_pending" },
    nearby_pois: hasGooglePlaces
      ? { state: "partial", source_type: "api", confidence: "live", why_missing: "busy_times_and_parking_pending" }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "google_places_disabled" },
    offline: { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "offline_cache_not_implemented" },
    incidents: hasGoogleRoutes
      ? {
          state: hasCoverageWarnings ? "partial" : "partial",
          source_type: "maps",
          confidence: "cached",
          why_missing: hasCoverageWarnings ? "incident_feed_degraded" : "incident_feed_pending",
        }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "incident_source_not_connected" },
    eco_route: hasDeeplink || hasGoogleRoutes
      ? { state: "partial", source_type: hasGoogleRoutes ? "maps" : "deeplink", confidence: "cached", why_missing: "eco_scoring_pending" }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "eco_route_provider_pending" },
  };

  return CAPABILITY_KEYS.map((key) => {
    const fromApi = input[key];
    const fallback = defaults[key];
    return {
      key,
      state: fromApi?.state ?? fallback.state,
      source_type: fromApi?.source_type ?? fallback.source_type,
      confidence: fromApi?.confidence ?? fallback.confidence,
      last_checked_at: fromApi?.last_checked_at ?? null,
      why_missing: fromApi?.why_missing ?? fallback.why_missing ?? null,
    };
  });
}

export function filterSavedPlacesForWatch(savedPlaces: DoorToDoorSavedPlace[], selectedWatchId: string): DoorToDoorSavedPlace[] {
  if (!selectedWatchId) return savedPlaces.filter((item) => item.watch_id === null);
  return savedPlaces.filter((item) => item.watch_id === selectedWatchId || item.watch_id === null);
}
