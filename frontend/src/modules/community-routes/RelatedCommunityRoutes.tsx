import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useI18n } from "@/i18n";
import { fetchRelatedCommunityRoutes } from "@/modules/community-routes/communityRoutesApi";
import type { CommunityRelatedRoute } from "@/modules/community-routes/communityRoutesTypes";

type RelatedCommunityRoutesProps = {
  readonly origin: string;
  readonly destination: string;
};

export function RelatedCommunityRoutes({
  origin,
  destination,
}: RelatedCommunityRoutesProps) {
  const { t } = useI18n();
  const [routes, setRoutes] = useState<CommunityRelatedRoute[]>([]);

  useEffect(() => {
    let active = true;
    void fetchRelatedCommunityRoutes(origin, destination)
      .then((response) => {
        if (active) setRoutes(response.routes);
      })
      .catch(() => {
        if (active) setRoutes([]);
      });
    return () => {
      active = false;
    };
  }, [destination, origin]);

  if (routes.length === 0) return null;

  return (
    <section className="community-related" aria-labelledby="community-related-title">
      <h3 id="community-related-title">
        {t("watchlist.communitySignals.relatedTitle", { origin, destination })}
      </h3>
      <p>{t("watchlist.communitySignals.relatedBody")}</p>
      <ul className="community-related-list">
        {routes.map((route) => (
          <li key={`${route.origin_iata}-${route.destination_iata}`}>
            <Link
              className="community-related-link"
              href={`/quick-search?origin=${route.origin_iata}&destination=${route.destination_iata}`}
            >
              <strong>{route.origin_iata} → {route.destination_iata}</strong>
              <span>{t("watchlist.communitySignals.travelers", { count: route.travelers_count })}</span>
              <ChevronRight aria-hidden="true" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
