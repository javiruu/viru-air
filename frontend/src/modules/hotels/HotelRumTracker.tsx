"use client";

import { useEffect } from "react";

import { trackUxEvent } from "@/lib/uxTracking";

import {
  HOTEL_RUM_EVENT,
  buildHotelRumMetadata,
  hasHotelRumConsent,
  shouldFlushHotelRumVisibility,
  type HotelRumMetric,
} from "./hotelRum";

function readNavigationType(): string {
  if (typeof performance === "undefined") return "navigate";
  const entry = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
  return entry?.type || "navigate";
}

export function HotelRumTracker() {
  useEffect(() => {
    if (typeof window === "undefined" || !hasHotelRumConsent(window.localStorage)) return;

    const sent = new Set<string>();
    const observations = new Map<HotelRumMetric, number>();
    const observers: Array<{
      observer: PerformanceObserver;
      callback: (entry: PerformanceEntry) => void;
    }> = [];

    const remember = (metric: HotelRumMetric, value: number) => {
      if (Number.isFinite(value) && value >= 0) observations.set(metric, value);
    };

    const observe = (
      type: string,
      callback: (entry: PerformanceEntry) => void,
      options: { buffered?: boolean; durationThreshold?: number } = {},
    ) => {
      try {
        const observer = new PerformanceObserver((list) => list.getEntries().forEach(callback));
        observer.observe({ type, buffered: options.buffered ?? true, ...options } as PerformanceObserverInit);
        observers.push({ observer, callback });
      } catch {
        // Unsupported metric must not affect hotel search.
      }
    };

    observe("largest-contentful-paint", (entry) => {
      const paint = entry as PerformancePaintTiming & { renderTime?: number };
      const candidate = paint.renderTime || entry.startTime;
      remember("lcp", candidate);
    });
    observe("layout-shift", (entry) => {
      const shift = entry as PerformanceEntry & { hadRecentInput?: boolean; value?: number };
      if (!shift.hadRecentInput) {
        remember("cls", (observations.get("cls") || 0) + (shift.value || 0));
      }
    });
    observe("event", (entry) => {
      const interaction = entry as PerformanceEntry & { duration?: number; interactionId?: number };
      if ((interaction.interactionId || 0) > 0) remember("inp", Math.max(observations.get("inp") || 0, interaction.duration || 0));
    }, { buffered: false, durationThreshold: 16 });

    const navigation = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    if (navigation && Number.isFinite(navigation.responseStart)) remember("ttfb", navigation.responseStart - navigation.startTime);

    let flushed = false;
    const flush = () => {
      if (flushed) return;
      observers.forEach(({ observer, callback }) => {
        observer.takeRecords().forEach(callback);
      });
      flushed = true;
      for (const [metric, value] of observations) {
        const metadata = buildHotelRumMetadata(metric, value, {
          navigationType: readNavigationType(),
          viewportWidth: window.innerWidth,
        });
        if (!metadata) continue;
        const dedupeKey = `${metadata.metric}:${metadata.value_bucket}:${metadata.navigation_type}:${metadata.device_class}`;
        if (sent.has(dedupeKey)) continue;
        sent.add(dedupeKey);
        void trackUxEvent(HOTEL_RUM_EVENT, metadata);
      }
    };

    const handleVisibilityChange = () => {
      if (shouldFlushHotelRumVisibility(document.visibilityState)) flush();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pagehide", flush);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("pagehide", flush);
      flush();
      observers.forEach(({ observer }) => observer.disconnect());
    };
  }, []);

  return null;
}
