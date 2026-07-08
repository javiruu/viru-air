import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/modules/shared/api";
import type { SearchResult } from "@/modules/quick-search/types";

export type WatchlistItemBrief = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
};

/**
 * Builds a stable key from a SearchResult that can be compared with watchlist items.
 */
export function buildWatchKey(
  origin: string,
  destination: string,
  travelDate: string,
): string {
  return `${origin}_${destination}_${travelDate}`;
}

export function buildWatchKeyFromResult(result: SearchResult): string {
  return buildWatchKey(result.origin, result.destination, result.travel_date);
}

/**
 * Hook that loads the user's watchlist items on mount and exposes
 * a Set of watched flight keys plus helpers to check & add entries.
 *
 * This allows the QuickSearch results list to show "Ya añadido" instead of
 * "Guardar" for flights already saved to the watchlist.
 */
export function useQuickSearchWatchlist() {
  const [watchedByKey, setWatchedByKey] = useState<Map<string, string>>(new Map());

  useEffect(() => {
    let cancelled = false;
    apiFetch<WatchlistItemBrief[]>("/watchlist")
      .then((items) => {
        if (cancelled) return;
        const nextWatchedByKey = new Map<string, string>();
        if (Array.isArray(items)) {
          for (const item of items) {
            if (item.id && item.origin_iata && item.destination_iata && item.travel_date_local) {
              nextWatchedByKey.set(buildWatchKey(item.origin_iata, item.destination_iata, item.travel_date_local), item.id);
            }
          }
        }
        setWatchedByKey(nextWatchedByKey);
      })
      .catch(() => {
        // Silently fail — the watchlist may not be available yet
        if (cancelled) return;
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const isInWatchlist = useCallback(
    (result: SearchResult): boolean => {
      return watchedByKey.has(buildWatchKeyFromResult(result));
    },
    [watchedByKey],
  );

  const getWatchId = useCallback(
    (result: SearchResult): string => {
      return watchedByKey.get(buildWatchKeyFromResult(result)) ?? "";
    },
    [watchedByKey],
  );

  const markAsSaved = useCallback(
    (result: SearchResult, watchId?: string | null) => {
      const key = buildWatchKeyFromResult(result);
      setWatchedByKey((prev) => {
        if (prev.get(key) === watchId || (!watchId && prev.has(key))) return prev;
        const next = new Map(prev);
        if (watchId) {
          next.set(key, watchId);
        } else if (!next.has(key)) {
          next.set(key, "");
        }
        return next;
      });
    },
    [],
  );

  return { isInWatchlist, getWatchId, markAsSaved };
}
