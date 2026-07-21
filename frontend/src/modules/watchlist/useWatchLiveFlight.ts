"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/modules/shared/api";
import type { LiveFlightTracking } from "@/modules/watchlist/liveFlightTypes";

const ERROR_RETRY_SECONDS = 300;

export function useWatchLiveFlight(watchId: string | null) {
  const [data, setData] = useState<LiveFlightTracking | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [hasError, setHasError] = useState(false);
  const refreshRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!watchId) {
      setData(null);
      setIsLoading(false);
      setIsRefreshing(false);
      setHasError(false);
      refreshRef.current = null;
      return;
    }

    let disposed = false;
    let hasResolvedData = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;

    const clearTimer = () => {
      if (timer) clearTimeout(timer);
      timer = null;
    };

    const schedule = (seconds: number) => {
      clearTimer();
      if (disposed || document.hidden) return;
      const boundedSeconds = Math.max(30, Math.min(21600, seconds));
      timer = setTimeout(() => void load(false), boundedSeconds * 1000);
    };

    const load = async (initial: boolean) => {
      clearTimer();
      controller?.abort();
      const requestController = new AbortController();
      controller = requestController;
      if (initial || !hasResolvedData) setIsLoading(true);
      else setIsRefreshing(true);

      try {
        const response = await apiFetch<LiveFlightTracking>(`/watchlist/${watchId}/live`, {
          signal: requestController.signal,
        });
        if (disposed || requestController.signal.aborted) return;
        hasResolvedData = true;
        setData(response);
        setHasError(false);
        schedule(response.refresh_after_seconds);
      } catch (error) {
        if (disposed || requestController.signal.aborted) return;
        setHasError(true);
        schedule(ERROR_RETRY_SECONDS);
      } finally {
        if (!disposed && controller === requestController) {
          setIsLoading(false);
          setIsRefreshing(false);
        }
      }
    };

    const handleVisibility = () => {
      if (document.hidden) {
        clearTimer();
        controller?.abort();
        return;
      }
      void load(false);
    };

    setData(null);
    setHasError(false);
    void load(true);
    refreshRef.current = () => void load(false);
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      disposed = true;
      clearTimer();
      controller?.abort();
      refreshRef.current = null;
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [watchId]);

  const refresh = useCallback(() => refreshRef.current?.(), []);

  return { data, isLoading, isRefreshing, hasError, refresh };
}
