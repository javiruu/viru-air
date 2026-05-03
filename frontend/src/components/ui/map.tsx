"use client";

import {
  createContext,
  forwardRef,
  type MutableRefObject,
  type ReactNode,
  useContext,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { createRoot, type Root } from "react-dom/client";
import maplibregl, { type LngLatBoundsLike, type LngLatLike, type Map as MapLibreMap } from "maplibre-gl";

type MapStyleSet = {
  light: string;
  dark: string;
};

export type MapViewport = {
  center: [number, number];
  zoom: number;
  bearing: number;
  pitch: number;
};

export type MapRef = {
  map: MapLibreMap | null;
  fitBounds: (bounds: LngLatBoundsLike, options?: maplibregl.FitBoundsOptions) => void;
  easeTo: (options: maplibregl.EaseToOptions) => void;
};

type MapProps = {
  center?: [number, number];
  zoom?: number;
  styles?: MapStyleSet;
  viewport?: MapViewport;
  onViewportChange?: (viewport: MapViewport) => void;
  fadeDuration?: number;
  className?: string;
  children?: ReactNode;
};

type MapContextValue = {
  map: MapLibreMap | null;
  mapContainer: MutableRefObject<HTMLDivElement | null>;
};

const MapContext = createContext<MapContextValue | null>(null);

const DEFAULT_STYLES: MapStyleSet = {
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
};

function getThemeStyle(styles: MapStyleSet): string {
  if (typeof document === "undefined") return styles.light;
  const theme = document.documentElement.getAttribute("data-theme");
  return theme === "dark" ? styles.dark : styles.light;
}

function createRendererHost() {
  const element = document.createElement("div");
  const root = createRoot(element);
  return { element, root };
}

function renderInHost(root: Root, children: ReactNode) {
  root.render(<>{children}</>);
}

function useMapContext(): MapContextValue {
  const context = useContext(MapContext);
  if (!context) {
    throw new Error("Map components must be used inside <Map>.");
  }
  return context;
}

export const Map = forwardRef<MapRef, MapProps>(function Map(
  { center = [-3.7, 40.4], zoom = 4, styles = DEFAULT_STYLES, viewport, onViewportChange, fadeDuration = 0, className, children },
  ref,
) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [readyMap, setReadyMap] = useState<MapLibreMap | null>(null);
  const activeThemeRef = useRef<"light" | "dark">(typeof document !== "undefined" && document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light");
  const currentStyles = useMemo(() => styles, [styles]);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const initialStyle = getThemeStyle(currentStyles);
    const initialViewport = viewport ?? { center, zoom, bearing: 0, pitch: 0 };
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: initialStyle,
      center: initialViewport.center as LngLatLike,
      zoom: initialViewport.zoom,
      bearing: initialViewport.bearing,
      pitch: initialViewport.pitch,
      attributionControl: false,
      fadeDuration,
    });

    map.addControl(new maplibregl.AttributionControl({ compact: true }));
    mapRef.current = map;
    setReadyMap(map);

    const onMoveEnd = () => {
      if (!onViewportChange) return;
      const c = map.getCenter();
      onViewportChange({
        center: [c.lng, c.lat],
        zoom: map.getZoom(),
        bearing: map.getBearing(),
        pitch: map.getPitch(),
      });
    };

    map.on("moveend", onMoveEnd);

    return () => {
      map.off("moveend", onMoveEnd);
      map.remove();
      mapRef.current = null;
      setReadyMap(null);
    };
  }, [center, currentStyles, fadeDuration, onViewportChange, viewport, zoom]);

  useEffect(() => {
    if (!readyMap || !viewport) return;
    readyMap.easeTo({
      center: viewport.center,
      zoom: viewport.zoom,
      bearing: viewport.bearing,
      pitch: viewport.pitch,
      duration: 250,
    });
  }, [readyMap, viewport]);

  useEffect(() => {
    if (!readyMap) return;
    const observer = new MutationObserver(() => {
      const nextTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
      if (nextTheme === activeThemeRef.current) return;
      activeThemeRef.current = nextTheme;
      readyMap.setStyle(nextTheme === "dark" ? currentStyles.dark : currentStyles.light);
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, [readyMap, currentStyles]);

  useImperativeHandle(
    ref,
    () => ({
      map: mapRef.current,
      fitBounds(bounds, options) {
        mapRef.current?.fitBounds(bounds, options);
      },
      easeTo(options) {
        mapRef.current?.easeTo(options);
      },
    }),
    [],
  );

  return (
    <MapContext.Provider value={{ map: readyMap, mapContainer }}>
      <div className={className} style={{ position: "relative", width: "100%", height: "100%" }}>
        <div ref={mapContainer} style={{ width: "100%", height: "100%" }} />
        {readyMap ? children : null}
      </div>
    </MapContext.Provider>
  );
});

type MapControlsProps = {
  showNavigation?: boolean;
};

export function MapControls({ showNavigation = true }: MapControlsProps) {
  const { map } = useMapContext();
  useEffect(() => {
    if (!map || !showNavigation) return;
    const nav = new maplibregl.NavigationControl({ visualizePitch: true, showCompass: true, showZoom: true });
    map.addControl(nav, "top-right");
    return () => {
      map.removeControl(nav);
    };
  }, [map, showNavigation]);
  return null;
}

type MapRouteProps = {
  id?: string;
  coordinates: [number, number][];
  color?: string;
  width?: number;
  opacity?: number;
  dashArray?: [number, number];
  interactive?: boolean;
  onClick?: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
};

export function MapRoute({
  id,
  coordinates,
  color = "#4285F4",
  width = 3,
  opacity = 0.8,
  dashArray,
  interactive = true,
  onClick,
  onMouseEnter,
  onMouseLeave,
}: MapRouteProps) {
  const { map } = useMapContext();
  const sourceId = useMemo(() => `route-src-${id ?? Math.random().toString(36).slice(2)}`, [id]);
  const layerId = useMemo(() => `route-layer-${id ?? Math.random().toString(36).slice(2)}`, [id]);

  useEffect(() => {
    if (!map) return;
    const addOrUpdate = () => {
      const data = {
        type: "FeatureCollection",
        features: [{ type: "Feature", geometry: { type: "LineString", coordinates }, properties: {} }],
      } as const;
      const existing = map.getSource(sourceId) as maplibregl.GeoJSONSource | undefined;
      if (existing) {
        existing.setData(data as any);
      } else {
        map.addSource(sourceId, { type: "geojson", data: data as any });
      }
      if (!map.getLayer(layerId)) {
        map.addLayer({
          id: layerId,
          type: "line",
          source: sourceId,
          paint: {
            "line-color": color,
            "line-width": width,
            "line-opacity": opacity,
            ...(dashArray ? { "line-dasharray": dashArray } : {}),
          },
          layout: interactive ? undefined : { visibility: "visible" },
        });
      } else {
        map.setPaintProperty(layerId, "line-color", color);
        map.setPaintProperty(layerId, "line-width", width);
        map.setPaintProperty(layerId, "line-opacity", opacity);
        if (dashArray) map.setPaintProperty(layerId, "line-dasharray", dashArray);
      }
    };

    if (map.isStyleLoaded()) addOrUpdate();
    else map.once("load", addOrUpdate);

    const handleClick = () => onClick?.();
    const handleMouseEnter = () => {
      map.getCanvas().style.cursor = "pointer";
      onMouseEnter?.();
    };
    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = "";
      onMouseLeave?.();
    };

    if (interactive) {
      map.on("click", layerId, handleClick);
      map.on("mouseenter", layerId, handleMouseEnter);
      map.on("mouseleave", layerId, handleMouseLeave);
    }

    return () => {
      if (interactive) {
        map.off("click", layerId, handleClick);
        map.off("mouseenter", layerId, handleMouseEnter);
        map.off("mouseleave", layerId, handleMouseLeave);
      }
      if (map.getLayer(layerId)) map.removeLayer(layerId);
      if (map.getSource(sourceId)) map.removeSource(sourceId);
    };
  }, [color, coordinates, dashArray, interactive, layerId, map, onClick, onMouseEnter, onMouseLeave, opacity, sourceId, width]);

  return null;
}

