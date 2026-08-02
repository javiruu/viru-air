import { useEffect, useMemo, useState } from "react";

import {
  communityRouteKey,
  fetchCommunityRouteInsights,
} from "@/modules/community-routes/communityRoutesApi";
import type {
  CommunityRoute,
  CommunityRouteInsight,
} from "@/modules/community-routes/communityRoutesTypes";

export function useCommunityRouteInsights(
  routes: readonly CommunityRoute[],
): ReadonlyMap<string, CommunityRouteInsight> {
  const signature = routes
    .map(communityRouteKey)
    .filter((key, index, values) => values.indexOf(key) === index)
    .sort()
    .join("|");
  const requestedRoutes = useMemo(() => {
    if (!signature) return [];
    return signature.split("|").map((key) => {
      const [origin_iata, destination_iata] = key.split("-");
      return { origin_iata, destination_iata };
    });
  }, [signature]);
  const [insights, setInsights] = useState<ReadonlyMap<string, CommunityRouteInsight>>(
    () => new Map(),
  );

  useEffect(() => {
    let active = true;
    if (requestedRoutes.length === 0) {
      setInsights(new Map());
      return () => {
        active = false;
      };
    }
    void fetchCommunityRouteInsights(requestedRoutes)
      .then((response) => {
        if (!active) return;
        setInsights(
          new Map(response.routes.map((route) => [communityRouteKey(route), route])),
        );
      })
      .catch(() => {
        if (active) setInsights(new Map());
      });
    return () => {
      active = false;
    };
  }, [requestedRoutes]);

  return insights;
}
