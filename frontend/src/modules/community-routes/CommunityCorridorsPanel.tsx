import { ChevronRight, Radar } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useI18n } from "@/i18n";
import { fetchPopularCommunityRoutes } from "@/modules/community-routes/communityRoutesApi";
import type { CommunityPopularRoute } from "@/modules/community-routes/communityRoutesTypes";
import { BoneyardLoad, LoadReference } from "@/modules/shared/BoneyardLoad";

import styles from "./CommunityCorridorsPanel.module.css";

export function CommunityCorridorsPanel() {
  const { t } = useI18n();
  const [routes, setRoutes] = useState<CommunityPopularRoute[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void fetchPopularCommunityRoutes()
      .then((response) => {
        if (active) setRoutes(response.routes);
      })
      .catch(() => {
        if (active) setRoutes([]);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const strongest = routes[0]?.searches_count ?? 1;

  return (
    <article className={styles.panel} aria-labelledby="community-corridors-title">
      <div className={styles.header}>
        <div>
          <span className={styles.kicker}>
            <Radar aria-hidden="true" />
            {t("dashboard.communityCorridors.eyebrow")}
          </span>
          <h4 id="community-corridors-title">
            {t("dashboard.communityCorridors.title")}
          </h4>
        </div>
        <span className={styles.period}>{t("dashboard.communityCorridors.period")}</span>
      </div>

      {isLoading ? (
        <BoneyardLoad name="community-corridors-load" className={styles.loading} ariaLabel={t("dashboard.communityCorridors.loading")}>
          <div className={styles.heatStrip} aria-hidden="true">
            {Array.from({ length: 10 }, (_, index) => (
              <LoadReference key={index} shape="block" className={styles.heatLoad} />
            ))}
          </div>
          {Array.from({ length: 5 }, (_, index) => (
            <LoadReference key={index} className={styles.rowLoad} />
          ))}
        </BoneyardLoad>
      ) : routes.length > 0 ? (
        <>
          <div className={styles.heatStrip} aria-label={t("dashboard.communityCorridors.heatAria")}>
            {routes.map((route, index) => {
              const weight = Math.max(18, Math.round((route.searches_count / strongest) * 100));
              return (
                <span
                  key={`${route.origin_iata}-${route.destination_iata}`}
                  className={styles.heatCell}
                  style={{
                    background: `color-mix(in srgb, var(--color-accent) ${weight}%, var(--color-surface-elevated))`,
                  }}
                  title={`${route.origin_iata} → ${route.destination_iata}: ${route.searches_count}`}
                >
                  <span className="sr-only">{index + 1}</span>
                </span>
              );
            })}
          </div>
          <ol className={styles.list}>
            {routes.map((route, index) => (
              <li key={`${route.origin_iata}-${route.destination_iata}`}>
                <Link
                  className={index === 0 ? styles.topRoute : styles.route}
                  href={`/quick-search?origin=${route.origin_iata}&destination=${route.destination_iata}`}
                >
                  <span className={styles.rank}>{String(index + 1).padStart(2, "0")}</span>
                  <strong>{route.origin_iata} → {route.destination_iata}</strong>
                  <span className={styles.count}>
                    {t("dashboard.communityCorridors.searches", { count: route.searches_count })}
                  </span>
                  <ChevronRight aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ol>
        </>
      ) : (
        <div className={styles.empty}>
          <span className={styles.emptyStrip} aria-hidden="true" />
          <strong>{t("dashboard.communityCorridors.emptyTitle")}</strong>
          <p>{t("dashboard.communityCorridors.emptyBody")}</p>
        </div>
      )}
    </article>
  );
}
