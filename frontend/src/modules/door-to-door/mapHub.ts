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
  const hasGtfsTransit = providerByName.get("gtfs_transit")?.enabled || false;
  const hasGooglePlaces = providerByName.get("google_places")?.enabled || false;

  const defaults: Record<DoorToDoorMapCapabilityKey, Omit<DoorToDoorMapCapability, "key">> = {
    // ── Capacidades con valor real (Fase 9) ──
    navigation: hasGoogleRoutes
      ? { state: "available", source_type: "maps", confidence: "live", why_missing: null }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "google_routes_disabled" },
    transit: hasGtfsTransit
      ? { state: "partial", source_type: "open_data", confidence: "cached", why_missing: "corridor_limited" }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "gtfs_provider_disabled" },
    alternatives: response?.options?.length
      ? { state: "available", source_type: "api", confidence: "cached", why_missing: null }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "route_candidates_pending" },
    saved_places: { state: "available", source_type: "api", confidence: "cached", why_missing: null },
    // ── Fase 7: capacidades activadas con backend real ──
    traffic: hasGoogleRoutes
      ? { state: "partial", source_type: "maps", confidence: "cached", why_missing: "driving_only" }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "google_routes_disabled" },
    nearby_pois: hasGooglePlaces
      ? { state: "partial", source_type: "maps", confidence: "cached", why_missing: "search_endpoint_not_wired" }
      : { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "google_places_disabled" },
    // ── Capacidades sembradas, sin backend real ──
    street_view_preview: { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "street_view_not_connected" },
    offline: { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "offline_cache_not_implemented" },
    incidents: { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "incident_source_not_connected" },
    eco_route: { state: "planned", source_type: "none", confidence: "unavailable", why_missing: "eco_route_provider_pending" },
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
