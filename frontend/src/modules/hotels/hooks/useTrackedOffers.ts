"use client";

import { useCallback, useMemo, useState } from "react";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { createTrackedOfferV2, deleteTrackedOffer, listTrackedOffersV2, transitionTrackedOfferV2Lifecycle } from "../api";
import type { HotelRateOut, HotelSearchOut, HotelTrackedOfferOut, HotelTrackedOfferV2Out, HotelTrackedOfferV2State, HotelTrackingCandidate } from "../types";
import { resolveHotelMessage } from "./useHotelSearch";

export function useTrackedOffers(
  results: HotelSearchOut[],
  selectedHotelId: string | null,
  rates: HotelRateOut[],
) {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();

  const [trackedOffers, setTrackedOffers] = useState<HotelTrackedOfferOut[]>([]);
  const [trackedOffersError, setTrackedOffersError] = useState<string | null>(null);
  const [trackedOffersLoading, setTrackedOffersLoading] = useState(false);
  const [trackedBusyOfferIds, setTrackedBusyOfferIds] = useState<string[]>([]);
  const [trackedBusyHotelIds, setTrackedBusyHotelIds] = useState<string[]>([]);
  const [trackingCandidate, setTrackingCandidate] = useState<HotelTrackingCandidate | null>(null);
  const [trackedOfferStates, setTrackedOfferStates] = useState<Record<string, HotelTrackedOfferV2State>>({});
  const [trackedOfferStateVersions, setTrackedOfferStateVersions] = useState<Record<string, number>>({});

  const toTrackedOfferView = useCallback((offer: HotelTrackedOfferV2Out): HotelTrackedOfferOut => {
    const observation = offer.latest_observation;
    const observedPrice = observation?.price.status === "observed" ? observation.price.amount : null;
    return {
      id: offer.id, user_id: "", hotel_id: offer.hotel_id, area_label: null, origin_query: null,
      latitude: null, longitude: null, radius_km: null,
      check_in: offer.stay_context.check_in, check_out: offer.stay_context.check_out, guests: offer.stay_context.guests,
      room_label: observation?.room_label ?? null, meal_plan: observation?.meal_plan ?? null,
      cancellation_policy: observation?.cancellation_policy ?? null, provider: observation?.provider ?? "unknown",
      initial_price: null, current_price: observedPrice, target_price: null, currency: offer.stay_context.currency,
      is_active: offer.state === "active", created_at: "", updated_at: "",
    };
  }, []);

  const trackedHotelIds = useMemo(
    () => trackedOffers.filter((o) => o.is_active).map((o) => o.hotel_id),
    [trackedOffers],
  );

  const refreshTrackedOffers = useCallback(async () => {
    setTrackedOffersLoading(true);
    try {
      const response = await listTrackedOffersV2();
      setTrackedOffers(response.data.map(toTrackedOfferView));
      setTrackedOfferStates(Object.fromEntries(response.data.map((offer) => [offer.id, offer.state])));
      setTrackedOfferStateVersions(Object.fromEntries(response.data.map((offer) => [offer.id, offer.state_version])));
      setTrackedOffersError(null);
    } catch (error) {
      setTrackedOffersError(
        error instanceof Error && error.message.includes("HOTEL_FEATURE_ENABLED")
          ? resolveHotelMessage(error, t)
          : t("hotels.trackedOffers.loadError"),
      );
    } finally {
      setTrackedOffersLoading(false);
    }
  }, [t, toTrackedOfferView]);

  const handleTrackPrice = useCallback(
    (hotelId: string) => {
      if (trackedBusyHotelIds.length > 0) return;

      const hotel = results.find((item) => item.id === hotelId);
      const hotelRates = hotelId === selectedHotelId ? rates : [];
      const cheapest = hotelRates.length > 0 ? [...hotelRates].sort((a, b) => a.amount - b.amount)[0] : null;
      // H46: never create tracking silently with defaults that look complete.
      if (hotel === undefined || cheapest === null) {
        notify({ tone: "warning", title: t("hotels.messages.trackingNeedsContext") });
        return;
      }

      setTrackingCandidate({ hotel, rate: cheapest });
    },
    [results, selectedHotelId, rates, trackedBusyHotelIds.length, notify, t],
  );

  const handleTrackRate = useCallback(
    (rate: HotelRateOut) => {
      if (trackedBusyHotelIds.length > 0) return;

      const hotel = results.find((item) => item.id === rate.hotel_id);
      if (hotel === undefined) {
        notify({ tone: "warning", title: t("hotels.messages.trackingNeedsContext") });
        return;
      }

      setTrackingCandidate({ hotel, rate });
    },
    [results, trackedBusyHotelIds.length, notify, t],
  );

  const handleConfirmTracking = useCallback(async () => {
    if (trackingCandidate === null) return;

    const { hotel, rate } = trackingCandidate;
    setTrackedBusyHotelIds((current) => [...current, hotel.id]);
    try {
      const created = await createTrackedOfferV2(rate.id);
      await refreshTrackedOffers();
      setTrackingCandidate(null);
      notify({
        tone: "success",
        title: t(
          created.creation.outcome === "existing"
            ? "hotels.messages.trackedOfferAlreadyExists"
            : "hotels.messages.trackedOfferCreated",
        ),
      });
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      notify({ tone: "error", title: message });
    } finally {
      setTrackedBusyHotelIds((current) => current.filter((id) => id !== hotel.id));
    }
  }, [trackingCandidate, refreshTrackedOffers, notify, t]);

  const handleCloseTrackingConfirmation = useCallback(() => {
    setTrackingCandidate(null);
  }, []);

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

  const handleSetTrackingActive = useCallback(
    async (offerId: string, isActive: boolean) => {
      const expectedStateVersion = trackedOfferStateVersions[offerId];
      if (expectedStateVersion === undefined) {
        notify({ tone: "error", title: t("hotels.trackedOffers.loadError") });
        return;
      }
      setTrackedBusyOfferIds((current) => [...current, offerId]);
      try {
        const transition = await transitionTrackedOfferV2Lifecycle(
          offerId,
          isActive ? "resume" : "pause",
          expectedStateVersion,
        );
        await refreshTrackedOffers();
        notify({
          tone: transition.outcome === "expired" ? "warning" : "success",
          title: t(
            transition.outcome === "expired"
              ? "hotels.messages.trackedOfferExpired"
              : isActive
                ? "hotels.messages.trackedOfferResumed"
                : "hotels.messages.trackedOfferPaused",
          ),
        });
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        notify({ tone: "error", title: message });
      } finally {
        setTrackedBusyOfferIds((current) => current.filter((id) => id !== offerId));
      }
    },
    [refreshTrackedOffers, trackedOfferStateVersions, notify, t],
  );

  const handleArchiveTracking = useCallback(
    async (offerId: string) => {
      const expectedStateVersion = trackedOfferStateVersions[offerId];
      if (expectedStateVersion === undefined) {
        notify({ tone: "error", title: t("hotels.trackedOffers.loadError") });
        return;
      }
      setTrackedBusyOfferIds((current) => [...current, offerId]);
      try {
        await transitionTrackedOfferV2Lifecycle(offerId, "archive", expectedStateVersion);
        await refreshTrackedOffers();
        notify({ tone: "success", title: t("hotels.messages.trackedOfferArchived") });
      } catch (error) {
        notify({ tone: "error", title: resolveHotelMessage(error, t) });
      } finally {
        setTrackedBusyOfferIds((current) => current.filter((id) => id !== offerId));
      }
    },
    [refreshTrackedOffers, trackedOfferStateVersions, notify, t],
  );

  return {
    trackedOffers,
    trackedOffersError,
    trackedOfferStates,
    trackedOfferStateVersions,
    trackedOffersLoading,
    trackedBusyOfferIds,
    trackedBusyHotelIds,
    trackedHotelIds,
    trackingCandidate,
    refreshTrackedOffers,
    handleTrackPrice,
    handleTrackRate,
    handleConfirmTracking,
    handleCloseTrackingConfirmation,
    handleStopTracking,
    handleSetTrackingActive,
    handleArchiveTracking,
  };
}
