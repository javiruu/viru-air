import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/modules/shared/api";
import type { SearchResult } from "@/modules/quick-search/types";

export type WatchlistItemBrief = {
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
  const [watchedKeys, setWatchedKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    apiFetch<WatchlistItemBrief[]>("/watchlist")
      .then((items) => {
        if (cancelled) return;
        const keys = new Set<string>();
        if (Array.isArray(items)) {
          for (const item of items) {
            if (item.origin_iata && item.destination_iata && item.travel_date_local) {
              keys.add(buildWatchKey(item.origin_iata, item.destination_iata, item.travel_date_local));
            }
          }
        }
        setWatchedKeys(keys);
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
      return watchedKeys.has(buildWatchKeyFromResult(result));
    },
    [watchedKeys],
  );

  const markAsSaved = useCallback(
    (result: SearchResult) => {
      const key = buildWatchKeyFromResult(result);
      if (!watchedKeys.has(key)) {
        setWatchedKeys((prev) => {
          const next = new Set(prev);
          next.add(key);
          return next;
        });
      }
    },
    [watchedKeys],
  );

  return { isInWatchlist, markAsSaved };
}
