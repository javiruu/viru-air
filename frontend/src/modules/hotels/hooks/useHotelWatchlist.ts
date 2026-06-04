"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { createHotelWatchlistItem, deleteHotelWatchlistItem, getHotelDetail, HotelsRequestError, listHotelWatchlist } from "../api";
import type { HotelDetailOut, HotelWatchlistEntry, HotelWatchlistItemOut } from "../types";
import { resolveHotelMessage } from "./useHotelSearch";

export function useHotelWatchlist() {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [watchlistItems, setWatchlistItems] = useState<HotelWatchlistItemOut[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [watchlistHotelCache, setWatchlistHotelCache] = useState<Record<string, HotelDetailOut>>({});
  const [watchlistUnavailableHotelIds, setWatchlistUnavailableHotelIds] = useState<string[]>([]);
  const [watchlistBusyHotelIds, setWatchlistBusyHotelIds] = useState<string[]>([]);
  const watchlistHotelCacheRef = useRef<Record<string, HotelDetailOut>>({});

  const watchlistHotelIds = useMemo(
    () => watchlistItems.map((item) => item.hotel_id),
    [watchlistItems],
  );

  const watchlistEntries = useMemo<HotelWatchlistEntry[]>(
    () =>
      watchlistItems.map((item) => ({
        item,
        hotel: watchlistHotelCache[item.hotel_id] ?? null,
        detailUnavailable: watchlistUnavailableHotelIds.includes(item.hotel_id),
      })),
    [watchlistHotelCache, watchlistItems, watchlistUnavailableHotelIds],
  );

  useEffect(() => {
    watchlistHotelCacheRef.current = watchlistHotelCache;
  }, [watchlistHotelCache]);

  const hydrateWatchlistHotels = useCallback(async (items: HotelWatchlistItemOut[]) => {
    const missingHotelIds = Array.from(
      new Set(
        items
          .map((item) => item.hotel_id)
          .filter((hotelId) => !watchlistHotelCacheRef.current[hotelId]),
      ),
    );

    if (missingHotelIds.length === 0) return;

    const results = await Promise.allSettled(
      missingHotelIds.map((hotelId) => getHotelDetail(hotelId)),
    );
    const nextCache: Record<string, HotelDetailOut> = {};
    const failedHotelIds: string[] = [];

    results.forEach((result, index) => {
      const hotelId = missingHotelIds[index];
      if (result.status === "fulfilled") {
        nextCache[hotelId] = result.value;
      } else {
        failedHotelIds.push(hotelId);
      }
    });

    const successfulHotelIds = Object.keys(nextCache);
    if (successfulHotelIds.length > 0) {
      setWatchlistHotelCache((current) => ({ ...current, ...nextCache }));
      setWatchlistUnavailableHotelIds((current) =>
        current.filter((hotelId) => !successfulHotelIds.includes(hotelId)),
      );
    }
    if (failedHotelIds.length > 0) {
      setWatchlistUnavailableHotelIds((current) =>
        Array.from(new Set([...current, ...failedHotelIds])),
      );
    }
  }, []);

  const refreshWatchlist = useCallback(async () => {
    setWatchlistLoading(true);
    setWatchlistError(null);
    try {
      const items = await listHotelWatchlist();
      setWatchlistItems(items);
      await hydrateWatchlistHotels(items);
    } catch (error) {
      setWatchlistError(
        resolveHotelMessage(error, t) || t("hotels.messages.watchlistLoadError"),
      );
    } finally {
      setWatchlistLoading(false);
    }
  }, [t, hydrateWatchlistHotels]);

  const markWatchlistBusy = useCallback((hotelId: string, isBusy: boolean) => {
    setWatchlistBusyHotelIds((current) => {
      if (isBusy) return current.includes(hotelId) ? current : [...current, hotelId];
      return current.filter((item) => item !== hotelId);
    });
  }, []);

  const handleAddWatch = useCallback(
    async (hotelId: string) => {
      markWatchlistBusy(hotelId, true);
      try {
        await createHotelWatchlistItem({
          hotel_id: hotelId,
          label: t("hotels.watchlist.defaultLabel"),
        });
        await refreshWatchlist();
        notify({ tone: "success", title: t("hotels.messages.watchAdded") });
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        if (error instanceof HotelsRequestError && error.message === "hotel_watchlist_item_already_exists") {
          await refreshWatchlist();
        }
        notify({ tone: "error", title: message });
      } finally {
        markWatchlistBusy(hotelId, false);
      }
    },
    [refreshWatchlist, markWatchlistBusy, t, notify],
  );

  const handleRemoveWatch = useCallback(
    async (itemId: string, hotelId: string) => {
      markWatchlistBusy(hotelId, true);
      try {
        await deleteHotelWatchlistItem(itemId);
        await refreshWatchlist();
        notify({ tone: "success", title: t("hotels.messages.watchRemoved") });
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        notify({ tone: "error", title: message });
      } finally {
        markWatchlistBusy(hotelId, false);
      }
    },
    [refreshWatchlist, markWatchlistBusy, t, notify],
  );

  return {
    watchlistItems,
    watchlistLoading,
    watchlistError,
    watchlistHotelIds,
    watchlistBusyHotelIds,
    watchlistEntries,
    watchlistHotelCache,
    setWatchlistHotelCache,
    setWatchlistUnavailableHotelIds,
    refreshWatchlist,
    handleAddWatch,
    handleRemoveWatch,
    hydrateWatchlistHotels,
  };
}