type MapMarkerProps = {
  longitude: number;
  latitude: number;
  children?: ReactNode;
  onClick?: () => void;
};

export function MapMarker({ longitude, latitude, children, onClick }: MapMarkerProps) {
  const { map } = useMapContext();
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const renderHostRef = useRef<{ element: HTMLDivElement; root: Root } | null>(null);

  useEffect(() => {
    if (!map) return;
    const host = createRendererHost();
    renderHostRef.current = host;
    renderInHost(host.root, children);
    host.element.className = "mapcn-marker-host";
    if (onClick) {
      host.element.addEventListener("click", onClick);
    }
    const marker = new maplibregl.Marker({ element: host.element }).setLngLat([longitude, latitude]).addTo(map);
    markerRef.current = marker;
    return () => {
      if (onClick) {
        host.element.removeEventListener("click", onClick);
      }
      marker.remove();
      host.root.unmount();
      markerRef.current = null;
      renderHostRef.current = null;
    };
  }, [children, map, latitude, longitude, onClick]);

  useEffect(() => {
    markerRef.current?.setLngLat([longitude, latitude]);
  }, [latitude, longitude]);

  useEffect(() => {
    if (!renderHostRef.current) return;
    renderInHost(renderHostRef.current.root, children);
  }, [children]);

  return null;
}

type MapPopupProps = {
  longitude: number;
  latitude: number;
  children?: ReactNode;
  onClose?: () => void;
  closeButton?: boolean;
  className?: string;
};

export function MapPopup({ longitude, latitude, children, onClose, closeButton = false, className }: MapPopupProps) {
  const { map } = useMapContext();
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const renderHostRef = useRef<{ element: HTMLDivElement; root: Root } | null>(null);

  useEffect(() => {
    if (!map) return;
    const host = createRendererHost();
    host.element.className = className ?? "mapcn-popup-host";
    renderHostRef.current = host;
    renderInHost(host.root, children);
    const popup = new maplibregl.Popup({ closeButton, closeOnClick: false })
      .setLngLat([longitude, latitude])
      .setDOMContent(host.element)
      .addTo(map);
    if (onClose) popup.on("close", onClose);
    popupRef.current = popup;
    return () => {
      if (onClose) popup.off("close", onClose);
      popup.remove();
      host.root.unmount();
      popupRef.current = null;
      renderHostRef.current = null;
    };
  }, [children, map, longitude, latitude, closeButton, className, onClose]);

  useEffect(() => {
    popupRef.current?.setLngLat([longitude, latitude]);
  }, [latitude, longitude]);

  useEffect(() => {
    if (!renderHostRef.current) return;
    renderInHost(renderHostRef.current.root, children);
  }, [children]);

  return null;
}
