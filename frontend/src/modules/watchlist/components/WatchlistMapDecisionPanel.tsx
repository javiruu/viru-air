"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { Map, MapControls, MapMarker, MapPopup, MapRoute, type MapRef } from "@/components/ui/map";
import { formatCurrency } from "@/modules/shared/format";
import type { WatchMapInsight, WatchMapMode, WatchMapRouteView } from "@/modules/watchlist/types";

type WatchlistMapDecisionPanelProps = {
  routes: WatchMapRouteView[];
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
  if (route.trend === "up") return "En subida";
  if (route.trend === "down") return "En bajada";
  return "Estable";
}

export function WatchlistMapDecisionPanel({
  routes,
  mode,
  insight,
  compareLimitExceeded,
  onFocusWatch,
}: WatchlistMapDecisionPanelProps) {
  const mapRef = useRef<MapRef>(null);
  const [activePopupWatchId, setActivePopupWatchId] = useState<string | null>(null);

  const visibleRoutes = useMemo(() => routes.slice(0, 4), [routes]);
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

  return (
    <section className="panel panel-soft watch-map-panel section-gap" aria-label="Mesa de decisiones de rutas">
      <div className="panel-header watch-map-header">
        <div>
          <h2 className="panel-title">Mesa de decisiones</h2>
          <p className="panel-subtitle">
            {mode === "compare" ? "Comparación activa de rutas" : "Ruta seleccionada en foco"}
          </p>
        </div>
        <span className={`watch-map-mode watch-map-mode-${mode}`}>{mode === "compare" ? "Modo comparación" : "Modo enfoque"}</span>
      </div>

      <div className="watch-map-copy">
        <span className={`watch-map-insight watch-map-insight-${insight.type}`}>{insight.text}</span>
        {compareLimitExceeded ? <span className="watch-map-limit">Se muestran hasta 4 rutas para mantener la lectura limpia.</span> : null}
      </div>

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
                <span>{route.priceCurrent != null ? formatCurrency(route.priceCurrent, route.currency) : "Sin dato"}</span>
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
                <span>{route.priceTarget != null ? `Objetivo ${formatCurrency(route.priceTarget, route.currency)}` : "Sin objetivo"}</span>
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
                    {popupRoute.origin} → {popupRoute.destination}
                  </strong>
                  <span>{trendLabel(popupRoute)}</span>
                </header>
                <p>
                  Actual:{" "}
                  {popupRoute.priceCurrent != null
                    ? formatCurrency(popupRoute.priceCurrent, popupRoute.currency)
                    : "Sin dato"}
                </p>
                <p>
                  Objetivo:{" "}
                  {popupRoute.priceTarget != null
                    ? formatCurrency(popupRoute.priceTarget, popupRoute.currency)
                    : "No definido"}
                </p>
                <button
                  type="button"
                  className="btn-secondary btn-compact"
                  onClick={() => onFocusWatch(popupRoute.watchId)}
                >
                  Ir al detalle
                </button>
              </article>
            </MapPopup>
          ) : null}
        </Map>
      </div>
    </section>
  );
}
