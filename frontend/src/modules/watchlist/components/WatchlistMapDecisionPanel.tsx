"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { useI18n } from "@/i18n";
import { Map, MapControls, MapMarker, MapPopup, MapRoute, type MapRef } from "@/components/ui/map";
import { formatCurrency } from "@/modules/shared/format";
import type { WatchMapInsight, WatchMapMode, WatchMapRouteView } from "@/modules/watchlist/types";

type WatchlistMapDecisionPanelProps = {
  routes: WatchMapRouteView[];
  hasWatchItems: boolean;
  mode: WatchMapMode;
  insight: WatchMapInsight;
  compareLimitExceeded: boolean;
  onFocusWatch: (watchId: string) => void;
};

function routeColor(route: WatchMapRouteView) {
  if (route.isPrimary) return "#D95D39";
  return route.isCompared ? "#2E6E62" : "#8F7A65";
}

function trendLabel(route: WatchMapRouteView) {
  if (route.trend === "up") return "up";
  if (route.trend === "down") return "down";
  return "stable";
}

export function WatchlistMapDecisionPanel({
  routes,
  hasWatchItems,
  mode,
  insight,
  compareLimitExceeded,
  onFocusWatch,
}: WatchlistMapDecisionPanelProps) {
  const { t } = useI18n();
  const mapRef = useRef<MapRef>(null);
  const [activePopupWatchId, setActivePopupWatchId] = useState<string | null>(null);

  const visibleRoutes = useMemo(() => routes.slice(0, 4), [routes]);
  const hasMapData = visibleRoutes.length > 0;
  const primary = useMemo(
    () => visibleRoutes.find((route) => route.isPrimary) ?? visibleRoutes[0] ?? null,
    [visibleRoutes],
  );
  const popupRoute = useMemo(
    () =>
      visibleRoutes.find((route) => route.watchId === activePopupWatchId) ??
      primary ??
      null,
    [activePopupWatchId, primary, visibleRoutes],
  );

  useEffect(() => {
    if (!primary) return;
    const boundsPoints = (mode === "compare" ? visibleRoutes : [primary]).flatMap((route) => [
      route.originCoordinates,
      route.destinationCoordinates,
    ]);
    if (boundsPoints.length < 2) return;
    const lngs = boundsPoints.map((point) => point[0]);
    const lats = boundsPoints.map((point) => point[1]);
    mapRef.current?.fitBounds(
      [
        [Math.min(...lngs), Math.min(...lats)],
        [Math.max(...lngs), Math.max(...lats)],
      ],
      { padding: 84, duration: 250, maxZoom: mode === "single" ? 6 : 5.5 },
    );
  }, [mode, primary, visibleRoutes]);

  useEffect(() => {
    if (!activePopupWatchId && primary) setActivePopupWatchId(primary.watchId);
  }, [activePopupWatchId, primary]);

  if (!hasMapData) {
    return (
      <section className="panel panel-soft watch-map-panel section-gap" aria-label={t("watchlist.map.title")}>
        <div className="panel-header watch-map-header">
          <div>
            <h2 className="panel-title">{t("watchlist.map.title")}</h2>
          </div>
        </div>
        <div className="watch-map-copy">
          <span className="watch-map-insight watch-map-insight-neutral">
            {hasWatchItems ? t("watchlist.map.unavailableTitle") : t("watchlist.map.emptyTitle")}
          </span>
          <span className="watch-map-limit">
            {hasWatchItems ? t("watchlist.map.unavailableBody") : t("watchlist.map.emptyBody")}
          </span>
        </div>
      </section>
    );
  }

  return (
    <section className="panel panel-soft watch-map-panel section-gap" aria-label={t("watchlist.map.title")}>
      <div className="panel-header watch-map-header">
        <div>
          <h2 className="panel-title">{t("watchlist.map.title")}</h2>
          <p className="panel-subtitle">
            {mode === "compare" ? t("watchlist.map.compareMode") : t("watchlist.map.focusMode")}
          </p>
        </div>
        <span className={`watch-map-mode watch-map-mode-${mode}`}>
          {mode === "compare" ? t("watchlist.map.comparePill") : t("watchlist.map.focusPill")}
        </span>
      </div>

      <div className="watch-map-copy">
        <span className={`watch-map-insight watch-map-insight-${insight.type}`}>{insight.text}</span>
        {compareLimitExceeded ? <span className="watch-map-limit">{t("watchlist.map.compareLimitHint")}</span> : null}
      </div>
      {hasMapData ? (
        <div className="watch-map-legend" role="note" aria-label={t("watchlist.map.legendAriaLabel")}>
          <span className="watch-map-legend-item">
            <span className="watch-map-legend-swatch watch-map-legend-swatch-primary" aria-hidden="true" />
            <span>{t("watchlist.map.legendPrimary")}</span>
          </span>
          <span className="watch-map-legend-item">
            <span className="watch-map-legend-swatch watch-map-legend-swatch-compared" aria-hidden="true" />
            <span>{t("watchlist.map.legendCompared")}</span>
          </span>
          <span className="watch-map-legend-item">
            <span className="watch-map-legend-swatch watch-map-legend-swatch-other" aria-hidden="true" />
            <span>{t("watchlist.map.legendOther")}</span>
          </span>
        </div>
      ) : null}

      <div className="watch-map-stage">
        <Map ref={mapRef} center={[-3.7, 40.4]} zoom={4.3} className="watch-map-canvas">
          <MapControls />
          {visibleRoutes.map((route) => {
            const isPrimary = route.isPrimary;
            return (
              <MapRoute
                key={`route-${route.watchId}`}
                id={`watch-route-${route.watchId}`}
                coordinates={[route.originCoordinates, route.destinationCoordinates]}
                color={routeColor(route)}
                width={isPrimary ? 5 : 3}
                opacity={isPrimary ? 0.95 : 0.45}
                dashArray={isPrimary ? undefined : [1.1, 1.2]}
                onClick={() => {
                  setActivePopupWatchId(route.watchId);
                  onFocusWatch(route.watchId);
                }}
              />
            );
          })}

          {visibleRoutes.map((route) => (
            <MapMarker
              key={`marker-origin-${route.watchId}`}
              longitude={route.originCoordinates[0]}
              latitude={route.originCoordinates[1]}
              onClick={() => {
                setActivePopupWatchId(route.watchId);
                onFocusWatch(route.watchId);
              }}
            >
              <div className={`watch-map-chip ${route.isPrimary ? "is-primary" : ""}`}>
                <strong>{route.origin}</strong>
                <span>{route.priceCurrent != null ? formatCurrency(route.priceCurrent, route.currency) : t("watchlist.compare.noData")}</span>
              </div>
            </MapMarker>
          ))}

          {visibleRoutes.map((route) => (
            <MapMarker
              key={`marker-destination-${route.watchId}`}
              longitude={route.destinationCoordinates[0]}
              latitude={route.destinationCoordinates[1]}
              onClick={() => {
                setActivePopupWatchId(route.watchId);
                onFocusWatch(route.watchId);
              }}
            >
              <div className={`watch-map-chip watch-map-chip-destination ${route.isPrimary ? "is-primary" : ""}`}>
                <strong>{route.destination}</strong>
                <span>{route.priceTarget != null ? t("watchlist.map.targetLabel", { value: formatCurrency(route.priceTarget, route.currency) }) : t("watchlist.map.noTarget")}</span>
              </div>
            </MapMarker>
          ))}

          {popupRoute ? (
            <MapPopup
              longitude={(popupRoute.originCoordinates[0] + popupRoute.destinationCoordinates[0]) / 2}
              latitude={(popupRoute.originCoordinates[1] + popupRoute.destinationCoordinates[1]) / 2}
              closeButton
              onClose={() => setActivePopupWatchId(null)}
            >
              <article className="watch-map-popup">
                <header>
                  <strong>
                    {popupRoute.origin} {"->"} {popupRoute.destination}
                  </strong>
                  <span>
                    {trendLabel(popupRoute) === "up"
                      ? t("watchlist.smartList.trendUp")
                      : trendLabel(popupRoute) === "down"
                        ? t("watchlist.smartList.trendDown")
                        : t("watchlist.smartList.trendStable")}
                  </span>
                </header>
                <p>
                  {t("watchlist.compare.current")}:{" "}
                  {popupRoute.priceCurrent != null
                    ? formatCurrency(popupRoute.priceCurrent, popupRoute.currency)
                    : t("watchlist.compare.noData")}
                </p>
                <p>
                  {t("watchlist.map.targetLabelShort")}:{" "}
                  {popupRoute.priceTarget != null
                    ? formatCurrency(popupRoute.priceTarget, popupRoute.currency)
                    : t("watchlist.map.noTarget")}
                </p>
                <button
                  type="button"
                  className="btn-secondary btn-compact"
                  onClick={() => onFocusWatch(popupRoute.watchId)}
                >
                  {t("watchlist.map.goToDetail")}
                </button>
              </article>
            </MapPopup>
          ) : null}
        </Map>
      </div>
    </section>
  );
}
