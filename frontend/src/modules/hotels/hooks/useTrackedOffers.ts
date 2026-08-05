"use client";

import { useCallback, useMemo, useState } from "react";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { createTrackedOffer, deleteTrackedOffer, listTrackedOffers } from "../api";
import type { HotelRateOut, HotelSearchOut, HotelTrackedOfferOut } from "../types";
import { resolveHotelMessage } from "./useHotelSearch";

export function useTrackedOffers(
  results: HotelSearchOut[],
  selectedHotelId: string | null,
  rates: HotelRateOut[],
) {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();

  const [trackedOffers, setTrackedOffers] = useState<HotelTrackedOfferOut[]>([]);
  const [trackedOffersLoading, setTrackedOffersLoading] = useState(false);
  const [trackedBusyOfferIds, setTrackedBusyOfferIds] = useState<string[]>([]);
  const [trackedBusyHotelIds, setTrackedBusyHotelIds] = useState<string[]>([]);

  const trackedHotelIds = useMemo(
    () => trackedOffers.filter((o) => o.is_active).map((o) => o.hotel_id),
    [trackedOffers],
  );

  const refreshTrackedOffers = useCallback(async () => {
    setTrackedOffersLoading(true);
    try {
      const offers = await listTrackedOffers();
      setTrackedOffers(offers);
    } catch {
      // silently ignore — tracked offers are secondary
    } finally {
      setTrackedOffersLoading(false);
    }
  }, []);

  const handleTrackPrice = useCallback(
    async (hotelId: string) => {
      setTrackedBusyHotelIds((current) => [...current, hotelId]);
      try {
        const hotel = results.find((h) => h.id === hotelId);
        const hotelRates = hotelId === selectedHotelId ? rates : [];
        const cheapest =
          hotelRates.length > 0
            ? [...hotelRates].sort((a, b) => a.amount - b.amount)[0]
            : null;
        // H46: never create tracking silently with defaults that look complete.
        // Without an eligible stay (observed price/rates) block with a reason
        // and offer a safe alternative.
        if (cheapest === null) {
          notify({ tone: "warning", title: t("hotels.messages.trackingNeedsContext") });
          return;
        }
        await createTrackedOffer({
          hotel_id: hotelId,
          area_label: hotel?.city || undefined,
          provider: cheapest?.provider || "mock",
          currency: cheapest?.currency || "EUR",
          check_in: cheapest?.check_in || undefined,
          check_out: cheapest?.check_out || undefined,
          guests: cheapest?.guests || undefined,
          initial_price: cheapest ? cheapest.amount : undefined,
        });
        await refreshTrackedOffers();
        notify({ tone: "success", title: t("hotels.messages.trackedOfferCreated") });
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        notify({ tone: "error", title: message });
      } finally {
        setTrackedBusyHotelIds((current) => current.filter((id) => id !== hotelId));
      }
    },
    [results, selectedHotelId, rates, refreshTrackedOffers, notify, t],
  );

  const handleStopTracking = useCallback(
    async (offerId: string) => {
      setTrackedBusyOfferIds((current) => [...current, offerId]);
      try {
        await deleteTrackedOffer(offerId);
        await refreshTrackedOffers();
        notify({ tone: "success", title: t("hotels.messages.trackedOfferDeleted") });
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        notify({ tone: "error", title: message });
      } finally {
        setTrackedBusyOfferIds((current) => current.filter((id) => id !== offerId));
      }
    },
    [refreshTrackedOffers, notify, t],
  );

  return {
    trackedOffers,
    trackedOffersLoading,
    trackedBusyOfferIds,
    trackedBusyHotelIds,
    trackedHotelIds,
    refreshTrackedOffers,
    handleTrackPrice,
    handleStopTracking,
  };
}
