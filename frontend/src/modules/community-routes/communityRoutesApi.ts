import { COMMUNITY_MIN_SAMPLE_SIZE } from "@/modules/community-routes/communityConstants";
import { apiFetch } from "@/modules/shared/api";
import type {
  CommunityPopularRoute,
  CommunityPopularRoutesResponse,
  CommunityRelatedRoute,
  CommunityRelatedRoutesResponse,
  CommunityRoute,
  CommunityRouteInsight,
  CommunityRouteInsightsResponse,
} from "@/modules/community-routes/communityRoutesTypes";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeIata(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim().toUpperCase();
  return /^[A-Z]{3}$/.test(normalized) ? normalized : null;
}

function normalizeCount(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0
    ? Math.floor(value)
    : 0;
}

function normalizeNullablePrice(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0
    ? value
    : null;
}

function normalizePopularRoute(value: unknown): CommunityPopularRoute | null {
  if (!isRecord(value)) return null;
  const origin = normalizeIata(value.origin_iata);
  const destination = normalizeIata(value.destination_iata);
  if (!origin || !destination) return null;
  return {
    origin_iata: origin,
    destination_iata: destination,
    searches_count: normalizeCount(value.searches_count),
    is_trending: value.is_trending === true,
  };
}

export function normalizePopularRoutesResponse(
  value: unknown,
): CommunityPopularRoutesResponse {
  if (!isRecord(value) || value.window_days !== 7) {
    return { window_days: 7, routes: [] };
  }
  const routes = isRecord(value) && Array.isArray(value.routes)
    ? value.routes.map(normalizePopularRoute).filter((route): route is CommunityPopularRoute => route !== null)
    : [];
  return { window_days: 7, routes: routes.slice(0, 10) };
}

export function normalizeRouteInsightsResponse(
  value: unknown,
): CommunityRouteInsightsResponse {
  const routes = isRecord(value) && Array.isArray(value.routes)
    ? value.routes.flatMap((candidate): CommunityRouteInsight[] => {
        const route = normalizePopularRoute(candidate);
        if (!route || !isRecord(candidate)) return [];
        const sampleSize = normalizeCount(candidate.sample_size);
        const minPrice = normalizeNullablePrice(candidate.min_price);
        const maxPrice = normalizeNullablePrice(candidate.max_price);
        const isPublic = sampleSize >= COMMUNITY_MIN_SAMPLE_SIZE && minPrice !== null && maxPrice !== null;
        return [{
          ...route,
          sample_size: isPublic ? sampleSize : 0,
          min_price: isPublic ? minPrice : null,
          max_price: isPublic ? maxPrice : null,
          currency: "EUR",
        }];
      })
    : [];
  return { routes };
}

export function normalizeRelatedRoutesResponse(
  value: unknown,
): CommunityRelatedRoutesResponse {
  const routes = isRecord(value) && Array.isArray(value.routes)
    ? value.routes.flatMap((candidate): CommunityRelatedRoute[] => {
        if (!isRecord(candidate)) return [];
        const origin = normalizeIata(candidate.origin_iata);
        const destination = normalizeIata(candidate.destination_iata);
        const travelersCount = normalizeCount(candidate.travelers_count);
        if (!origin || !destination || travelersCount < COMMUNITY_MIN_SAMPLE_SIZE) return [];
        return [{
          origin_iata: origin,
          destination_iata: destination,
          travelers_count: travelersCount,
        }];
      })
    : [];
  return { routes: routes.slice(0, 3) };
}

export async function fetchPopularCommunityRoutes(): Promise<CommunityPopularRoutesResponse> {
  return normalizePopularRoutesResponse(
    await apiFetch<unknown>("/community/routes/popular"),
  );
}

export async function fetchCommunityRouteInsights(
  routes: readonly CommunityRoute[],
): Promise<CommunityRouteInsightsResponse> {
  const normalizedRoutes: CommunityRouteInsight[] = [];
  for (let index = 0; index < routes.length; index += 100) {
    const response = normalizeRouteInsightsResponse(
      await apiFetch<unknown>("/community/routes/insights", {
        method: "POST",
        body: JSON.stringify({ routes: routes.slice(index, index + 100) }),
      }),
    );
    normalizedRoutes.push(...response.routes);
  }
  return { routes: normalizedRoutes };
}

export async function fetchRelatedCommunityRoutes(
  origin: string,
  destination: string,
): Promise<CommunityRelatedRoutesResponse> {
  return normalizeRelatedRoutesResponse(
    await apiFetch<unknown>(
      `/community/routes/${encodeURIComponent(origin)}/${encodeURIComponent(destination)}/related`,
    ),
  );
}

export async function fetchPopularDestinationsFromOrigin(
  origin: string,
): Promise<CommunityPopularRoutesResponse> {
  return normalizePopularRoutesResponse(
    await apiFetch<unknown>(
      `/community/routes/popular-from/${encodeURIComponent(origin)}`,
    ),
  );
}

export function communityRouteKey(route: CommunityRoute): string {
  return `${route.origin_iata.trim().toUpperCase()}-${route.destination_iata.trim().toUpperCase()}`;
}
