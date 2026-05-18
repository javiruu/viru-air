"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { useI18n } from "@/i18n";
import { Map, MapControls, MapMarker, MapPopup, MapRoute, type MapRef } from "@/components/ui/map";
import { getWatchStatusMeta } from "@/modules/shared/statusCatalog";
import { formatCurrency } from "@/modules/shared/format";
import { safeDateTime } from "@/modules/watchlist/presentation";
import type { WatchMapInsight, WatchMapMode, WatchMapRouteView } from "@/modules/watchlist/types";

type WatchlistMapDecisionPanelProps = {
  routes: WatchMapRouteView[];
  hasSelectedRoute: boolean;
  hasWatchItems: boolean;
  selectedRouteContext: {
    origin: string;
    destination: string;
    travelDate: string;
    status: string;
    lastCaptureAt: string | null;
  } | null;
  mode: WatchMapMode;
  insight: WatchMapInsight;
  compareLimitExceeded: boolean;
  onFocusWatch: (watchId: string) => void;
};

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return reduced;
}

function AnimatedRouteDot({ originCoordinates, destinationCoordinates }: {
  originCoordinates: [number, number];
  destinationCoordinates: [number, number];
}) {
  const reduced = useReducedMotion();
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (reduced) return;
    let startTime: number | null = null;
    const duration = 4000;
    let rafId: number;

    function tick(timestamp: number) {
      if (startTime === null) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const raw = (elapsed % duration) / duration;
      const eased = raw < 0.5
        ? 2 * raw * raw
        : 1 - Math.pow(-2 * raw + 2, 2) / 2;
      setProgress(eased);
      rafId = requestAnimationFrame(tick);
    }

    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [reduced]);

  if (reduced) return null;

  const lng = originCoordinates[0] + (destinationCoordinates[0] - originCoordinates[0]) * progress;
  const lat = originCoordinates[1] + (destinationCoordinates[1] - originCoordinates[1]) * progress;

  return (
    <MapMarker longitude={lng} latitude={lat}>
      <div className="watch-map-route-dot" aria-hidden="true" />
    </MapMarker>
  );
}

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
  hasSelectedRoute,
  hasWatchItems,
  selectedRouteContext,
  mode,
  insight,
  compareLimitExceeded,
  onFocusWatch,
}: WatchlistMapDecisionPanelProps) {
  const { t, localeTag } = useI18n();
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
  const selectedRouteLabel = primary ? `${primary.origin} → ${primary.destination}` : "--";
  const selectedStatus = primary ? getWatchStatusMeta(primary.status, t) : null;
  const fallbackRouteLabel = selectedRouteContext ? `${selectedRouteContext.origin} → ${selectedRouteContext.destination}` : "--";
  const fallbackStatus = selectedRouteContext ? getWatchStatusMeta(selectedRouteContext.status, t) : null;

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

  if (!hasSelectedRoute) {
    return (
      <section className="panel panel-soft watch-map-panel section-gap" aria-label={t("watchlist.map.title")}>
        <div className="panel-header watch-map-header">
          <div>
            <h2 className="panel-title">{t("watchlist.map.title")}</h2>
            <p className="panel-subtitle">{t("watchlist.map.noRouteSelectedLabel")}</p>
          </div>
        </div>
        <div className="watch-map-empty-state" role="status" aria-live="polite">
          <div className="watch-map-empty-visual" aria-hidden="true">
            <span className="watch-map-empty-node watch-map-empty-node-origin">ORG</span>
            <span className="watch-map-empty-line" />
            <span className="watch-map-empty-node watch-map-empty-node-destination">DST</span>
          </div>
          <div className="watch-map-empty-copy">
            <strong>{t("watchlist.map.emptySelectionTitle")}</strong>
            <p className="panel-note">{t("watchlist.map.emptySelectionBody")}</p>
          </div>
        </div>
      </section>
    );
  }

  if (!hasMapData) {
    return (
      <section className="panel panel-soft watch-map-panel section-gap" aria-label={t("watchlist.map.title")}>
        <div className="panel-header watch-map-header">
          <div>
            <h2 className="panel-title">{t("watchlist.map.title")}</h2>
            <p className="panel-subtitle">{fallbackRouteLabel}</p>
          </div>
          {fallbackStatus ? <span className={`status-pill ${fallbackStatus.tone}`}>{fallbackStatus.label}</span> : null}
        </div>
        <div className="watch-map-empty-state" role="status" aria-live="polite">
          <div className="watch-map-empty-visual" aria-hidden="true">
            <span className="watch-map-empty-node watch-map-empty-node-origin">{selectedRouteContext?.origin ?? "ORG"}</span>
            <span className="watch-map-empty-line" />
            <span className="watch-map-empty-node watch-map-empty-node-destination">{selectedRouteContext?.destination ?? "DST"}</span>
          </div>
          <div className="watch-map-empty-copy">
            <strong>{hasWatchItems ? t("watchlist.map.unavailableTitle") : t("watchlist.map.emptyTitle")}</strong>
            <p className="panel-note">
              {hasWatchItems ? t("watchlist.map.unavailableBody") : t("watchlist.map.emptyBody")}
            </p>
          </div>
          {selectedRouteContext ? (
            <div className="watch-map-meta" role="list" aria-label={t("watchlist.map.metaAriaLabel")}>
              <div className="watch-map-meta-item" role="listitem">
                <span>{t("watchlist.map.originLabel")}</span>
                <strong>{selectedRouteContext.origin}</strong>
              </div>
              <div className="watch-map-meta-item" role="listitem">
                <span>{t("watchlist.map.destinationLabel")}</span>
                <strong>{selectedRouteContext.destination}</strong>
              </div>
              <div className="watch-map-meta-item" role="listitem">
                <span>{t("watchlist.map.dateLabel")}</span>
                <strong>{selectedRouteContext.travelDate || "--"}</strong>
              </div>
              <div className="watch-map-meta-item" role="listitem">
                <span>{t("watchlist.map.lastCaptureLabel")}</span>
                <strong>{selectedRouteContext.lastCaptureAt ? safeDateTime(selectedRouteContext.lastCaptureAt, localeTag) : "--"}</strong>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    );
  }

  return (
    <section className="panel panel-soft watch-map-panel section-gap" aria-label={t("watchlist.map.title")}>
      <div className="panel-header watch-map-header">
        <div>
          <h2 className="panel-title">{t("watchlist.map.title")}</h2>
          <p className="panel-subtitle">{selectedRouteLabel}</p>
        </div>
        {selectedStatus ? <span className={`status-pill ${selectedStatus.tone}`}>{selectedStatus.label}</span> : null}
      </div>

      <div className="watch-map-copy">
        <span className={`watch-map-insight watch-map-insight-${insight.type}`}>{insight.text}</span>
        {compareLimitExceeded ? <span className="watch-map-limit">{t("watchlist.map.compareLimitHint")}</span> : null}
      </div>
      {primary ? (
        <div className="watch-map-meta" role="list" aria-label={t("watchlist.map.metaAriaLabel")}>
          <div className="watch-map-meta-item" role="listitem">
            <span>{t("watchlist.map.originLabel")}</span>
            <strong>{primary.origin}</strong>
          </div>
          <div className="watch-map-meta-item" role="listitem">
            <span>{t("watchlist.map.destinationLabel")}</span>
            <strong>{primary.destination}</strong>
          </div>
          <div className="watch-map-meta-item" role="listitem">
            <span>{t("watchlist.map.dateLabel")}</span>
            <strong>{primary.travelDate || "--"}</strong>
          </div>
          <div className="watch-map-meta-item" role="listitem">
            <span>{t("watchlist.map.lastCaptureLabel")}</span>
            <strong>{primary.freshnessTs ? safeDateTime(primary.freshnessTs, localeTag) : "--"}</strong>
          </div>
        </div>
      ) : null}
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

          {primary ? (
            <AnimatedRouteDot
              originCoordinates={primary.originCoordinates}
              destinationCoordinates={primary.destinationCoordinates}
            />
          ) : null}

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
                <span>{route.priceCurrent != null ? formatCurrency(route.priceCurrent, route.currency, localeTag) : t("watchlist.compare.noData")}</span>
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
                <span>{route.priceTarget != null ? t("watchlist.map.targetLabel", { value: formatCurrency(route.priceTarget, route.currency, localeTag) }) : t("watchlist.map.noTarget")}</span>
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
                    {popupRoute.origin} {"→"} {popupRoute.destination}
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
                    ? formatCurrency(popupRoute.priceCurrent, popupRoute.currency, localeTag)
                    : t("watchlist.compare.noData")}
                </p>
                <p>
                  {t("watchlist.map.targetLabelShort")}:{" "}
                  {popupRoute.priceTarget != null
                    ? formatCurrency(popupRoute.priceTarget, popupRoute.currency, localeTag)
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
