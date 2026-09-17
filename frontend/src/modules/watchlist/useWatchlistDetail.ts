import { useEffect } from "react";

import { getWatchDetailApiV1WatchlistWatchIdGet } from "@/api/generated/watchlist/watchlist";
import { summaryApiV1PricesSummaryGet } from "@/api/generated/prices/prices";
import {
  normalizeWatchDetailApiResponse,
  type WatchDetailApiResponse,
} from "@/modules/watchlist/watchlistApiCompatibility";
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
      getWatchDetailApiV1WatchlistWatchIdGet(selectedWatchId),
      summaryApiV1PricesSummaryGet({ watch_id: selectedWatchId }),
    ])
      .then(([detail, summary]) => {
        if (!isMounted) return;
        setSelectedWatchDetail(normalizeWatchDetailApiResponse(detail as unknown as WatchDetailApiResponse));
        setSelectedWatchSummary(summary as unknown as PriceSummary);
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
  }, [
    selectedWatchId,
    setIsLoadingSelectedWatchDetail,
    setSelectedWatchDetail,
    setSelectedWatchSummary,
  ]);
}
