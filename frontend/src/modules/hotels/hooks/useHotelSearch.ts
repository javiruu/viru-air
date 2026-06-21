"use client";

import { useCallback, useMemo, useState } from "react";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import {
  HotelsRequestError,
  areaResolve,
  areaSearch,
  ingestHotelsMock,
  searchHotels,
} from "../api";
import type { HotelAreaResolveOut, HotelAreaSearchResultOut, HotelSearchOut } from "../types";

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

function defaultCheckIn(): string {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().slice(0, 10);
}

function defaultCheckOut(): string {
  const d = new Date();
  d.setDate(d.getDate() + 14);
  return d.toISOString().slice(0, 10);
}

export function useHotelSearch(onAfterIngest?: () => Promise<void>) {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();

  // ── Name/City search ────────────────────────────────────────────
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [searchMode, setSearchMode] = useState<"name" | "area">("name");

  // ── Area search ─────────────────────────────────────────────────
  const [areaQuery, setAreaQuery] = useState("");
  const [areaSuggestions, setAreaSuggestions] = useState<HotelAreaResolveOut[]>([]);
  const [areaResolved, setAreaResolved] = useState<HotelAreaResolveOut | null>(null);
  const [areaResolving, setAreaResolving] = useState(false);
  const [checkIn, setCheckIn] = useState(defaultCheckIn);
  const [checkOut, setCheckOut] = useState(defaultCheckOut);
  const [guests, setGuests] = useState(2);
  const [radiusKm, setRadiusKm] = useState(10);
  const [useProvider, setUseProvider] = useState(false);
  const [areaResults, setAreaResults] = useState<HotelAreaSearchResultOut[]>([]);

  // ── Shared ──────────────────────────────────────────────────────
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<HotelSearchOut[]>([]);
  const [selectedHotelId, setSelectedHotelId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedHotel = useMemo(
    () => results.find((item) => item.id === selectedHotelId) ?? null,
    [results, selectedHotelId],
  );
  const featureDisabled = Boolean(errorMessage && errorMessage.includes("HOTEL_FEATURE_ENABLED"));

  // ── Name search ─────────────────────────────────────────────────
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
    // Clear area results when switching to name mode
    if (searchMode === "name") {
      setAreaResults([]);
    }
    try {
      if (searchMode === "area" && areaResolved && checkIn && checkOut) {
        const list = await areaSearch({
          latitude: areaResolved.latitude,
          longitude: areaResolved.longitude,
          radius_km: radiusKm,
          check_in: checkIn,
          check_out: checkOut,
          guests,
          use_provider: useProvider,
        });
        setAreaResults(list);
        const derived: HotelSearchOut[] = list.map((r) => ({
          id: r.hotel_id,
          canonical_name: r.canonical_name,
          city: r.city,
          country_code: r.country_code,
          stars: r.stars,
        }));
        setResults(derived);
        if (!derived.some((item) => item.id === selectedHotelId)) {
          setSelectedHotelId(derived[0]?.id ?? null);
        }
      } else {
        await runSearch();
      }
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      setErrorMessage(message);
      notify({ tone: "error", title: message });
    } finally {
      setLoading(false);
    }
  }, [runSearch, t, notify, searchMode, areaResolved, checkIn, checkOut, guests, radiusKm, useProvider, selectedHotelId]);

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

  // ── Area resolve (autocomplete) ─────────────────────────────────
  const handleAreaResolve = useCallback(async () => {
    if (areaQuery.trim().length < 2) {
      setAreaSuggestions([]);
      return;
    }
    setAreaResolving(true);
    try {
      const resolved = await areaResolve(areaQuery.trim());
      setAreaSuggestions([resolved]);
    } catch {
      setAreaSuggestions([]);
    } finally {
      setAreaResolving(false);
    }
  }, [areaQuery]);

  const handleSelectArea = useCallback((suggestion: HotelAreaResolveOut) => {
    setAreaResolved(suggestion);
    setAreaQuery(suggestion.area_label);
    setAreaSuggestions([]);
  }, []);

  // ── Area search active check ────────────────────────────────────
  const isAreaSearchActive = searchMode === "area" && areaResults.length > 0;

  return {
    query,
    setQuery,
    city,
    setCity,
    searchMode,
    setSearchMode,
    areaQuery,
    setAreaQuery,
    areaSuggestions,
    areaResolving,
    areaResolved,
    checkIn,
    setCheckIn,
    checkOut,
    setCheckOut,
    guests,
    setGuests,
    radiusKm,
    setRadiusKm,
    useProvider,
    setUseProvider,
    areaResults,
    isAreaSearchActive,
    loading,
    results,
    selectedHotelId,
    setSelectedHotelId,
    selectedHotel,
    errorMessage,
    featureDisabled,
    handleSearch,
    handleIngest,
    handleAreaResolve,
    handleSelectArea,
    runSearch,
  };
}
