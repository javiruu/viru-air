"use client";

import { useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";

import { fetchPopularDestinationsFromOrigin } from "@/modules/community-routes/communityRoutesApi";
import type { CommunityPopularRoute } from "@/modules/community-routes/communityRoutesTypes";
import { BoneyardLoad, LoadReference } from "@/modules/shared/BoneyardLoad";

type PopularDestinationsChipsProps = {
  readonly origin: string;
  readonly onSelectDestination: (iata: string) => void;
  readonly t: (key: string, params?: Readonly<Record<string, string | number>>) => string;
};

export function PopularDestinationsChips({
  origin,
  onSelectDestination,
  t,
}: PopularDestinationsChipsProps) {
  const [routes, setRoutes] = useState<CommunityPopularRoute[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const code = origin.trim().toUpperCase();
    if (code.length !== 3) {
      setRoutes([]);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    fetchPopularDestinationsFromOrigin(code)
      .then((response) => {
        if (!active) return;
        setRoutes(response.routes);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setRoutes([]);
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [origin]);

  const hasRoutes = routes.length > 0;
  if (!loading && !hasRoutes) return null;

  return (
    <div className="community-popular-destinations-strip" aria-label={t("popularDestinationsLabel")} aria-busy={loading}>
      <span className="community-popular-destinations-strip-label">
        <TrendingUp aria-hidden="true" size={14} />
        {t("popularDestinationsLabel")}
      </span>
      <div className="community-popular-destinations-chips">
        {loading
          ? (
            <BoneyardLoad name="community-popular-destinations-load" className="community-popular-destination-loads" ariaLabel={t("popularDestinationsLabel")}>
              {Array.from({ length: 3 }).map((_, i) => (
                <LoadReference key={`community-popular-destination-load-${i}`} shape="chip" className="community-popular-destination-chip-load" />
              ))}
            </BoneyardLoad>
          )
          : routes.map((route) => (
              <button
                key={`${route.origin_iata}-${route.destination_iata}`}
                type="button"
                className="community-popular-destination-chip"
                onClick={() => onSelectDestination(route.destination_iata)}
                title={t("popularDestinationAria", {
                  origin: route.origin_iata,
                  destination: route.destination_iata,
                })}
              >
                {route.destination_iata}
              </button>
            ))}
      </div>
    </div>
  );
}
