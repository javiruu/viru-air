"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import {
  HotelsRequestError,
  adaptAreaSearchV2ToV1,
  areaResolve,
  areaSearchV2,
  ingestHotelsMock,
  searchHotels,
} from "../api";
import type { HotelAreaResolveOut, HotelAreaSearchResultOut, HotelSearchOut } from "../types";
import { createHotelSearchIntentId } from "../searchIntent";
import {
  buildHotelSearchQuery,
  canonicalizeHotelSearchQuery,
  hasHotelSearchIntent,
  isHotelDateRangeValid,
  readHotelSearchUrlState,
} from "../hotelSearchUrlState";
import type { HotelReturnPanel } from "../hotelSearchUrlState";

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
  const router = useRouter();
  const searchParams = useSearchParams();
  const [urlHydrated, setUrlHydrated] = useState(false);
  const [urlSearchPending, setUrlSearchPending] = useState(false);
  const lastSyncedUrlRef = useRef<string | null>(null);

  // ── Name/City search ────────────────────────────────────────────
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [searchMode, setSearchMode] = useState<"name" | "area">("name");
  const [panel, setPanel] = useState<HotelReturnPanel>("search");

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
  const searchAbortRef = useRef<AbortController | null>(null);
  const searchRequestIdRef = useRef(0);
  const areaResolveAbortRef = useRef<AbortController | null>(null);
  const areaResolveRequestIdRef = useRef(0);
  const [selectedHotelId, setSelectedHotelId] = useState<string | null>(null);
  const [searchIntentId, setSearchIntentId] = useState<string | null>(null);
  const selectedHotelExplicitRef = useRef(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // H46: distinguishes first-visit idle (never searched) from a completed
  // search without matches (empty).
  const [hasSearched, setHasSearched] = useState(false);

  const selectedHotel = useMemo(
    () => results.find((item) => item.id === selectedHotelId) ?? null,
    [results, selectedHotelId],
  );
  const featureDisabled = Boolean(errorMessage && errorMessage.includes("HOTEL_FEATURE_ENABLED"));

  // ── Name search ─────────────────────────────────────────────────
  const beginSearchRequest = useCallback(() => {
    searchAbortRef.current?.abort();
    const controller = new AbortController();
    const requestId = searchRequestIdRef.current + 1;
    searchRequestIdRef.current = requestId;
    searchAbortRef.current = controller;
    const intentId = createHotelSearchIntentId();
    setSearchIntentId(intentId);
    return { controller, requestId, intentId };
  }, []);

  const runSearch = useCallback(async (request = beginSearchRequest()) => {
    const requestedSelectedHotelId = selectedHotelExplicitRef.current ? selectedHotelId : null;
    try {
      const list = await searchHotels(
        { q: query || undefined, city: city || undefined, limit: 30 },
        request.controller.signal,
        request.intentId,
      );
      if (request.controller.signal.aborted || request.requestId !== searchRequestIdRef.current) return;
      setResults(list);
      if (!list.some((item) => item.id === requestedSelectedHotelId)) {
        selectedHotelExplicitRef.current = false;
        setSelectedHotelId(list[0]?.id ?? null);
      }
    } finally {
      if (request.requestId === searchRequestIdRef.current) {
        searchAbortRef.current = null;
      }
    }
  }, [beginSearchRequest, query, city, selectedHotelId]);

  const handleSearch = useCallback(async (options?: { preserveSelection?: boolean }) => {
    if (searchMode === "area") {
      if (!areaResolved) {
        const message = t("hotels.messages.areaRequired");
        setErrorMessage(message);
        notify({ tone: "error", title: message });
        return;
      }
      if (!isHotelDateRangeValid(checkIn, checkOut)) {
        const message = t("hotels.messages.dateRangeInvalid");
        setErrorMessage(message);
        notify({ tone: "error", title: message });
        return;
      }
    }

    if (!options?.preserveSelection) {
      selectedHotelExplicitRef.current = false;
      setSelectedHotelId(null);
    }
    setHasSearched(true);
    setLoading(true);
    setErrorMessage(null);
    const request = beginSearchRequest();
    // Clear area results when switching to name mode
    if (searchMode === "name") {
      setAreaResults([]);
    }
    try {
      if (searchMode === "area" && areaResolved) {
        const response = await areaSearchV2({
          latitude: areaResolved.latitude,
          longitude: areaResolved.longitude,
          radius_km: radiusKm,
          check_in: checkIn,
          check_out: checkOut,
          guests,
          use_provider: useProvider,
        }, request.controller.signal, request.intentId);
        if (request.controller.signal.aborted || request.requestId !== searchRequestIdRef.current) return;
        const list = adaptAreaSearchV2ToV1(response);
        setAreaResults(list);
        const derived: HotelSearchOut[] = list.map((r) => ({
          id: r.hotel_id,
          canonical_name: r.canonical_name,
          city: r.city,
          country_code: r.country_code,
          stars: r.stars,
        }));
        setResults(derived);
        const requestedSelectedHotelId = selectedHotelExplicitRef.current ? selectedHotelId : null;
        if (!derived.some((item) => item.id === requestedSelectedHotelId)) {
          selectedHotelExplicitRef.current = false;
          setSelectedHotelId(derived[0]?.id ?? null);
        }
      } else {
        await runSearch(request);
      }
    } catch (error) {
      if (request.controller.signal.aborted || request.requestId !== searchRequestIdRef.current) return;
      const message = resolveHotelMessage(error, t);
      setErrorMessage(message);
      notify({ tone: "error", title: message });
    } finally {
      if (request.requestId === searchRequestIdRef.current) {
        searchAbortRef.current = null;
        setLoading(false);
      }
    }
  }, [beginSearchRequest, runSearch, t, notify, searchMode, areaResolved, checkIn, checkOut, guests, radiusKm, useProvider, selectedHotelId]);

  const handleIngest = useCallback(async () => {
    setHasSearched(true);
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
  const handleAreaQueryChange = useCallback((value: string) => {
    areaResolveAbortRef.current?.abort();
    areaResolveAbortRef.current = null;
    areaResolveRequestIdRef.current += 1;
    setAreaQuery(value);
    setAreaResolved(null);
    setAreaSuggestions([]);
  }, []);

  const handleSearchModeChange = useCallback((mode: "name" | "area") => {
    if (mode === "name") {
      areaResolveAbortRef.current?.abort();
      areaResolveAbortRef.current = null;
      areaResolveRequestIdRef.current += 1;
    }
    setSearchMode(mode);
    if (mode === "name") {
      setAreaQuery("");
      setAreaResolved(null);
      setAreaSuggestions([]);
      setAreaResults([]);
    }
  }, []);

  const handleAreaResolve = useCallback(async () => {
    const requestedQuery = areaQuery.trim();
    areaResolveAbortRef.current?.abort();
    areaResolveRequestIdRef.current += 1;
    const requestId = areaResolveRequestIdRef.current;
    if (requestedQuery.length < 2) {
      setAreaSuggestions([]);
      setAreaResolving(false);
      return;
    }
    const controller = new AbortController();
    areaResolveAbortRef.current = controller;
    setAreaResolving(true);
    try {
      const resolved = await areaResolve(requestedQuery, controller.signal);
      if (controller.signal.aborted || requestId !== areaResolveRequestIdRef.current) return;
      setAreaSuggestions([resolved]);
    } catch {
      if (controller.signal.aborted || requestId !== areaResolveRequestIdRef.current) return;
      setAreaSuggestions([]);
    } finally {
      if (requestId === areaResolveRequestIdRef.current) {
        areaResolveAbortRef.current = null;
        setAreaResolving(false);
      }
    }
  }, [areaQuery]);

  const handleSelectArea = useCallback((suggestion: HotelAreaResolveOut) => {
    setAreaResolved(suggestion);
    setAreaQuery(suggestion.area_label);
    setAreaSuggestions([]);
  }, []);

  useEffect(() => () => {
    searchAbortRef.current?.abort();
    areaResolveAbortRef.current?.abort();
  }, []);

  // ── Area search active check ────────────────────────────────────
  const isAreaSearchActive = searchMode === "area" && areaResults.length > 0;

  // Restore the canonical search context on first load and on browser
  // back/forward. Own router.replace calls are ignored to avoid loops.
  useEffect(() => {
    const rawQuery = searchParams.toString();
    const canonicalQuery = canonicalizeHotelSearchQuery(rawQuery);
    if (canonicalQuery === lastSyncedUrlRef.current) return;
    lastSyncedUrlRef.current = canonicalQuery;

    const state = readHotelSearchUrlState(searchParams);
    setPanel(state.panel);
    setSearchMode(state.mode);
    setQuery(state.query);
    setCity(state.city);
    setAreaQuery(state.areaQuery);
    setAreaResolved(state.areaResolved);
    setCheckIn((current) => searchParams.has("check_in") ? state.checkIn : current);
    setCheckOut((current) => searchParams.has("check_out") ? state.checkOut : current);
    setGuests(state.guests);
    setRadiusKm(state.radiusKm);
    setUseProvider(state.useProvider);
    selectedHotelExplicitRef.current = Boolean(state.selectedHotelId);
    setSelectedHotelId(state.selectedHotelId);
    setHasSearched(state.hasSearched);

    if (state.hasSearched && hasHotelSearchIntent(state)) {
      setResults([]);
      setAreaResults([]);
      setErrorMessage(null);
      setUrlSearchPending(true);
    } else if (!state.hasSearched) {
      setResults([]);
      setAreaResults([]);
      setErrorMessage(null);
      setUrlSearchPending(false);
    }
    setUrlHydrated(true);
  }, [searchParams]);

  // Re-run only searches explicitly marked as executed in the URL. This
  // makes reload/deep-link/back-forward useful without searching on typing.
  useEffect(() => {
    if (!urlHydrated || !urlSearchPending) return;
    if (searchMode === "area" && (!areaResolved || !isHotelDateRangeValid(checkIn, checkOut))) return;
    if (searchMode === "name" && !query.trim() && !city.trim()) return;
    setUrlSearchPending(false);
    void handleSearch({ preserveSelection: true });
  }, [
    areaResolved,
    checkIn,
    checkOut,
    city,
    handleSearch,
    query,
    searchMode,
    urlHydrated,
    urlSearchPending,
  ]);

  // Keep the form and selected hotel shareable. Defaults are omitted until
  // there is a real search intent, so a blank visit remains /hoteles.
  useEffect(() => {
    if (!urlHydrated) return;
    if (!hasSearched && searchMode === "name" && !query.trim() && !city.trim() && !selectedHotelId) return;

    const queryString = buildHotelSearchQuery({
      panel,
      mode: searchMode,
      query,
      city,
      areaQuery,
      areaResolved,
      checkIn,
      checkOut,
      guests,
      radiusKm,
      useProvider,
      hasSearched,
      selectedHotelId: selectedHotelExplicitRef.current ? selectedHotelId : null,
    });
    if (queryString === lastSyncedUrlRef.current) return;
    const canonicalQuery = canonicalizeHotelSearchQuery(queryString);
    if (canonicalQuery === lastSyncedUrlRef.current) return;
    lastSyncedUrlRef.current = canonicalQuery;
    router.replace(`/hoteles${queryString ? `?${queryString}` : ""}`, { scroll: false });
  }, [
    areaQuery,
    areaResolved,
    city,
    checkIn,
    checkOut,
    guests,
    hasSearched,
    query,
    panel,
    radiusKm,
    router,
    searchMode,
    selectedHotelId,
    urlHydrated,
    useProvider,
  ]);

  const selectHotel = useCallback((hotelId: string) => {
    selectedHotelExplicitRef.current = true;
    setPanel("detail");
    setSelectedHotelId(hotelId);
    const queryString = buildHotelSearchQuery({
      panel: "detail",
      mode: searchMode,
      query,
      city,
      areaQuery,
      areaResolved,
      checkIn,
      checkOut,
      guests,
      radiusKm,
      useProvider,
      hasSearched,
      selectedHotelId: hotelId,
    });
    lastSyncedUrlRef.current = canonicalizeHotelSearchQuery(queryString);
    router.push(`/hoteles${queryString ? `?${queryString}` : ""}`, { scroll: false });
  }, [
    areaQuery,
    areaResolved,
    checkIn,
    checkOut,
    city,
    guests,
    hasSearched,
    query,
    radiusKm,
    router,
    searchMode,
    useProvider,
  ]);

  const navigatePanel = useCallback((nextPanel: HotelReturnPanel) => {
    const nextSelectedHotelId = nextPanel === "search" ? null : selectedHotelId;
    setPanel(nextPanel);
    if (nextPanel === "search") {
      selectedHotelExplicitRef.current = false;
      setSelectedHotelId(null);
    }
    const queryString = buildHotelSearchQuery({
      panel: nextPanel,
      mode: searchMode,
      query,
      city,
      areaQuery,
      areaResolved,
      checkIn,
      checkOut,
      guests,
      radiusKm,
      useProvider,
      hasSearched,
      selectedHotelId: nextSelectedHotelId,
    });
    lastSyncedUrlRef.current = canonicalizeHotelSearchQuery(queryString);
    router.push(`/hoteles${queryString ? `?${queryString}` : ""}`, { scroll: false });
  }, [
    areaQuery,
    areaResolved,
    checkIn,
    checkOut,
    city,
    guests,
    hasSearched,
    query,
    radiusKm,
    router,
    searchMode,
    selectedHotelId,
    useProvider,
  ]);

  return {
    panel,
    navigatePanel,
    query,
    setQuery,
    city,
    setCity,
    searchMode,
    setSearchMode,
    handleSearchModeChange,
    areaQuery,
    setAreaQuery,
    handleAreaQueryChange,
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
    hasSearched,
    selectedHotelId,
    searchIntentId,
    setSelectedHotelId,
    selectHotel,
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
