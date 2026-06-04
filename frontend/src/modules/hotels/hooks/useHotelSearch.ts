"use client";

import { useCallback, useMemo, useState } from "react";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { HotelsRequestError, ingestHotelsMock, searchHotels } from "../api";
import type { HotelSearchOut } from "../types";

function resolveHotelMessage(error: unknown, t: ReturnType<typeof useI18n>["t"]): string {
  if (error instanceof HotelsRequestError) {
    if (error.message.includes("HOTEL_FEATURE_ENABLED")) {
      return t("hotels.messages.featureDisabled");
    }
    if (error.message === "hotel_comp_set_member_already_exists") {
      return t("hotels.messages.memberAlreadyAdded");
    }
    if (error.message === "hotel_comp_set_anchor_cannot_be_member") {
      return t("hotels.messages.anchorCannotBeMember");
    }
    if (error.message === "hotel_not_found") {
      return t("hotels.messages.hotelNotFound");
    }
    if (error.message === "hotel_watchlist_item_already_exists") {
      return t("hotels.messages.watchAlreadyAdded");
    }
    if (error.message === "threshold_required_for_price_rule") {
      return t("hotels.alerts.validation.priceThresholdRequired");
    }
    if (error.message === "threshold_percent_required_for_parity_break") {
      return t("hotels.alerts.validation.parityThresholdRequired");
    }
    if (error.message === "threshold_amount_not_allowed_for_parity_break") {
      return t("hotels.alerts.validation.parityAmountNotAllowed");
    }
    return error.message;
  }
  if (error instanceof Error && error.message.includes("HOTEL_FEATURE_ENABLED")) {
    return t("hotels.messages.featureDisabled");
  }
  return error instanceof Error ? error.message : t("shared.errors.generic");
}

export { resolveHotelMessage };

export function useHotelSearch(onAfterIngest?: () => Promise<void>) {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();

  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<HotelSearchOut[]>([]);
  const [selectedHotelId, setSelectedHotelId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedHotel = useMemo(
    () => results.find((item) => item.id === selectedHotelId) ?? null,
    [results, selectedHotelId],
  );
  const featureDisabled = Boolean(errorMessage && errorMessage.includes("HOTEL_FEATURE_ENABLED"));

  const runSearch = useCallback(async () => {
    const list = await searchHotels({ q: query || undefined, city: city || undefined, limit: 30 });
    setResults(list);
    if (!list.some((item) => item.id === selectedHotelId)) {
      setSelectedHotelId(list[0]?.id ?? null);
    }
  }, [query, city, selectedHotelId]);

  const handleSearch = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      await runSearch();
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      setErrorMessage(message);
      notify({ tone: "error", title: message });
    } finally {
      setLoading(false);
    }
  }, [runSearch, t, notify]);

  const handleIngest = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const ingest = await ingestHotelsMock();
      notify({
        tone: "success",
        title: t("hotels.messages.ingestSuccess", { count: ingest.hotels_processed }),
      });
      await runSearch();
      await onAfterIngest?.();
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      setErrorMessage(message);
      notify({ tone: "error", title: message });
    } finally {
      setLoading(false);
    }
  }, [runSearch, t, notify, onAfterIngest]);

  return {
    query,
    setQuery,
    city,
    setCity,
    loading,
    results,
    selectedHotelId,
    setSelectedHotelId,
    selectedHotel,
    errorMessage,
    featureDisabled,
    handleSearch,
    handleIngest,
    runSearch,
  };
}
