import type {
  CommunityPricing,
  Watch,
  WatchDetail,
} from "@/modules/watchlist/types";

export function createEmptyCommunityPricing(): CommunityPricing {
  return {
    eligible: false,
    trigger_reason: null,
    response: null,
    aggregate: {
      sample_size: 0,
      minimum_sample_size: 3,
      is_public: false,
      min_price: null,
      max_price: null,
      currency: "EUR",
    },
  };
}

export type WatchApiResponse = Omit<Watch, "community_pricing"> & {
  readonly community_pricing?: CommunityPricing | null;
};

export type WatchDetailApiResponse = Omit<WatchDetail, "community_pricing"> & {
  readonly community_pricing?: CommunityPricing | null;
};

export function normalizeWatchApiResponse(response: WatchApiResponse): Watch {
  return {
    ...response,
    community_pricing:
      response.community_pricing ?? createEmptyCommunityPricing(),
  };
}

export function normalizeWatchDetailApiResponse(
  response: WatchDetailApiResponse,
): WatchDetail {
  return {
    ...response,
    community_pricing:
      response.community_pricing ?? createEmptyCommunityPricing(),
  };
}
