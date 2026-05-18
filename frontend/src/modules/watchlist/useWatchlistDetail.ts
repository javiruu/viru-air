import { useEffect } from "react";

import { apiFetch } from "@/modules/shared/api";
import type { PriceSummary, WatchDetail } from "@/modules/watchlist/types";

type UseWatchlistDetailInput = {
  selectedWatchId: string;
  setSelectedWatchDetail: (value: WatchDetail | null) => void;
  setSelectedWatchSummary: (value: PriceSummary | null) => void;
  setIsLoadingSelectedWatchDetail: (value: boolean) => void;
};

export function useWatchlistDetail({
  selectedWatchId,
  setSelectedWatchDetail,
  setSelectedWatchSummary,
  setIsLoadingSelectedWatchDetail,
}: UseWatchlistDetailInput): void {
  useEffect(() => {
    if (!selectedWatchId) {
      setSelectedWatchDetail(null);
      setSelectedWatchSummary(null);
      return;
    }
    let isMounted = true;
    setIsLoadingSelectedWatchDetail(true);
    Promise.all([
      apiFetch<WatchDetail>(`/watchlist/${selectedWatchId}`),
      apiFetch<PriceSummary>(`/prices/summary?watch_id=${selectedWatchId}`),
    ])
      .then(([detail, summary]) => {
        if (!isMounted) return;
        setSelectedWatchDetail(detail);
        setSelectedWatchSummary(summary);
      })
      .catch(() => {
        if (!isMounted) return;
        setSelectedWatchDetail(null);
        setSelectedWatchSummary(null);
      })
      .finally(() => {
        if (isMounted) setIsLoadingSelectedWatchDetail(false);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedWatchId, setIsLoadingSelectedWatchDetail, setSelectedWatchDetail, setSelectedWatchSummary]);
}
