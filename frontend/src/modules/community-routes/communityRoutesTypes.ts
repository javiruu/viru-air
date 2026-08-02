export type CommunityRoute = {
  readonly origin_iata: string;
  readonly destination_iata: string;
};

export type CommunityPopularRoute = CommunityRoute & {
  readonly searches_count: number;
  readonly is_trending: boolean;
};

export type CommunityRouteInsight = CommunityPopularRoute & {
  readonly sample_size: number;
  readonly min_price: number | null;
  readonly max_price: number | null;
  readonly currency: "EUR";
};

export type CommunityRelatedRoute = CommunityRoute & {
  readonly travelers_count: number;
};

export type CommunityPopularRoutesResponse = {
  readonly window_days: 7;
  readonly routes: CommunityPopularRoute[];
};

export type CommunityRouteInsightsResponse = {
  readonly routes: CommunityRouteInsight[];
};

export type CommunityRelatedRoutesResponse = {
  readonly routes: CommunityRelatedRoute[];
};
