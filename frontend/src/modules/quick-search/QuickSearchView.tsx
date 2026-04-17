"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { createPortal } from "react-dom";

import { apiFetch, apiFetchWithStatus } from "@/modules/shared/api";
import { getAirportMeta } from "@/modules/shared/airports";
import { getQuickSearchCopy } from "@/modules/shared/quickSearchCopy";
import { useFtueHint } from "@/lib/ftue";
import { trackUxEvent } from "@/lib/uxTracking";
import { formatRelativeTime } from "@/modules/shared/format";
import { trackEvent } from "@/modules/shared/analytics";
import { formatCurrency, formatNumber } from "@/modules/shared/format";
import { buildDateRange } from "@/modules/quick-search/utils";
import { buildCriteriaSignature, parseNumericInput } from "@/modules/quick-search/searchCriteria";
import {
  clampQuickSearchFlexDays,
  formatQuickSearchFlexSummary,
  getQuickSearchFlexPreset,
} from "@/modules/quick-search/flexibility";
const QuickSearchFiltersDrawer = dynamic(() =>
  import("@/modules/quick-search/components/QuickSearchFiltersDrawer").then((m) => m.QuickSearchFiltersDrawer),
);
const QuickSearchLoadingProgress = dynamic(() =>
  import("@/modules/quick-search/components/QuickSearchLoadingProgress").then((m) => m.QuickSearchLoadingProgress),
  { ssr: false },
);
const QuickSearchResultsList = dynamic(() =>
  import("@/modules/quick-search/components/QuickSearchResultsList").then((m) => m.QuickSearchResultsList),
  { ssr: false },
);
const QuickSearchSearchForm = dynamic(() =>
  import("@/modules/quick-search/components/QuickSearchSearchForm").then((m) => m.QuickSearchSearchForm),
);
const QuickSearchStatePanels = dynamic(() =>
  import("@/modules/quick-search/components/QuickSearchStatePanels").then((m) => m.QuickSearchStatePanels),
);
import { buildQuickSearchCanonicalPayload, prepareQuickSearchRequest } from "@/modules/quick-search/api/buildQuickSearchRequest";
import { QuickSearchDatePicker } from "@/modules/quick-search/components/QuickSearchDatePicker";
import { QuickSearchResultsWorkspace } from "@/modules/quick-search/components/QuickSearchResultsWorkspace";
import {
  AirportIataEntry,
  CountryAirports,
  DeepLinkResponse,
  Pref,
  QuickSearchAutocompleteField,
  QuickSearchExplainTag,
  QuickSearchField,
  QuickSearchFieldErrors,
  QuickSearchLoadingPhase,
  QuickSearchLoadingSubcheckStatus,
  QuickSearchMode,
  QuickSearchTagTone,
  QuickSearchTripType,
  RegionPref,
  SearchResult,
  SearchResponse,
  SearchResponseRaw,
  WeatherDay,
  WeatherReport,
  SummaryHighlightKey,
  ZeroResultRelaxAction,
} from "@/modules/quick-search/types";
import { normalizeQuickSearchResponse } from "@/modules/quick-search/responseNormalizer";
import { useQuickSearchMainState } from "@/modules/quick-search/state/useQuickSearchController";
import { useQuickSearchLoadingFlow } from "@/modules/quick-search/state/useQuickSearchLoadingFlow";
import { useQuickSearchScreenState } from "@/modules/quick-search/state/useQuickSearchScreenState";
import airportsIata from "@/data/airports_iata.min.json";

const RELAX_HIGHLIGHT_BY_ACTION: Record<ZeroResultRelaxAction, Exclude<SummaryHighlightKey, null>> = {
  disable_strict: "strict",
  increase_duration: "duration",
  open_radius_150: "radius",
  clear_exclusions: "exclusions",
};

const IATA_TO_MAC: Record<string, string> = {
  BRU: "BRL",
};
const EMPTY_SEARCH_VALIDATION_MESSAGE = "Please enter a search";

type ExecutedCriteriaSnapshot = {
  route: string;
  dateLabel: string;
  paxLabel: string;
};

const AIRPORTS = airportsIata as Array<{ 
  iata: string;
  name: string;
  municipality: string;
  country_code: string;
  iso_region: string;
  type: string;
}>;

const airportsByCountry = new Map<string, typeof AIRPORTS>();
const airportsByIata = new Map<string, (typeof AIRPORTS)[number]>();

for (const a of AIRPORTS) {
  airportsByIata.set(a.iata, a);
  const key = a.country_code || "";
  const list = airportsByCountry.get(key) || [];
  list.push(a);
  airportsByCountry.set(key, list);
}

function buildAirportSuggestions(value: string, limit = 6) {
  const q = value.trim().toLowerCase();
  if (!q) return [];
  const out: Array<{ iata: string; name: string }> = [];
  const seen = new Set<string>();
  for (const airport of AIRPORTS) {
    if (out.length >= limit) break;
    if (airport.iata.toLowerCase().startsWith(q)) {
      out.push({
        iata: airport.iata,
        name: airport.municipality || airport.name,
      });
      seen.add(airport.iata);
    }
  }
  if (out.length < limit) {
    for (const airport of AIRPORTS) {
      if (out.length >= limit) break;
      if (seen.has(airport.iata)) continue;
      const hay = `${airport.name} ${airport.municipality}`.toLowerCase();
      if (hay.includes(q)) {
        out.push({
          iata: airport.iata,
          name: airport.municipality || airport.name,
        });
        seen.add(airport.iata);
      }
    }
  }
  return out;
}

export function QuickSearchView({ mode = "quick-search" }: { mode?: QuickSearchMode }) {
  const router = useRouter();
  const [executedCriteria, setExecutedCriteria] = useState<ExecutedCriteriaSnapshot | null>(null);
  // signature of the last successfully executed criteria (used to detect pending changes)
  const [appliedCriteriaSignature, setAppliedCriteriaSignature] = useState<string | null>(null);
  const initialOrigin = mode === "recommendations" ? "" : "MAD";
  const initialDestination = mode === "recommendations" ? "" : "DUB";
  const {
    origin,
    setOrigin,
    destination,
    setDestination,
    travelDate,
    setTravelDate,
    returnDate,
    setReturnDate,
    isReturn,
    setIsReturn,
    adults,
    setAdults,
    results,
    setResults,
    message,
    setMessage,
    messageType,
    setMessageType,
    hasSearched,
    setHasSearched,
    isLoading,
    setIsLoading,
    weatherOrigin,
    setWeatherOrigin,
    weatherDestination,
    setWeatherDestination,
    weatherMessage,
    setWeatherMessage,
    filtersNotice,
    setFiltersNotice,
    filtersMeta,
    setFiltersMeta,
    searchMeta,
    setSearchMeta,
    jobId,
    setJobId,
    searchState,
    setSearchState,
    searchError,
    setSearchError,
    rateLimitSeconds,
    setRateLimitSeconds,
    activePicker,
    setActivePicker,
    airportSearch,
    setAirportSearch,
    recentAirports,
    setRecentAirports,
    originCountryOnly,
    setOriginCountryOnly,
    destinationCountryOnly,
    setDestinationCountryOnly,
    originSelectedCountryCode,
    setOriginSelectedCountryCode,
    destinationSelectedCountryCode,
    setDestinationSelectedCountryCode,
    isEditing,
    setIsEditing,
    routePulse,
    setRoutePulse,
    departAfter,
    setDepartAfter,
    departBefore,
    setDepartBefore,
    bufferMin,
    setBufferMin,
    includeStops,
    setIncludeStops,
    maxStops,
    setMaxStops,
    radiusKm,
    setRadiusKm,
    includeNearbyOrigins,
    setIncludeNearbyOrigins,
    includeNearbyDestinations,
    setIncludeNearbyDestinations,
    excludeOrigins,
    setExcludeOrigins,
    excludeDestinations,
    setExcludeDestinations,
    excludeOriginInput,
    setExcludeOriginInput,
    excludeDestinationInput,
    setExcludeDestinationInput,
    strictFilters,
    setStrictFilters,
    daysBefore,
    setDaysBefore,
    daysAfter,
    setDaysAfter,
    applyFlexReturn,
    setApplyFlexReturn,
    priceMin,
    setPriceMin,
    priceMax,
    setPriceMax,
    durationMax,
    setDurationMax,
    riskFilter,
    setRiskFilter,
    sortBy,
    setSortBy,
    isDegraded,
    setIsDegraded,
    compactView,
    setCompactView,
    showHighRisk,
    setShowHighRisk,
    expandedRows,
    setExpandedRows,
    selectedResultId,
    setSelectedResultId,
    pref,
    setPref,
    regionPref,
    setRegionPref,
    prefBadge,
    setPrefBadge,
    deepLink,
    setDeepLink,
    deepLinkError,
    setDeepLinkError,
    copyModalOpen,
    setCopyModalOpen,
    copyModalPayload,
    setCopyModalPayload,
    toast,
    setToast,
    summaryHighlightKey,
    setSummaryHighlightKey,
    originTouched,
    setOriginTouched,
    destinationTouched,
    setDestinationTouched,
    dateTouched,
    setDateTouched,
    fieldErrors,
    setFieldErrors,
    activeAutocompleteField,
    setActiveAutocompleteField,
    activeAutocompleteIndex,
    setActiveAutocompleteIndex,
    isFiltersOpen,
    setIsFiltersOpen,
    isExplainOpen,
    setIsExplainOpen,
    openRowMenuId,
    setOpenRowMenuId,
    targetProgress,
    setTargetProgress,
    displayProgress,
    setDisplayProgress,
    loadingPhase,
    setLoadingPhase,
    showBoarding,
    setShowBoarding,
    loadingVisualHold,
    setLoadingVisualHold,
    showLoader,
    setShowLoader,
    prefersReducedMotion,
    setPrefersReducedMotion,
    isMobileViewport,
    setIsMobileViewport,
    warningsExpanded,
    setWarningsExpanded,
    criticalWarningsExpanded,
    setCriticalWarningsExpanded,
    emptyCausesExpanded,
    setEmptyCausesExpanded,
    infoExpanded,
    setInfoExpanded,
    selectedCountry,
    setSelectedCountry,
    countrySelectionTouched,
    setCountrySelectionTouched,
    airportSelectionTouched,
    setAirportSelectionTouched,
    blurTimer,
    autocompleteBlurTimer,
    zeroResultsTracked,
    idleStateTracked,
    resultsToolbarRef,
    formRef,
    filtersToggleRef,
    filtersCloseRef,
    explainPopoverRef,
    explainTriggerRef,
    relaxUndoRef,
    lastPickerTriggerRef,
    airportSearchInputRef,
    rowMenuTriggerRefs,
    tripTypeIncompleteTrackedRef,
    sourcesShownKeyRef,
    freshnessShownKeyRef,
    headrowRemovedTrackedRef,
    requestIdRef,
    activeLoadingRequestRef,
    prevSearchStateRef,
    progressRafRef,
    animFromRef,
    animToRef,
    animStartTsRef,
    animDurationMsRef,
    lastTargetRef,
    isAnimatingRef,
    displayProgressRef,
    commitRafRef,
    boardingThresholdTimerRef,
    takeoffHoldTimerRef,
    loadingStartRef,
    hideTimeoutRef,
    debugEpochRef,
    debugLastTickLogTsRef,
  } = useQuickSearchMainState(initialOrigin, initialDestination);
  const normalizedRadiusKm = Math.min(500, Math.max(10, Number.isFinite(radiusKm) ? radiusKm : 150));

  const debugLog = useCallback((message: string) => {
    if (process.env.NODE_ENV === "production" || typeof window === "undefined") return;
    const now = typeof performance !== "undefined" ? performance.now() : Date.now();
    if (debugEpochRef.current === null) {
      debugEpochRef.current = now;
    }
    const ts = Math.max(0, Math.round(now - debugEpochRef.current));
    // eslint-disable-next-line no-console
    console.debug(`[qs] ${message} ts=${ts}ms`);
  }, [debugEpochRef]);

  useEffect(() => {
    setRoutePulse(true);
    const timeout = window.setTimeout(() => setRoutePulse(false), 140);
    return () => window.clearTimeout(timeout);
  }, [origin, destination, setRoutePulse]);

  useQuickSearchLoadingFlow({
    searchState,
    showLoader,
    loadingVisualHold,
    targetProgress,
    displayProgress,
    prefersReducedMotion,
    setShowLoader,
    setShowBoarding,
    setLoadingVisualHold,
    setDisplayProgress,
    setLoadingPhase,
    setTargetProgress,
    activeLoadingRequestRef,
    prevSearchStateRef,
    requestIdRef,
    progressRafRef,
    animFromRef,
    animToRef,
    animStartTsRef,
    animDurationMsRef,
    lastTargetRef,
    isAnimatingRef,
    displayProgressRef,
    commitRafRef,
    boardingThresholdTimerRef,
    takeoffHoldTimerRef,
    loadingStartRef,
    hideTimeoutRef,
    debugLastTickLogTsRef,
    debugLog,
  });

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setPrefersReducedMotion(media.matches);
    apply();
    if (media.addEventListener) {
      media.addEventListener("change", apply);
      return () => media.removeEventListener("change", apply);
    }
    media.addListener(apply);
    return () => media.removeListener(apply);
  }, [setPrefersReducedMotion]);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const media = window.matchMedia("(max-width: 900px)");
    const apply = () => setIsMobileViewport(media.matches);
    apply();
    if (media.addEventListener) {
      media.addEventListener("change", apply);
      return () => media.removeEventListener("change", apply);
    }
    media.addListener(apply);
    return () => media.removeListener(apply);
  }, [setIsMobileViewport]);


  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = window.localStorage.getItem("viru_recent_airports");
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        setRecentAirports(parsed.filter((item) => typeof item === "string"));
      }
    } catch {
      setRecentAirports([]);
    }
  }, [setRecentAirports]);

  useEffect(() => {
    if (rateLimitSeconds <= 0) return;
    const timer = window.setInterval(() => {
      setRateLimitSeconds((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [rateLimitSeconds, setRateLimitSeconds]);

  useEffect(() => {
    if (searchState === "empty") {
      if (!zeroResultsTracked.current) {
        trackEvent("quicksearch_zero_results_shown", {
          strict_filters: strictFilters,
          include_stops: includeStops,
          max_stops: includeStops ? maxStops : 0,
          duration_max: durationMax ? Number(durationMax) : null,
          depart_after: departAfter || null,
          depart_before: departBefore || null,
          radius_km: normalizedRadiusKm,
          exclude_origins_count: excludeOrigins.length,
          exclude_destinations_count: excludeDestinations.length,
        });
        trackEvent("quicksearch_empty_shown", {
          strict_filters: strictFilters,
          include_stops: includeStops,
          radius_km: normalizedRadiusKm,
        });
        zeroResultsTracked.current = true;
      }
      return;
    }
    zeroResultsTracked.current = false;
  }, [
    searchState,
    strictFilters,
    includeStops,
    maxStops,
    durationMax,
    departAfter,
    departBefore,
    includeNearbyOrigins,
    includeNearbyDestinations,
    normalizedRadiusKm,
    excludeOrigins.length,
    excludeDestinations.length,
    zeroResultsTracked,
  ]);

  useEffect(() => {
    if (searchState === "idle") {
      if (!idleStateTracked.current) {
        trackEvent("quicksearch_idle_shown", { mode });
        idleStateTracked.current = true;
      }
      return;
    }
    idleStateTracked.current = false;
  }, [searchState, mode, idleStateTracked]);

  useEffect(() => {
    if (!headrowRemovedTrackedRef.current) {
      trackEvent("quicksearch_results_headrow_removed", { mode });
      headrowRemovedTrackedRef.current = true;
    }
  }, [mode, headrowRemovedTrackedRef]);

  useEffect(() => {
    const derivedTripType = getTripTypeLabel(isReturn, returnDate);
    if (derivedTripType === "round_trip_incomplete") {
      if (!tripTypeIncompleteTrackedRef.current) {
        trackEvent("quicksearch_triptype_incomplete_shown", { is_return: isReturn, has_return_date: Boolean(returnDate) });
        tripTypeIncompleteTrackedRef.current = true;
      }
      return;
    }
    tripTypeIncompleteTrackedRef.current = false;
  }, [isReturn, returnDate, tripTypeIncompleteTrackedRef]);

  useEffect(() => {
    return () => {
      if (autocompleteBlurTimer.current) {
        window.clearTimeout(autocompleteBlurTimer.current);
      }
    };
  }, [autocompleteBlurTimer]);

  useEffect(() => {
    if (!hasSearched) return;
    if (!resultsToolbarRef.current) return;
    resultsToolbarRef.current.focus();
  }, [hasSearched, resultsToolbarRef]);

  useEffect(() => {
    if (!summaryHighlightKey) return;
    const timer = window.setTimeout(() => setSummaryHighlightKey(null), 800);
    return () => window.clearTimeout(timer);
  }, [summaryHighlightKey, setSummaryHighlightKey]);

  useEffect(() => {
    if (filtersNotice.length === 0 && warningsExpanded) {
      setWarningsExpanded(false);
    }
  }, [filtersNotice.length, warningsExpanded, setWarningsExpanded]);

  useEffect(() => {
    if (filtersNotice.length === 0 && criticalWarningsExpanded) {
      setCriticalWarningsExpanded(false);
    }
  }, [filtersNotice.length, criticalWarningsExpanded, setCriticalWarningsExpanded]);

  useEffect(() => {
    if (searchState !== "empty" && emptyCausesExpanded) {
      setEmptyCausesExpanded(false);
    }
  }, [searchState, emptyCausesExpanded, setEmptyCausesExpanded]);

  const closeExplainPopover = useCallback(() => {
    setIsExplainOpen(false);
    if (explainPopoverRef.current) {
      explainPopoverRef.current.open = false;
    }
    if (typeof window !== "undefined") {
      window.requestAnimationFrame(() => {
        explainTriggerRef.current?.focus();
      });
    }
  }, [explainPopoverRef, explainTriggerRef, setIsExplainOpen]);

  const closeFiltersDrawer = useCallback(() => {
    setIsFiltersOpen(false);
    if (typeof window !== "undefined") {
      window.requestAnimationFrame(() => {
        filtersToggleRef.current?.focus();
      });
    }
  }, [filtersToggleRef, setIsFiltersOpen]);

  const closeRowMenu = useCallback((targetId?: string | null) => {
    setOpenRowMenuId((prev) => {
      const idToClose = targetId ?? prev;
      if (!idToClose) return prev;
      if (typeof window !== "undefined") {
        window.requestAnimationFrame(() => {
          rowMenuTriggerRefs.current[idToClose]?.focus();
        });
      }
      return prev === idToClose ? null : prev;
    });
  }, [rowMenuTriggerRefs, setOpenRowMenuId]);

  useEffect(() => {
    if (!isFiltersOpen) return;
    if (typeof window === "undefined") return;
    window.requestAnimationFrame(() => {
      filtersCloseRef.current?.focus();
    });
  }, [isFiltersOpen, filtersCloseRef]);

  useEffect(() => {
    if (!isFiltersOpen) return;
    if (typeof window === "undefined") return;

    const body = document.body;
    const docEl = document.documentElement;
    const scrollY = window.scrollY;

    const prevBodyOverflow = body.style.overflow;
    const prevBodyPosition = body.style.position;
    const prevBodyTop = body.style.top;
    const prevBodyWidth = body.style.width;
    const prevBodyOverscroll = body.style.overscrollBehavior;
    const prevDocOverscroll = docEl.style.overscrollBehavior;

    body.style.overflow = "hidden";
    body.style.position = "fixed";
    body.style.top = `-${scrollY}px`;
    body.style.width = "100%";
    body.style.overscrollBehavior = "contain";
    docEl.style.overscrollBehavior = "contain";

    return () => {
      body.style.overflow = prevBodyOverflow;
      body.style.position = prevBodyPosition;
      body.style.top = prevBodyTop;
      body.style.width = prevBodyWidth;
      body.style.overscrollBehavior = prevBodyOverscroll;
      docEl.style.overscrollBehavior = prevDocOverscroll;
      window.scrollTo(0, scrollY);
    };
  }, [isFiltersOpen]);

  useEffect(() => {
    if (!activePicker) return;
    if (typeof window === "undefined") return;
    window.requestAnimationFrame(() => {
      airportSearchInputRef.current?.focus();
    });
  }, [activePicker, airportSearchInputRef]);

  const copy = useMemo(
    () => getQuickSearchCopy(regionPref?.language ?? pref?.language),
    [regionPref?.language, pref?.language],
  );
  const { locale, localeTag, t, tWarn } = copy;
  const [flexCustomPanelOpen, setFlexCustomPanelOpen] = useState(false);
  const isRecommendations = mode === "recommendations";
  const pageTitle = isRecommendations ? t("titleRecommendations") : t("title");
  const pageSubtitle = isRecommendations ? t("subtitleRecommendations") : t("subtitle");
  const pageWorkspaceHint = isRecommendations ? t("workspaceHintRecommendations") : t("workspaceHint");
  const formatScore = (value: number) => formatNumber(value, { maximumFractionDigits: 2 }, localeTag);
  const formatMoney = (value: number, currency?: string) => {
    const code = currency ?? searchMeta?.currency ?? "EUR";
    return formatCurrency(value, code, localeTag);
  };
  const countryDisplayNames = useMemo(() => {
    try {
      return new Intl.DisplayNames([localeTag], { type: "region" });
    } catch {
      return null;
    }
  }, [localeTag]);
  const countryOptions = useMemo(() => {
    const list = Array.from(airportsByCountry.entries()).map(([code, airports]) => ({
      code,
      name: countryDisplayNames?.of(code) || code,
      airports,
    }));
    list.sort((a, b) => a.name.localeCompare(b.name));
    return list;
  }, [countryDisplayNames]);
  const countryByCode = useMemo(() => {
    return new Map(countryOptions.map((country) => [country.code, country]));
  }, [countryOptions]);

  useEffect(() => {
    if (selectedCountry || countryOptions.length === 0) return;
    const mad = airportsByIata.get("MAD");
    const next = (mad && countryByCode.get(mad.country_code)) || countryOptions[0] || null;
    setSelectedCountry(next);
  }, [selectedCountry, countryOptions, countryByCode, setSelectedCountry]);

  useEffect(() => {
    if (!selectedCountry) return;
    const next = countryByCode.get(selectedCountry.code);
    if (next && next !== selectedCountry) {
      setSelectedCountry(next);
    }
  }, [countryByCode, selectedCountry, setSelectedCountry]);

  useEffect(() => {
    apiFetch<Pref>("/preferences/search")
      .then((data) => {
        setPref(data);
        setRadiusKm((prev) => (
          Number.isFinite(data.default_radius_km) ? data.default_radius_km : prev
        ));
        setIncludeStops(Boolean(data.include_stops_default));
        setDepartAfter((prev) => data.avoid_departure_before ?? prev);
        setPrefBadge(true);
      })
      .catch(() => {
        setPref(null);
      });
  }, [setDepartAfter, setIncludeStops, setPref, setPrefBadge, setRadiusKm]);

  useEffect(() => {
    apiFetch<RegionPref>("/preferences/region")
      .then(setRegionPref)
      .catch(() => setRegionPref(null));
  }, [setRegionPref]);

  const localRyanairUrl = useMemo(() => {
    if (!travelDate || originCountryOnly || destinationCountryOnly) return "";
    const originMac = IATA_TO_MAC[origin] || "";
    const destinationMac = IATA_TO_MAC[destination] || "";
    const params = new URLSearchParams({
      adults: String(adults),
      teens: "0",
      children: "0",
      infants: "0",
      dateOut: travelDate,
      dateIn: isReturn ? returnDate : "",
      isConnectedFlight: "false",
      discount: "0",
      promoCode: "",
      isReturn: isReturn ? "true" : "false",
      originIata: origin,
      destinationIata: destination,
      originMac,
      destinationMac,
      tpAdults: String(adults),
      tpTeens: "0",
      tpChildren: "0",
      tpInfants: "0",
      tpStartDate: travelDate,
      tpEndDate: isReturn ? returnDate : "",
      tpDiscount: "0",
      tpPromoCode: "",
      tpOriginIata: origin,
      tpDestinationIata: destination,
      tpOriginMac: originMac,
      tpDestinationMac: destinationMac,
    });
    return `https://www.ryanair.com/es/es/trip/flights/select?${params.toString()}`;
  }, [adults, destination, destinationCountryOnly, isReturn, origin, originCountryOnly, returnDate, travelDate]);

  useEffect(() => {
    if (!origin || !destination || !travelDate || originCountryOnly || destinationCountryOnly) {
      setDeepLink(null);
      setDeepLinkError("");
      return;
    }
    if (isReturn && !returnDate) {
      setDeepLink(null);
      return;
    }
    const controller = new AbortController();
    const params = new URLSearchParams();
    params.set("origin_iata", origin);
    params.set("destination_iata", destination);
    params.set("date_out", travelDate);
    if (isReturn && returnDate) {
      params.set("date_in", returnDate);
    }
    params.set("adults", String(adults));
    params.set("teens", "0");
    params.set("children", "0");
    params.set("infants", "0");
    params.set("locale", locale === "en" ? "en-us" : "es-es");
    apiFetch<DeepLinkResponse>(`/search/deeplink?${params.toString()}`, {
      method: "GET",
      signal: controller.signal,
    })
      .then((data) => {
        setDeepLink(data);
        setDeepLinkError("");
      })
      .catch(() => {
        if (controller.signal.aborted) {
          return;
        }
        setDeepLink(null);
        setDeepLinkError(t("deepLinkError"));
      });
    return () => controller.abort();
  }, [origin, destination, travelDate, returnDate, isReturn, adults, locale, t, originCountryOnly, destinationCountryOnly, setDeepLink, setDeepLinkError]);

  const findCountryByIataLocal = useCallback((iata: string): CountryAirports | null => {
    const code = iata.trim().toUpperCase();
    const entry = airportsByIata.get(code);
    if (!entry) return null;
    return countryByCode.get(entry.country_code) || null;
  }, [countryByCode]);

  function weatherLabel(code: number): string {
    if (code === 0) return t("weatherClear");
    if (code === 1 || code === 2) return t("weatherMostlyClear");
    if (code === 3) return t("weatherCloudy");
    if (code >= 45 && code <= 48) return t("weatherFog");
    if (code >= 51 && code <= 57) return t("weatherDrizzle");
    if (code >= 61 && code <= 67) return t("weatherRain");
    if (code >= 71 && code <= 77) return t("weatherSnow");
    if (code >= 80 && code <= 82) return t("weatherShowers");
    if (code >= 95) return t("weatherStorm");
    return t("weatherVariable");
  }

  type WeatherFetchErrorCode = "out_of_range" | "provider_error";

  class WeatherFetchError extends Error {
    code: WeatherFetchErrorCode;

    constructor(code: WeatherFetchErrorCode, message: string) {
      super(message);
      this.code = code;
    }
  }

  function isWeatherRangeSupported(start: string, end: string): boolean {
    const startDate = new Date(`${start}T00:00:00Z`);
    const endDate = new Date(`${end}T00:00:00Z`);
    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return false;

    const today = new Date();
    const todayUtc = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
    const maxDate = new Date(todayUtc);
    maxDate.setUTCDate(maxDate.getUTCDate() + 14);

    return startDate >= todayUtc && endDate <= maxDate;
  }

  async function fetchWeather(iata: string, start: string, end: string): Promise<WeatherReport | null> {
    const meta = getAirportMeta(iata);
    if (!meta) return null;

    if (!isWeatherRangeSupported(start, end)) {
      throw new WeatherFetchError("out_of_range", "weather_out_of_range");
    }

    const params = new URLSearchParams({
      latitude: String(meta.latitude),
      longitude: String(meta.longitude),
      daily: "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
      timezone: "auto",
      start_date: start,
      end_date: end,
    });
    const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params.toString()}`);
    if (!res.ok) {
      const reasonRaw = await res.text().catch(() => "");
      const isRange400 = res.status === 400 && reasonRaw.toLowerCase().includes("out of allowed range");
      if (isRange400) {
        throw new WeatherFetchError("out_of_range", "weather_out_of_range");
      }
      throw new WeatherFetchError("provider_error", `weather_provider_${res.status}`);
    }
    const data = await res.json();
    const times: string[] = data?.daily?.time || [];
    const maxTemps: number[] = data?.daily?.temperature_2m_max || [];
    const minTemps: number[] = data?.daily?.temperature_2m_min || [];
    const precip: number[] = data?.daily?.precipitation_probability_max || [];
    const codes: number[] = data?.daily?.weathercode || [];
    const days: WeatherDay[] = times.map((time: string, idx: number) => ({
      date: time,
      tempMax: Number(maxTemps[idx] ?? 0),
      tempMin: Number(minTemps[idx] ?? 0),
      precipProb: Number.isFinite(precip[idx]) ? precip[idx] : null,
      description: weatherLabel(Number(codes[idx] ?? 0)),
    }));
    return {
      iata: meta.iata,
      name: meta.name,
      city: meta.city,
      country: meta.country,
      days,
    };
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const startedAt = typeof performance !== "undefined" ? performance.now() : Date.now();
    requestIdRef.current += 1;
    const requestId = requestIdRef.current;
    activeLoadingRequestRef.current = requestId;
    const isCurrentRequest = () => requestId === requestIdRef.current;
    const setProgress = (phase: QuickSearchLoadingPhase, progress: number) => {
      if (!isCurrentRequest()) return;
      debugLog(`target -> ${progress} (${phase})`);
      setLoadingPhase(phase);
      setTargetProgress(progress);
    };
    setMessage("");
    setMessageType("error");
    setSearchError(null);
    setFieldErrors({});

    const nextFieldErrors: QuickSearchFieldErrors = {};
    const originHasValue = Boolean(origin.trim()) || Boolean(originCountryOnly);
    const destinationHasValue = Boolean(destination.trim()) || Boolean(destinationCountryOnly);
    const parsedPriceMin = parseNumericInput(priceMin, { min: 0 });
    const parsedPriceMax = parseNumericInput(priceMax, { min: 0 });
    const parsedDurationMax = parseNumericInput(durationMax, { min: 1 });
    const parsedBufferMin = parseNumericInput(bufferMin, { min: 0 });

    if (priceMin.trim() && parsedPriceMin === null) nextFieldErrors.price_min = t("errorText");
    if (priceMax.trim() && parsedPriceMax === null) nextFieldErrors.price_max = t("errorText");
    if (durationMax.trim() && parsedDurationMax === null) nextFieldErrors.duration_max = t("errorText");
    if (bufferMin.trim() && parsedBufferMin === null) nextFieldErrors.buffer_min = t("errorText");
    if (parsedPriceMin !== null && parsedPriceMax !== null && parsedPriceMin > parsedPriceMax) {
      nextFieldErrors.price_max = t("errorText");
    }

    if (!originHasValue && !destinationHasValue) {
      onEmptySearchValidation();
      return;
    }
    if (!travelDate) {
      setSearchState("error");
      setSearchError(t("errorText"));
      setDateTouched(true);
      setFieldErrors({ travel_date: t("selectOutbound") });
      return;
    }
    if (!originValid || !destinationValid) {
      setSearchState("error");
      setSearchError(t("errorText"));
      if (!originValid) setOriginTouched(true);
      if (!destinationValid) setDestinationTouched(true);
      setFieldErrors({
        origin_iata: !originValid ? t("iataInvalid") : undefined,
        destination_iata: !destinationValid ? t("iataInvalid") : undefined,
      });
      return;
    }
    if (isReturn && !returnDate) {
      setSearchState("error");
      setSearchError(t("selectReturn"));
      return;
    }
    if (isReturn && returnDate && returnDate < travelDate) {
      setSearchState("error");
      setSearchError(t("returnBefore"));
      return;
    }
    if (Object.keys(nextFieldErrors).length > 0) {
      setSearchState("error");
      setSearchError(t("errorText"));
      setFieldErrors(nextFieldErrors);
      return;
    }

    setAppliedCriteriaSignature(currentCriteriaSignature);
    setWeatherMessage("");
    setWeatherOrigin(null);
    setWeatherDestination(null);
    setFiltersNotice([]);
    setFiltersMeta(null);
    setSearchMeta(null);
    setJobId(null);
    setIsDegraded(false);
    setSearchState("loading");
    setLoadingVisualHold(false);
    setDisplayProgress(0);
    setProgress("requesting", 30);
    const nextExcludeOrigins = [...excludeOrigins];
    const nextExcludeDestinations = [...excludeDestinations];
    parseIataList(excludeOriginInput).forEach((value) => {
      if (!nextExcludeOrigins.includes(value)) nextExcludeOrigins.push(value);
    });
    parseIataList(excludeDestinationInput).forEach((value) => {
      if (!nextExcludeDestinations.includes(value)) nextExcludeDestinations.push(value);
    });
    if (excludeOriginInput) setExcludeOriginInput("");
    if (excludeDestinationInput) setExcludeDestinationInput("");
    setExcludeOrigins(nextExcludeOrigins);
    setExcludeDestinations(nextExcludeDestinations);
    const range = buildDateRange(travelDate, isReturn ? returnDate : travelDate);
    const payload = {
      origin_iata: originCountryOnly ? originCountryOnly.airports.map((item) => item.iata) : origin,
      destination_iata: destinationCountryOnly ? destinationCountryOnly.airports.map((item) => item.iata) : destination,
      travel_date: travelDate,
      date: travelDate,
      flex_days_before: daysBefore,
      flex_days_after: daysAfter,
      radius_km: normalizedRadiusKm,
      include_stops: includeStops,
      include_nearby_origins: includeNearbyOrigins,
      include_nearby_destinations: includeNearbyDestinations,
      depart_after: departAfter || undefined,
      depart_before: departBefore || undefined,
      price_min: parsedPriceMin ?? undefined,
      price_max: parsedPriceMax ?? undefined,
      duration_max_min: parsedDurationMax ?? undefined,
      buffer_min: parsedBufferMin ?? undefined,
      max_stops: includeStops ? maxStops : 0,
      exclude_origins: nextExcludeOrigins,
      exclude_destinations: nextExcludeDestinations,
      strict_filters: strictFilters,
      soft_filters_weight: 0.6,
    };
    const nextExecutedCriteria: ExecutedCriteriaSnapshot = {
      route: `${originCountryOnly ? originCountryOnly.name : origin} → ${destinationCountryOnly ? destinationCountryOnly.name : destination}`,
      dateLabel: isReturn && returnDate ? `${travelDate} → ${returnDate}` : travelDate,
      paxLabel: `${adults} ${adults === 1 ? t("summaryPassengersSingular") : t("summaryPassengersPlural")}`,
    };
    trackEvent("quicksearch_search_submitted", {
      has_origin_country_scope: Boolean(originCountryOnly),
      has_destination_country_scope: Boolean(destinationCountryOnly),
      include_stops: includeStops,
      strict_filters: strictFilters,
      radius_km: normalizedRadiusKm,
      flex_days_before: daysBefore,
      flex_days_after: daysAfter,
    });
    const preparedRequest = prepareQuickSearchRequest(payload);
    if (preparedRequest.issues.length > 0) {
      setSearchError(t("errorText"));
      setSearchState("idle");
      setIsLoading(false);
      trackEvent("quicksearch_contract_blocked", {
        issues: preparedRequest.issues.map((issue) => issue.code).join(","),
      });
      return;
    }
    const canonicalPayload = buildQuickSearchCanonicalPayload(preparedRequest.params);
    try {
      if (!isCurrentRequest()) return;
      setIsLoading(true);
      const originWeatherIata = originCountryOnly ? "" : origin;
      const destinationWeatherIata = destinationCountryOnly ? "" : destination;
      const weatherRangeSupported = range.length > 0 && isWeatherRangeSupported(range[0], range[range.length - 1]);
      if (!weatherRangeSupported && (originWeatherIata || destinationWeatherIata)) {
        setWeatherMessage(t("weatherUnavailableRange"));
      }

      const originWeatherPromise = weatherRangeSupported && originWeatherIata
        ? fetchWeather(originWeatherIata, range[0], range[range.length - 1])
        : Promise.resolve(null);
      const destinationWeatherPromise = weatherRangeSupported && destinationWeatherIata
        ? fetchWeather(destinationWeatherIata, range[0], range[range.length - 1])
        : Promise.resolve(null);
      void Promise.allSettled([originWeatherPromise, destinationWeatherPromise]).then(([originWeather, destinationWeather]) => {
        if (!isCurrentRequest()) return;
        if (originWeather.status === "fulfilled") {
          setWeatherOrigin(originWeather.value);
        }
        if (destinationWeather.status === "fulfilled") {
          setWeatherDestination(destinationWeather.value);
        }

        if (originWeather.status === "rejected" || destinationWeather.status === "rejected") {
          const reasons = [originWeather, destinationWeather]
            .filter((item): item is PromiseRejectedResult => item.status === "rejected")
            .map((item) => item.reason);
          const hasOutOfRange = reasons.some(
            (reason) => reason && typeof reason === "object" && "code" in reason && reason.code === "out_of_range",
          );
          setWeatherMessage(hasOutOfRange ? t("weatherUnavailableRange") : t("weatherError"));
        }
      });
      const searchResult = await apiFetchWithStatus<SearchResponseRaw>("/search/quick", {
        method: "POST",
        body: JSON.stringify(canonicalPayload),
      });
      if (!isCurrentRequest()) return;
      setProgress("response_parsed", 80);
      if (searchResult.ok) {
          const data: SearchResponse = normalizeQuickSearchResponse(searchResult.data);
          setResults(data.results);
          setExecutedCriteria(nextExecutedCriteria);
          setFiltersMeta(data.filters || null);
          setSearchMeta(data.meta || null);
          setJobId(data.job_id || null);
          setIsDegraded(Boolean(data.meta?.stale_data || data.results.find((item) => item.stale_data)));
          if (data.filters?.warnings && data.filters.warnings.length > 0) {
            setFiltersNotice(data.filters.warnings.map((item) => tWarn(item)));
          }
          setProgress("client_done", 95);
          setHasSearched(true);
          const isEmptyResult = data.results.length === 0;
          setSearchState(isEmptyResult ? "empty" : "success");
          const durationMs = Math.round((typeof performance !== "undefined" ? performance.now() : Date.now()) - startedAt);
          void trackUxEvent("quick_search_executed", { duration_ms: durationMs, result_count: data.results.length });
          if (isEmptyResult) {
            void trackUxEvent("search_empty_results", { duration_ms: durationMs });
          }
        } else {
          const { status, error } = searchResult;
          const validationErrors = parseValidationErrors(error.details);
          if (Object.keys(validationErrors).length > 0) {
            setFieldErrors(validationErrors);
            if (validationErrors.origin_iata) setOriginTouched(true);
            if (validationErrors.destination_iata) setDestinationTouched(true);
            if (validationErrors.travel_date) setDateTouched(true);
          }
          setProgress("client_done", 95);
          if (status === 429) {
            setRateLimitSeconds(error.retry_after_sec ?? 30);
            setSearchState("rate");
            setSearchError(t("rateLimitText"));
          } else {
            if (status === 422) {
              trackEvent("quicksearch_contract_rejected", {
                has_field_errors: Object.keys(validationErrors).length > 0,
                detail: error.message?.slice(0, 120) || "validation_error",
              });
            }
            setSearchState("error");
            setSearchError(Object.keys(validationErrors).length > 0 ? t("errorText") : t("searchFailed"));
          }
          setHasSearched(true);
      }
    } catch (error) {
      if (!isCurrentRequest()) return;
      setProgress("client_done", 95);
      setSearchState("error");
      setSearchError(t("searchFailed"));
      setHasSearched(true);
    } finally {
      if (isCurrentRequest()) {
        setIsLoading(false);
      }
    }
  }

  async function addToWatchlist(result: SearchResult) {
    setMessage("");
    try {
      try {
        const response = await apiFetch<{ watch_id?: string; created_or_existing?: string }>("/search/save-result", {
          method: "POST",
          body: JSON.stringify({
            job_id: jobId,
            result_id: result.result_id ?? null,
            origin_iata: result.origin,
            destination_iata: result.destination,
            travel_date: result.travel_date,
            price_total: result.price_total ?? result.price,
            currency: result.currency,
            duration_total: result.duration_total_min ?? result.duration_total ?? null,
            stop_count: result.stop_count ?? null,
            risk_label: result.risk_label ?? null,
            minutes_buffer: result.minutes_buffer ?? null,
            distance_km_ground: result.distance_km_ground ?? null,
            ranking_score: result.ranking_score ?? null,
            freshness_ts: result.freshness_ts ?? null,
            deeplink_url: result.deeplink_url ?? deeplinkUrl ?? null,
            itinerary_type: result.itinerary_type ?? null,
          }),
        });
        if (response.created_or_existing === "existing") {
          setToast({
            message: t("watchExists"),
            actionLabel: t("viewWatchlist"),
            onAction: () => router.push("/watchlist"),
          });
        } else {
          trackEvent("quicksearch_watchlist_added", {
            origin: result.origin,
            destination: result.destination,
            travel_date: result.travel_date,
            source: result.source,
            risk_label: result.risk_label ?? null,
          });
          setToast({
            message: t("watchAdded"),
            actionLabel: t("viewWatchlist"),
            onAction: () => router.push("/watchlist"),
          });
        }
      } catch {
        await apiFetch("/watchlist", {
          method: "POST",
          body: JSON.stringify({
            origin_iata: result.origin,
            destination_iata: result.destination,
            travel_date_local: result.travel_date,
          }),
        });
        trackEvent("quicksearch_watchlist_added", {
          origin: result.origin,
          destination: result.destination,
          travel_date: result.travel_date,
          source: result.source,
          risk_label: result.risk_label ?? null,
        });
        setToast({
          message: t("watchAdded"),
          actionLabel: t("viewWatchlist"),
          onAction: () => router.push("/watchlist"),
        });
      }
    } catch (error) {
      setMessage(t("watchFailed"));
      setMessageType("error");
    }
  }

  function openPicker(which: "origin" | "destination") {
    const current = which === "origin" ? origin : destination;
    const country = (which === "origin" ? originCountryOnly : destinationCountryOnly)
      || findCountryByIataLocal(current)
      || countryOptions[0]
      || null;
    setSelectedCountry(country);
    setCountrySelectionTouched(false);
    setAirportSelectionTouched(false);
    setAirportSearch("");
    setActivePicker(which);
  }

  const closePickerWithFocusReturn = useCallback(() => {
    setActivePicker(null);
    if (typeof window !== "undefined") {
      window.requestAnimationFrame(() => {
        lastPickerTriggerRef.current?.focus();
      });
    }
  }, [lastPickerTriggerRef, setActivePicker]);

  function clearSelection() {
    if (activePicker === "origin") {
      setOrigin("");
      setOriginCountryOnly(null);
      setOriginSelectedCountryCode(null);
    }
    if (activePicker === "destination") {
      setDestination("");
      setDestinationCountryOnly(null);
      setDestinationSelectedCountryCode(null);
    }
  }

  function selectAirport(iata: string) {
    setAirportSelectionTouched(true);
    const entry = airportsByIata.get(iata.trim().toUpperCase());
    const countryCode = entry ? entry.country_code : null;
    if (activePicker === "origin") {
      setOrigin(iata);
      setOriginCountryOnly(null);
      setOriginSelectedCountryCode(countryCode);
    } else if (activePicker === "destination") {
      setDestination(iata);
      setDestinationCountryOnly(null);
      setDestinationSelectedCountryCode(countryCode);
    }
    if (typeof window !== "undefined") {
      const next = [iata, ...recentAirports.filter((item) => item !== iata)].slice(0, 6);
      setRecentAirports(next);
      window.localStorage.setItem("viru_recent_airports", JSON.stringify(next));
    }
    closePickerWithFocusReturn();
  }

  const selectCountryOnly = useCallback((country: CountryAirports | null) => {
    if (!country) return;
    if (activePicker === "origin") {
      setOrigin("");
      setOriginCountryOnly(country);
      setOriginSelectedCountryCode(null);
    }
    if (activePicker === "destination") {
      setDestination("");
      setDestinationCountryOnly(country);
      setDestinationSelectedCountryCode(null);
    }
    closePickerWithFocusReturn();
  }, [
    activePicker,
    setDestination,
    setDestinationCountryOnly,
    setDestinationSelectedCountryCode,
    setOrigin,
    setOriginCountryOnly,
    setOriginSelectedCountryCode,
    closePickerWithFocusReturn,
  ]);

  const closePicker = useCallback(() => {
    if (activePicker && countrySelectionTouched && !airportSelectionTouched && selectedCountry) {
      selectCountryOnly(selectedCountry);
      return;
    }
    closePickerWithFocusReturn();
  }, [
    activePicker,
    countrySelectionTouched,
    airportSelectionTouched,
    selectedCountry,
    selectCountryOnly,
    closePickerWithFocusReturn,
  ]);

  useEffect(() => {
    if (!activePicker && !isFiltersOpen && !copyModalOpen && !isExplainOpen && !openRowMenuId) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      closePicker();
      closeFiltersDrawer();
      closeExplainPopover();
      setCopyModalOpen(false);
      closeRowMenu();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    activePicker,
    isFiltersOpen,
    copyModalOpen,
    isExplainOpen,
    openRowMenuId,
    closePicker,
    closeFiltersDrawer,
    closeExplainPopover,
    closeRowMenu,
    setCopyModalOpen,
  ]);

  function onFieldFocus() {
    if (blurTimer.current) {
      window.clearTimeout(blurTimer.current);
      blurTimer.current = null;
    }
    setIsEditing(true);
  }

  function onFieldBlur() {
    if (blurTimer.current) {
      window.clearTimeout(blurTimer.current);
    }
    blurTimer.current = window.setTimeout(() => setIsEditing(false), 120);
  }

  function clearAutocompleteBlurTimer() {
    if (!autocompleteBlurTimer.current) return;
    window.clearTimeout(autocompleteBlurTimer.current);
    autocompleteBlurTimer.current = null;
  }

  function onAutocompleteFieldFocus(field: QuickSearchAutocompleteField) {
    clearAutocompleteBlurTimer();
    setActiveAutocompleteField(field);
    setActiveAutocompleteIndex(-1);
  }

  function onAutocompleteFieldBlur() {
    clearAutocompleteBlurTimer();
    autocompleteBlurTimer.current = window.setTimeout(() => {
      setActiveAutocompleteField(null);
      setActiveAutocompleteIndex(-1);
    }, 120);
  }

  function onEmptySearchValidation() {
    const detail = `${EMPTY_SEARCH_VALIDATION_MESSAGE}. Search query is required.`;
    setSearchState("error");
    setSearchError(`${detail} / Por favor, introduce una búsqueda.`);
    setOriginTouched(true);
    setDestinationTouched(true);
    setFieldErrors({
      origin_iata: detail,
      destination_iata: detail,
    });
  }

  function selectAutocompleteSuggestion(field: QuickSearchAutocompleteField, iata: string, submitAfterSelect = false) {
    const entry = airportsByIata.get(iata.trim().toUpperCase());
    const countryCode = entry ? entry.country_code : null;
    if (field === "origin") {
      setOrigin(iata);
      setOriginCountryOnly(null);
      setOriginSelectedCountryCode(countryCode);
      setOriginTouched(true);
      setFieldErrors((prev) => ({ ...prev, origin_iata: undefined }));
    } else {
      setDestination(iata);
      setDestinationCountryOnly(null);
      setDestinationSelectedCountryCode(countryCode);
      setDestinationTouched(true);
      setFieldErrors((prev) => ({ ...prev, destination_iata: undefined }));
    }
    setActiveAutocompleteField(null);
    setActiveAutocompleteIndex(-1);
    if (submitAfterSelect && typeof window !== "undefined") {
      window.requestAnimationFrame(() => formRef.current?.requestSubmit());
    }
  }

  function formatShortDate(value: string): string {
    if (!value) return "";
    const date = new Date(`${value}T00:00:00`);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString(localeTag, { day: "2-digit", month: "short" });
  }

  function setFlexPreset(nextPreset: "exact" | "plus-1" | "plus-2" | "plus-3") {
    if (nextPreset === "exact") {
      setDaysBefore(0);
      setDaysAfter(0);
    } else if (nextPreset === "plus-1") {
      setDaysBefore(1);
      setDaysAfter(1);
    } else if (nextPreset === "plus-2") {
      setDaysBefore(2);
      setDaysAfter(2);
    } else {
      setDaysBefore(3);
      setDaysAfter(3);
    }
    setFlexCustomPanelOpen(false);
  }

  function updateDaysBefore(delta: number) {
    setDaysBefore((prev) => clampQuickSearchFlexDays(prev + delta));
  }

  function updateDaysAfter(delta: number) {
    setDaysAfter((prev) => clampQuickSearchFlexDays(prev + delta));
  }

  function changeAdults(delta: number) {
    setAdults((prev) => Math.min(9, Math.max(1, prev + delta)));
  }

  function applyPreferences() {
    if (!pref) return;
    setRadiusKm(Number.isFinite(pref.default_radius_km) ? pref.default_radius_km : 150);
    setIncludeStops(Boolean(pref.include_stops_default));
    setDepartAfter(pref.avoid_departure_before ?? "07:00");
    setPrefBadge(true);
  }

  const formatRiskLabel = useCallback((label?: string | null) => {
    if (label === "low") return t("riskLow");
    if (label === "medium") return t("riskMedium");
    if (label === "high") return t("riskHigh");
    return label || "";
  }, [t]);

  function getRiskTag(result: SearchResult): QuickSearchExplainTag | null {
    if (!result.risk_label) return null;
    const tone: QuickSearchTagTone = result.risk_label === "high"
      ? "high"
      : result.risk_label === "medium"
        ? "med"
        : "low";
    return {
      key: `risk-${result.risk_label}`,
      label: formatRiskLabel(result.risk_label),
      tone,
    };
  }

  function getItineraryTag(result: SearchResult): QuickSearchExplainTag {
    return {
      key: `itinerary-${result.itinerary_type || "direct"}`,
      label: result.itinerary_type === "self_connect" ? t("itinerarySelfConnect") : t("itineraryDirect"),
      tone: result.itinerary_type === "self_connect" ? "med" : "fresh",
    };
  }

  function getFreshnessTag(result: SearchResult): QuickSearchExplainTag | null {
    if (result.stale_data) {
      return { key: "freshness-stale", label: t("stale"), tone: "stale" };
    }
    if (result.freshness_ts) {
      return {
        key: "freshness-live",
        label: `${t("freshnessLabel")} ${formatFreshness(result.freshness_ts)}`,
        tone: "fresh",
      };
    }
    return null;
  }

  function getResultTags(result: SearchResult, mode: "normal" | "compact" | "expanded"): QuickSearchExplainTag[] {
    const itineraryTag = getItineraryTag(result);
    const riskTag = getRiskTag(result);
    const freshnessTag = getFreshnessTag(result);
    if (mode === "compact") {
      return [riskTag ?? itineraryTag];
    }
    if (mode === "expanded") {
      return [
        itineraryTag,
        riskTag ?? { key: "risk-empty", label: `${t("resultsColRisk")}: --`, tone: "stale" },
        ...(freshnessTag ? [freshnessTag] : []),
      ].filter((tag): tag is QuickSearchExplainTag => Boolean(tag));
    }
    return [itineraryTag, ...(riskTag ? [riskTag] : []), ...(freshnessTag ? [freshnessTag] : [])];
  }

  function parseIataList(raw: string): string[] {
    return raw
      .toUpperCase()
      .split(/[,\s]+/)
      .map((item) => item.trim())
      .filter((item) => item.length === 3);
  }

  function addChip(
    value: string,
    current: string[],
    setCurrent: (next: string[]) => void,
    setInput: (next: string) => void,
  ) {
    const parsed = parseIataList(value);
    if (parsed.length === 0) {
      setInput(value.toUpperCase());
      return;
    }
    const next = [...current];
    parsed.forEach((iata) => {
      if (!next.includes(iata)) next.push(iata);
    });
    setCurrent(next);
    setInput("");
  }

  function removeChip(
    value: string,
    current: string[],
    setCurrent: (next: string[]) => void,
  ) {
    setCurrent(current.filter((item) => item !== value));
  }

  function formatMinutes(value?: number | null) {
    if (!value && value !== 0) return "--";
    return `${value} min`;
  }

  function formatFreshness(value?: string | null) {
    if (!value) return t("freshnessUnknown");
    const ts = new Date(value).getTime();
    if (Number.isNaN(ts)) return value;
    const diff = Math.max(0, Date.now() - ts);
    const mins = Math.round(diff / 60000);
    if (mins < 60) return `${mins} min`;
    const hours = Math.round(mins / 60);
    return `${hours} h`;
  }

  function mapFieldValidationMessage(field: QuickSearchField, message: string): string {
    const normalized = message.toLowerCase();
    if (field === "travel_date") {
      if (normalized.includes("required") || normalized.includes("missing")) return t("selectOutbound");
      return message;
    }
    if (field === "origin_iata") {
      if (normalized.includes("required") || normalized.includes("missing")) return t("originRequired");
      if (normalized.includes("iata") || normalized.includes("pattern") || normalized.includes("3")) return t("iataInvalid");
      return message;
    }
    if (normalized.includes("required") || normalized.includes("missing")) return t("destinationRequired");
    if (normalized.includes("iata") || normalized.includes("pattern") || normalized.includes("3")) return t("iataInvalid");
    return message;
  }

  function parseValidationErrors(details: unknown): QuickSearchFieldErrors {
    if (!Array.isArray(details)) return {};
    const mapped: QuickSearchFieldErrors = {};
    details.forEach((item) => {
      if (!item || typeof item !== "object") return;
      const record = item as { loc?: unknown; msg?: unknown };
      if (!Array.isArray(record.loc) || typeof record.msg !== "string") return;
      const lastLoc = String(record.loc[record.loc.length - 1] || "");
      if (lastLoc === "origin_iata" || lastLoc === "destination_iata" || lastLoc === "travel_date") {
        mapped[lastLoc] = mapFieldValidationMessage(lastLoc, record.msg);
      }
    });
    return mapped;
  }

  function resultKey(result: SearchResult, fallback: number) {
    return result.result_id || `${result.origin}-${result.destination}-${result.travel_date}-${fallback}`;
  }

  function trackOpenRyanair() {
    trackEvent("quicksearch_open_ryanair", {
      origin,
      destination,
      travel_date: travelDate,
      is_return: isReturn,
      adults,
      source: "quick_search",
    });
  }

  function renderFlag(countryCode?: string | null) {
    const normalizedCode = (countryCode || "").trim().toUpperCase();
    if (!/^[A-Z]{2}$/.test(normalizedCode)) {
      return (
        <span className="qs-flag-fallback">
          <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
            <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeWidth="1.7" />
            <path
              d="M4 12h16M12 4a12 12 0 0 0 0 16M12 4a12 12 0 0 1 0 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </span>
      );
    }
    const OFFSET = 127397;
    const flag = String.fromCodePoint(
      normalizedCode.charCodeAt(0) + OFFSET,
      normalizedCode.charCodeAt(1) + OFFSET,
    );
    return <span className="qs-flag-emoji" aria-hidden="true">{flag}</span>;
  }

  function resolveInputCountryCode(
    countryOnlyCode?: string | null,
    selectedCode?: string | null,
  ): string | null {
    const candidate = countryOnlyCode ?? selectedCode ?? null;
    if (!candidate) return null;
    const normalized = candidate.trim().toUpperCase();
    return /^[A-Z]{2}$/.test(normalized) ? normalized : null;
  }

  function getTripTypeLabel(returnEnabled: boolean, selectedReturnDate: string): QuickSearchTripType {
    if (!returnEnabled) return "one_way";
    if (!selectedReturnDate) return "round_trip_incomplete";
    return "round_trip";
  }

  const originCode = origin.trim().toUpperCase();
  const destinationCode = destination.trim().toUpperCase();
  const originValid = originCountryOnly ? originCountryOnly.airports.length > 0 : (
    originCode.length === 3 && airportsByIata.has(originCode)
  );
  const destinationValid = destinationCountryOnly ? destinationCountryOnly.airports.length > 0 : (
    destinationCode.length === 3 && airportsByIata.has(destinationCode)
  );
  const originSuggestions = useMemo(() => buildAirportSuggestions(origin), [origin]);
  const destinationSuggestions = useMemo(() => buildAirportSuggestions(destination), [destination]);
  const countryAirports = useMemo(
    () => (selectedCountry ? airportsByCountry.get(selectedCountry.code) || [] : []),
    [selectedCountry],
  );
  const filteredCountryAirports = useMemo(() => {
    const q = airportSearch.trim().toLowerCase();
    const filtered = countryAirports.filter((a) => {
      if (!q) return true;
      if (a.iata.toLowerCase().startsWith(q)) return true;
      if (a.name.toLowerCase().includes(q)) return true;
      if (a.municipality.toLowerCase().includes(q)) return true;
      return false;
    });
    return filtered.length > 200 ? filtered.slice(0, 200) : filtered;
  }, [airportSearch, countryAirports]);
  const airportPickerModal = activePicker ? (
    <div className="airport-modal-overlay" onClick={closePicker}>
      <section
        className="airport-modal qs-airport-modal"
        role="dialog"
        aria-modal="true"
        aria-label={t("modalPickTitle")}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="qs-airport-modal__body">
          <div className="airport-modal-left qs-airport-modal__countries">
            <div className="qs-airport-modal__header">
              <h2>{activePicker === "origin" ? t("modalOriginCountry") : t("modalDestinationCountry")}</h2>
            </div>
            <div className="airport-country-grid">
              {countryOptions.map((country) => {
                const isActive = selectedCountry?.code === country.code;
                return (
                  <button
                    key={country.code}
                    type="button"
                    className={isActive ? "country-pill active" : "country-pill"}
                    onClick={() => {
                      setSelectedCountry(country);
                      setCountrySelectionTouched(true);
                    }}
                  >
                    {renderFlag(country.code)}
                    {country.name}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="airport-modal-right qs-airport-modal__airports">
            <div className="airport-modal-header qs-airport-modal__header">
              <h3>{t("modalPickTitle")}</h3>
              <button type="button" className="link-reset" onClick={clearSelection}>
                {t("modalClear")}
              </button>
            </div>
            {selectedCountry ? (
              <div className="section-gap-sm">
                <button type="button" className="btn-secondary btn-compact" onClick={() => selectCountryOnly(selectedCountry)}>
                  {t("pickCountryOnly").replace("{country}", selectedCountry.name)}
                </button>
                <p className="panel-note">{t("pickCountryOnlyHint")}</p>
              </div>
            ) : null}
            <div className="airport-search qs-airport-modal__search">
              <input
                ref={airportSearchInputRef}
                className="qs-input"
                name="airport_search"
                autoComplete="off"
                value={airportSearch}
                onChange={(e) => setAirportSearch(e.target.value)}
                placeholder={t("pickSearch")}
              />
            </div>
            {recentAirports.length > 0 ? (
              <div className="airport-recent qs-airport-modal__recents">
                <span className="muted">{t("pickRecent")}</span>
                <div className="airport-recent-grid">
                  {recentAirports.map((iata) => (
                    <button key={`recent-${iata}`} type="button" onClick={() => selectAirport(iata)}>
                      {iata}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="airport-list">
              {filteredCountryAirports.map((airport) => (
                <button key={airport.iata} type="button" onClick={() => selectAirport(airport.iata)}>
                  {renderFlag(selectedCountry?.code || null)}
                  {airport.municipality || airport.name} <span>{airport.iata}</span>
                </button>
              ))}
              {countryAirports.length === 0 ? (
                <p className="panel-note">{t("pickEmpty")}</p>
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </div>
  ) : null;
  const activeSuggestions = activeAutocompleteField === "origin"
    ? originSuggestions
    : activeAutocompleteField === "destination"
      ? destinationSuggestions
      : [];
  const activeSuggestionId =
    activeAutocompleteField && activeAutocompleteIndex >= 0 && activeAutocompleteIndex < activeSuggestions.length
      ? `${activeAutocompleteField}-suggestion-${activeSuggestions[activeAutocompleteIndex]?.iata}`
      : undefined;
  const autocompleteLiveText = activeAutocompleteField
    ? activeSuggestions.length > 0
      ? t("autocompleteSuggestionsAvailable").replace("{count}", String(activeSuggestions.length))
      : t("autocompleteNoSuggestions")
    : "";
  const tripType = getTripTypeLabel(isReturn, returnDate);
  const radiusActive = includeNearbyOrigins || includeNearbyDestinations;
  const hasInvalidRoute = !originValid || !destinationValid;
  const routeInputsValid = originValid && destinationValid;
  // edited criteria signature drives the dirty-state check against last applied criteria
  const currentCriteriaSignature = useMemo(() => buildCriteriaSignature({
    origin,
    destination,
    originCountryCode: originCountryOnly?.code ?? null,
    destinationCountryCode: destinationCountryOnly?.code ?? null,
    travelDate,
    returnDate,
    isReturn,
    adults,
    daysBefore,
    daysAfter,
    applyFlexReturn,
    includeStops,
    maxStops,
    durationMax,
    riskFilter,
    radiusKm,
    includeNearbyOrigins,
    includeNearbyDestinations,
    excludeOrigins,
    excludeDestinations,
    excludeOriginInput,
    excludeDestinationInput,
    strictFilters,
    priceMin,
    priceMax,
    departAfter,
    departBefore,
    bufferMin,
  }), [
    origin,
    destination,
    originCountryOnly,
    destinationCountryOnly,
    travelDate,
    returnDate,
    isReturn,
    adults,
    daysBefore,
    daysAfter,
    applyFlexReturn,
    includeStops,
    maxStops,
    durationMax,
    riskFilter,
    radiusKm,
    includeNearbyOrigins,
    includeNearbyDestinations,
    excludeOrigins,
    excludeDestinations,
    excludeOriginInput,
    excludeDestinationInput,
    strictFilters,
    priceMin,
    priceMax,
    departAfter,
    departBefore,
    bufferMin,
  ]);
  const pendingSearchChanges = Boolean(hasSearched && appliedCriteriaSignature && currentCriteriaSignature !== appliedCriteriaSignature);

  const searchDisabledHint = !routeInputsValid
    ? t("searchHintRouteInvalid")
    : tripType === "round_trip_incomplete"
      ? t("selectReturnHint")
    : !travelDate
      ? t("searchHintNeedDate")
      : "";
  const isReady = Boolean(
    routeInputsValid &&
    travelDate &&
    (!isReturn || returnDate) &&
    adults > 0 &&
    rateLimitSeconds === 0 &&
    !isLoading,
  );
  const summaryMissingBadges = [
    !origin.trim() && !originCountryOnly ? t("summaryMissingOrigin") : null,
    !destination.trim() && !destinationCountryOnly ? t("summaryMissingDestination") : null,
    !travelDate ? t("summaryMissingDate") : null,
    tripType === "round_trip_incomplete" ? t("summaryRoundTripMissingReturn") : null,
  ].filter((value): value is string => Boolean(value));
  const summaryDate = travelDate ? formatShortDate(travelDate) : "--";
  const summaryOriginLabel = originCountryOnly ? originCountryOnly.name : (origin || "---");
  const summaryDestinationLabel = destinationCountryOnly ? destinationCountryOnly.name : (destination || "---");
  const summaryTrip = `${summaryOriginLabel} → ${summaryDestinationLabel}`;
  const summaryTripTypeLabel = tripType === "one_way"
    ? t("summaryOneWay")
    : tripType === "round_trip"
      ? t("summaryRoundTrip")
      : t("summaryRoundTripMissingReturn");
  const summaryMeta = `${adults} ${adults === 1 ? t("summaryPassengersSingular") : t("summaryPassengersPlural")} - ${
    summaryTripTypeLabel
  } - ${summaryDate}`;
  const flexPreset = getQuickSearchFlexPreset(daysBefore, daysAfter);
  const summaryFlex = formatQuickSearchFlexSummary(daysBefore, daysAfter, {
    exact: t("exactDate"),
    plusOne: t("flexPresetOne"),
    plusTwo: t("flexPresetTwo"),
    plusThree: t("flexPresetThree"),
    customTemplate: t("flexCustomSummary"),
  });
  const effectiveFlexCustomPanelOpen = flexCustomPanelOpen || flexPreset === "custom";
  const flexHelperText = effectiveFlexCustomPanelOpen
    ? t("flexHelperCustom")
    : flexPreset === "exact"
      ? t("flexHelperExact")
      : t("flexHelperFlexible");
  const summaryStrict = strictFilters ? t("summaryStrictOn") : t("summaryStrictOff");
  const loadingPhaseLabel = loadingPhase === "requesting"
    ? t("loadingPhaseRequesting")
    : loadingPhase === "response_parsed"
      ? t("loadingPhaseResponseParsed")
      : loadingPhase === "client_done"
        ? t("loadingPhaseClientDone")
        : loadingPhase === "committed"
          ? t("loadingPhaseCommitted")
          : t("loadingPhaseRequesting");
  const progressPercent = Math.max(0, Math.min(100, Math.round(displayProgress)));
  const boardingPassengers = isMobileViewport ? 24 : 50;
  const progressRatio = Math.min(1, Math.max(0, displayProgress / 100));
  const easedProgressRatio = Math.pow(progressRatio, 2.2);
  const boardedCount = Math.min(
    boardingPassengers,
    Math.max(0, Math.floor(easedProgressRatio * boardingPassengers)),
  );
  const loadingSubcheckRoutes = useMemo(() => {
    const normalize = (value: string) => value.trim().toUpperCase();
    const dedupe = (values: string[]) => Array.from(new Set(values.filter(Boolean)));
    const buildPool = (
      value: string,
      countryOnly: CountryAirports | null,
      includeNearby: boolean,
    ) => {
      if (countryOnly?.airports?.length) {
        return dedupe(countryOnly.airports.map((airport) => normalize(airport.iata))).slice(0, 4);
      }
      const base = normalize(value);
      if (base.length !== 3 || !airportsByIata.has(base)) return [];
      if (!includeNearby) return [base];
      const country = findCountryByIataLocal(base);
      if (!country?.airports?.length) return [base];
      const nearby = country.airports
        .map((airport) => normalize(airport.iata))
        .filter((iata) => iata !== base)
        .slice(0, 3);
      return dedupe([base, ...nearby]).slice(0, 4);
    };

    const originPool = buildPool(origin, originCountryOnly, includeNearbyOrigins);
    const destinationPool = buildPool(destination, destinationCountryOnly, includeNearbyDestinations);
    const routes: string[] = [];

    for (const originCode of originPool) {
      for (const destinationCode of destinationPool) {
        if (originCode === destinationCode) continue;
        routes.push(`${originCode}-${destinationCode}`);
        if (routes.length >= 3) return routes;
      }
    }
    return routes.slice(0, 3);
  }, [
    origin,
    destination,
    originCountryOnly,
    destinationCountryOnly,
    includeNearbyOrigins,
    includeNearbyDestinations,
    findCountryByIataLocal,
  ]);
  const loadingSubcheckActiveIndex = loadingPhase === "requesting"
    ? (progressPercent >= 55 ? 1 : 0)
    : loadingPhase === "response_parsed"
      ? 1
      : loadingPhase === "client_done"
        ? 2
        : loadingPhase === "committed"
          ? 3
          : -1;
  const loadingSubchecks = useMemo(() => {
    return Array.from({ length: 3 }).map((_, idx) => {
      const route = loadingSubcheckRoutes[idx];
      const label = route
        ? t("loadingSubcheckFlight").replace("{route}", route)
        : t("loadingSubcheckCombo")
          .replace("{index}", String(idx + 1))
          .replace("{total}", "3");
      const status: QuickSearchLoadingSubcheckStatus = loadingSubcheckActiveIndex >= 3
        ? "done"
        : idx < loadingSubcheckActiveIndex
          ? "done"
          : idx === loadingSubcheckActiveIndex
            ? "active"
            : "pending";
      return {
        id: `loading-subcheck-${idx}`,
        label,
        status,
      };
    });
  }, [loadingSubcheckRoutes, loadingSubcheckActiveIndex, t]);
  const summaryDurationValue = parseNumericInput(durationMax, { min: 1 });
  const summaryDuration = summaryDurationValue !== null && Number.isFinite(summaryDurationValue)
    ? `${t("summaryDurationMax")} ${summaryDurationValue} min`
    : t("summaryDurationOpen");
  const summaryRadius = `${t("summaryRadius")} ${radiusKm} km`;
  const summaryExclusions = `${t("summaryExclusions")} ${excludeOrigins.length + excludeDestinations.length}`;
  const sortLabel = {
    ranking: t("sortRanking"),
    price: t("sortPrice"),
    duration: t("sortDuration"),
    risk: t("sortRisk"),
    freshness: t("sortFreshness"),
  } as const;
  const originCountry = resolveInputCountryCode(originCountryOnly?.code, originSelectedCountryCode);
  const destinationCountry = resolveInputCountryCode(destinationCountryOnly?.code, destinationSelectedCountryCode);
  const deeplinkUrl = deepLink?.url || deepLink?.fallback_url || localRyanairUrl;
  const {
    durationMaxNumber,
    visibleResults,
    hiddenHighRiskResults,
    warningSeverity,
    groupedNeutralWarnings,
    groupedCriticalWarnings,
    infoItemsCount,
    sourcesSummary,
    showDegradedState,
    zeroResultCauses,
    visibleZeroResultCauses,
    canExpandZeroResultCauses,
    emptyStateMainTitle,
    zeroResultActions,
  } = useQuickSearchScreenState({
    results,
    priceMin,
    priceMax,
    durationMax,
    riskFilter,
    sortBy,
    showHighRisk,
    filtersNotice,
    filtersMeta,
    isDegraded,
    searchMeta,
    weatherMessage,
    strictFilters,
    includeStops,
    radiusActive,
    radiusKm,
    excludeOriginsCount: excludeOrigins.length,
    excludeDestinationsCount: excludeDestinations.length,
    departAfter,
    departBefore,
    emptyCausesExpanded,
    t,
    tWarn,
  });
  const explainChipLabel = showDegradedState ? t("degradedChip") : t("toolbarExplain");
  const warningDetailOpenLabel = t("warningDetailsOpen");
  const warningDetailCloseLabel = t("warningDetailsClose");
  const warningGroupedTitle = t("warningsGroupedTitle");
  const warningProblemTitle = t("warningProblemTitle");

  useEffect(() => {
    if (!hasSearched || sourcesSummary.entries.length === 0) return;
    const key = `${jobId || "nojob"}:${sourcesSummary.entries.map(([source, count]) => `${source}:${count}`).join("|")}`;
    if (sourcesShownKeyRef.current === key) return;
    trackEvent("quicksearch_sources_aggregated_shown", {
      sources_count: sourcesSummary.entries.length,
      results_count: visibleResults.length,
    });
    sourcesShownKeyRef.current = key;
  }, [hasSearched, jobId, sourcesSummary.entries, visibleResults.length, sourcesShownKeyRef]);

  useEffect(() => {
    if (!hasSearched) return;
    const freshnessMode = searchMeta?.freshness_ts ? "timestamp" : "unavailable";
    const key = `${jobId || "nojob"}:${freshnessMode}:${searchMeta?.freshness_ts || "none"}`;
    if (freshnessShownKeyRef.current === key) return;
    trackEvent("quicksearch_freshness_global_shown", { mode: freshnessMode });
    freshnessShownKeyRef.current = key;
  }, [hasSearched, jobId, searchMeta?.freshness_ts, freshnessShownKeyRef]);

  const activeChips = useMemo(() => {
    const chips: Array<{ id: string; label: string; onClear: () => void }> = [];
    if (daysBefore > 0 || daysAfter > 0) {
      chips.push({
        id: "flex",
        label: summaryFlex,
        onClear: () => {
          setDaysBefore(0);
          setDaysAfter(0);
          setFlexCustomPanelOpen(false);
        },
      });
    }
    if (radiusActive && radiusKm !== 150) {
      chips.push({
        id: "radius",
        label: `${t("radiusLabel")}: ${radiusKm} km`,
        onClear: () => setRadiusKm(150),
      });
    }
    if (includeNearbyOrigins) {
      chips.push({
        id: "nearby-origins",
        label: t("nearbyOrigins"),
        onClear: () => setIncludeNearbyOrigins(false),
      });
    }
    if (includeNearbyDestinations) {
      chips.push({
        id: "nearby-destinations",
        label: t("nearbyDestinations"),
        onClear: () => setIncludeNearbyDestinations(false),
      });
    }
    if (priceMin) {
      chips.push({
        id: "price-min",
        label: `${t("priceMin")}: ${priceMin}`,
        onClear: () => setPriceMin(""),
      });
    }
    if (priceMax) {
      chips.push({
        id: "price-max",
        label: `${t("priceMax")}: ${priceMax}`,
        onClear: () => setPriceMax(""),
      });
    }
    if (durationMax) {
      chips.push({
        id: "duration-max",
        label: `${t("durationMax")}: ${durationMax}`,
        onClear: () => setDurationMax(""),
      });
    }
    if (!strictFilters) {
      chips.push({
        id: "strict",
        label: t("strictMode"),
        onClear: () => setStrictFilters(true),
      });
    }
    if (includeStops) {
      chips.push({
        id: "stops",
        label: `${t("includeStops")} - ${maxStops}`,
        onClear: () => setIncludeStops(false),
      });
    }
    if (riskFilter !== "all") {
      chips.push({
        id: "risk",
        label: `${t("riskAllowed")}: ${formatRiskLabel(riskFilter)}`,
        onClear: () => setRiskFilter("all"),
      });
    }
    if (excludeOrigins.length > 0) {
      chips.push({
        id: "exclude-origins",
        label: `${t("excludeOrigins")}: ${excludeOrigins.join(", ")}`,
        onClear: () => setExcludeOrigins([]),
      });
    }
    if (excludeDestinations.length > 0) {
      chips.push({
        id: "exclude-destinations",
        label: `${t("excludeDestinations")}: ${excludeDestinations.join(", ")}`,
        onClear: () => setExcludeDestinations([]),
      });
    }
    return chips;
  }, [
    daysBefore,
    daysAfter,
    summaryFlex,
    radiusActive,
    radiusKm,
    includeNearbyOrigins,
    includeNearbyDestinations,
    priceMin,
    priceMax,
    durationMax,
    strictFilters,
    includeStops,
    maxStops,
    riskFilter,
    excludeOrigins,
    excludeDestinations,
    formatRiskLabel,
    t,
    setDaysAfter,
    setDaysBefore,
    setFlexCustomPanelOpen,
    setDurationMax,
    setExcludeDestinations,
    setExcludeOrigins,
    setIncludeNearbyDestinations,
    setIncludeNearbyOrigins,
    setIncludeStops,
    setPriceMax,
    setPriceMin,
    setRadiusKm,
    setRiskFilter,
    setStrictFilters,
  ]);

  const clearAllFilters = useCallback(() => {
    activeChips.forEach((chip) => chip.onClear());
  }, [activeChips]);

  const [relaxPreviewOpen, setRelaxPreviewOpen] = useState(false);

  const relaxPreviewChanges = useMemo(() => {
    const rows: Array<{ id: string; label: string; before: string; after: string }> = [];
    if (strictFilters) {
      rows.push({ id: "strict", label: t("strictMode"), before: t("summaryStrictOn"), after: t("summaryStrictOff") });
    }
    if (riskFilter !== "all") {
      rows.push({ id: "risk", label: t("riskAllowed"), before: formatRiskLabel(riskFilter), after: t("riskAll") });
    }
    if (priceMin) {
      rows.push({ id: "priceMin", label: t("priceMin"), before: priceMin, after: "—" });
    }
    if (priceMax) {
      rows.push({ id: "priceMax", label: t("priceMax"), before: priceMax, after: "—" });
    }
    return rows;
  }, [strictFilters, riskFilter, priceMin, priceMax, t, formatRiskLabel]);

  const openRelaxPreview = () => {
    setRelaxPreviewOpen(true);
    trackEvent("relax_filters_preview_open", {
      changes_count: relaxPreviewChanges.length,
      restriction_types: relaxPreviewChanges.map((item) => item.id).join(","),
    });
  };

  const cancelRelaxPreview = () => {
    setRelaxPreviewOpen(false);
    trackEvent("relax_filters_cancelled", {
      changes_count: relaxPreviewChanges.length,
      restriction_types: relaxPreviewChanges.map((item) => item.id).join(","),
    });
  };

  const applyRelaxPreview = () => {
    setStrictFilters(false);
    setRiskFilter("all");
    setPriceMin("");
    setPriceMax("");
    setRelaxPreviewOpen(false);
    requestAnimationFrame(() => {
      void onSubmit({ preventDefault: () => {} } as FormEvent);
    });
    trackEvent("relax_filters_applied", {
      changes_count: relaxPreviewChanges.length,
      restriction_types: relaxPreviewChanges.map((item) => item.id).join(","),
    });
  };

  const undoZeroResultRelaxAction = useCallback((requestedAction?: ZeroResultRelaxAction) => {
    const undoPayload = relaxUndoRef.current;
    if (!undoPayload) return;
    if (requestedAction && undoPayload.action !== requestedAction) return;

    if (undoPayload.action === "disable_strict") {
      setStrictFilters(undoPayload.strictFilters);
    } else if (undoPayload.action === "increase_duration") {
      setDurationMax(undoPayload.durationMax);
    } else if (undoPayload.action === "open_radius_150") {
      setIncludeNearbyOrigins(undoPayload.includeNearbyOrigins);
      setIncludeNearbyDestinations(undoPayload.includeNearbyDestinations);
      setRadiusKm(undoPayload.radiusKm);
    } else {
      setExcludeOrigins(undoPayload.excludeOrigins);
      setExcludeDestinations(undoPayload.excludeDestinations);
      setExcludeOriginInput(undoPayload.excludeOriginInput);
      setExcludeDestinationInput(undoPayload.excludeDestinationInput);
    }

    trackEvent("quicksearch_relax_undo_clicked", { action: undoPayload.action });
    setSummaryHighlightKey(RELAX_HIGHLIGHT_BY_ACTION[undoPayload.action]);
    relaxUndoRef.current = null;
    setToast(null);
  }, [
    relaxUndoRef,
    setDurationMax,
    setExcludeDestinationInput,
    setExcludeDestinations,
    setExcludeOriginInput,
    setExcludeOrigins,
    setIncludeNearbyDestinations,
    setIncludeNearbyOrigins,
    setRadiusKm,
    setStrictFilters,
    setSummaryHighlightKey,
    setToast,
  ]);

  const onZeroResultRelaxAction = useCallback((action: ZeroResultRelaxAction) => {
    trackEvent("quicksearch_zero_results_relax_clicked", { action });
    const actionLabelMap: Record<ZeroResultRelaxAction, string> = {
      disable_strict: t("emptyActionDisableStrict"),
      increase_duration: t("emptyActionIncreaseDuration"),
      open_radius_150: t("emptyActionOpenRadius"),
      clear_exclusions: t("emptyActionClearExclusions"),
    };

    if (action === "disable_strict") {
      relaxUndoRef.current = { action, strictFilters };
      setStrictFilters(false);
    } else if (action === "increase_duration") {
      if (durationMaxNumber === null) return;
      relaxUndoRef.current = { action, durationMax };
      setDurationMax(String(durationMaxNumber + 60));
    } else if (action === "open_radius_150") {
      relaxUndoRef.current = {
        action,
        includeNearbyOrigins,
        includeNearbyDestinations,
        radiusKm,
      };
      setIncludeNearbyOrigins(true);
      setIncludeNearbyDestinations(true);
      setRadiusKm(150);
    } else {
      relaxUndoRef.current = {
        action,
        excludeOrigins,
        excludeDestinations,
        excludeOriginInput,
        excludeDestinationInput,
      };
      setExcludeOrigins([]);
      setExcludeDestinations([]);
      setExcludeOriginInput("");
      setExcludeDestinationInput("");
    }

    setSummaryHighlightKey(RELAX_HIGHLIGHT_BY_ACTION[action]);
    setToast({
      message: `${t("relaxToastPrefix")} ${actionLabelMap[action]}`,
      actionLabel: t("undoAction"),
      onAction: () => undoZeroResultRelaxAction(action),
    });
  }, [
    t,
    strictFilters,
    durationMax,
    durationMaxNumber,
    includeNearbyOrigins,
    includeNearbyDestinations,
    radiusKm,
    excludeOrigins,
    excludeDestinations,
    excludeOriginInput,
    excludeDestinationInput,
    undoZeroResultRelaxAction,
    relaxUndoRef,
    setDurationMax,
    setExcludeDestinationInput,
    setExcludeDestinations,
    setExcludeOriginInput,
    setExcludeOrigins,
    setIncludeNearbyDestinations,
    setIncludeNearbyOrigins,
    setRadiusKm,
    setStrictFilters,
    setSummaryHighlightKey,
    setToast,
  ]);

  const selectedResult = useMemo(() => {
    if (!selectedResultId) return null;
    return (
      visibleResults.find((item, idx) => resultKey(item, idx) === selectedResultId) || null
    );
  }, [visibleResults, selectedResultId]);

  const getCopyPayload = useCallback((result: SearchResult) => {
    return JSON.stringify(
      {
        origin_iata: result.origin || origin,
        destination_iata: result.destination || destination,
        date: result.travel_date || travelDate,
        flex_days_before: daysBefore,
        flex_days_after: daysAfter,
        radius_km: normalizedRadiusKm,
        include_nearby_origin: includeNearbyOrigins,
        include_nearby_destination: includeNearbyDestinations,
        price_min: parseNumericInput(priceMin, { min: 0 }) ?? undefined,
        price_max: parseNumericInput(priceMax, { min: 0 }) ?? undefined,
        departure_from: departAfter || undefined,
        departure_to: departBefore || undefined,
        duration_max_min: parseNumericInput(durationMax, { min: 1 }) ?? undefined,
        include_stops: includeStops,
        max_stops: includeStops ? maxStops : 0,
        risk_allowed: result.risk_label || riskFilter,
        exclude_origins: excludeOrigins,
        exclude_destinations: excludeDestinations,
        strict_mode: strictFilters,
        trip_type: isReturn ? "round_trip" : "one_way",
        return_date: isReturn ? returnDate : undefined,
        adults,
        flex_apply_return: isReturn ? applyFlexReturn : undefined,
        buffer_min: parseNumericInput(bufferMin, { min: 0 }) ?? undefined,
        result_id: result.result_id ?? undefined,
      },
      null,
      2,
    );
  }, [
    origin,
    destination,
    travelDate,
    daysBefore,
    daysAfter,
    includeNearbyOrigins,
    includeNearbyDestinations,
    priceMin,
    priceMax,
    departAfter,
    departBefore,
    durationMax,
    includeStops,
    maxStops,
    riskFilter,
    excludeOrigins,
    excludeDestinations,
    strictFilters,
    isReturn,
    returnDate,
    adults,
    applyFlexReturn,
    bufferMin,
    normalizedRadiusKm,
  ]);

  const quickSearchHint = useFtueHint("quick_search");
  const heroStatusTone =
    searchState === "error" || searchState === "rate"
      ? "alert"
      : searchState === "loading"
        ? "active"
        : showDegradedState || searchState === "empty"
          ? "warning"
          : hasSearched
            ? "ready"
            : "idle";
  const heroStatusLabel =
    searchState === "loading"
      ? t("loadingTitle")
      : searchState === "error"
        ? t("errorTitle")
        : searchState === "rate"
          ? t("rateLimitTitle")
          : showDegradedState
            ? t("degradedBadge")
            : hasSearched
              ? t("ready")
              : t("searchReadyTitle");
  const heroStatusTitle =
    searchState === "success"
      ? `${visibleResults.length} ${t("results")}`
      : searchState === "loading"
        ? `${progressPercent}%`
        : searchState === "rate"
          ? `${rateLimitSeconds}s`
          : searchState === "empty"
            ? emptyStateMainTitle
            : searchState === "error"
              ? t("errorTitle")
              : t("searchReadyTitle");
  const heroStatusBody =
    searchState === "success"
      ? executedCriteria?.route || summaryTrip
      : searchState === "loading"
        ? t("loadingText")
        : searchState === "rate"
          ? `${t("rateLimitText")} ${rateLimitSeconds}s`
          : searchState === "empty"
            ? t("emptyText")
            : searchState === "error"
              ? (searchError || t("searchFailed"))
              : (searchDisabledHint || t("searchReadyHint"));

  const runSearch = () => {
    void onSubmit({ preventDefault: () => {} } as FormEvent);
  };


  return (
    <main className="shell quick-search-shell" id="main-content">
      <section className="qs-command-stage">
        <div className="qs-command-stage__top">
          <div className="panel panel-soft qs-command-stage__intro">
            <div className="page-header qs-page-header">
              <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
                {t("back")}
              </button>
              <div className="page-title">
                <h1>{pageTitle}</h1>
                <p>{pageSubtitle}</p>
              </div>
            </div>
            <div className="qs-hero-meta" aria-live="polite">
              <span className="qs-hero-chip">{summaryTrip}</span>
              <span className="qs-hero-chip">{summaryMeta}</span>
              <span className="qs-hero-chip">{summaryFlex}</span>
              <span className={`qs-hero-chip ${showDegradedState ? "qs-hero-chip-warning" : ""}`}>
                {showDegradedState ? t("degradedChip") : summaryStrict}
              </span>
              {hasSearched ? (
                <span className="qs-hero-chip qs-hero-chip-accent">
                  {visibleResults.length} {t("results")}
                </span>
              ) : null}
            </div>
            {quickSearchHint.visible ? (
              <section className="notice notice-compact notice-info qs-hero-hint" role="status" aria-live="polite">
                <div>
                  <strong>{t("quickLookTitle")}</strong>
                  <p>{t("quickLookBody")}</p>
                </div>
                <div className="notice-actions">
                  <button type="button" className="btn-ghost btn-compact" onClick={quickSearchHint.dismiss}>
                    {t("quickLookAcknowledge")}
                  </button>
                </div>
              </section>
            ) : null}
          </div>
          <aside className={`panel panel-soft qs-command-stage__status qs-command-stage__status-${heroStatusTone}`} aria-live="polite">
            <div className="qs-command-stage__status-head">
              <span className="qs-command-stage__eyebrow">{t("searchSummaryTitle")}</span>
              <span className={`qs-command-stage__status-badge qs-command-stage__status-badge-${heroStatusTone}`}>
                {heroStatusLabel}
              </span>
            </div>
            <div className="qs-command-stage__status-copy">
              <strong>{heroStatusTitle}</strong>
              <p>{heroStatusBody}</p>
            </div>
            <div className="qs-command-stage__status-grid">
              <div className="qs-command-stage__metric">
                <span>{searchState === "loading" ? t("loadingTitle") : t("results")}</span>
                <strong>{searchState === "loading" ? `${progressPercent}%` : visibleResults.length}</strong>
              </div>
              <div className="qs-command-stage__metric">
                <span>{t("filtersTitle")}</span>
                <strong>{activeChips.length}</strong>
              </div>
              <div className="qs-command-stage__metric">
                <span>{t("infoSectionTitle")}</span>
                <strong>{infoItemsCount}</strong>
              </div>
            </div>
            {executedCriteria ? (
              <div className="qs-command-stage__snapshot">
                <span>{executedCriteria.route}</span>
                <span>{executedCriteria.dateLabel}</span>
                <span>{executedCriteria.paxLabel}</span>
              </div>
            ) : (
              <div className="qs-summary-detail-row qs-command-stage__snapshot">
                <span className="qs-summary-chip">{summaryTrip}</span>
                <span className="qs-summary-chip">{summaryMeta}</span>
                <span className="qs-summary-chip">{summaryFlex}</span>
              </div>
            )}
            <div className="qs-command-stage__signals">
              {pendingSearchChanges ? (
                <span className="qs-summary-chip qs-command-stage__signal qs-command-stage__signal-pending">
                  {t("pendingChangesTitle")}
                </span>
              ) : null}
              {warningSeverity.critical.length > 0 ? (
                <span className="qs-summary-chip qs-command-stage__signal qs-command-stage__signal-critical">
                  {warningSeverity.critical.length} {warningProblemTitle}
                </span>
              ) : null}
              {searchMeta?.freshness_ts ? (
                <span className="qs-summary-chip qs-command-stage__signal">
                  {t("freshnessLabel")} {formatFreshness(searchMeta.freshness_ts)}
                </span>
              ) : null}
            </div>
          </aside>
        </div>
        <QuickSearchSearchForm formRef={formRef} isReady={isReady} routePulse={routePulse} onSubmit={onSubmit}>
        <div className="qs-route">
          <div className="qs-route-card">
            <label className="qs-label">
              <span>
                {t("originLabel")}
                <span className="qs-tip" data-tip={t("originTip")} tabIndex={0} role="note" aria-label={t("originTip")}>
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.8" />
                    <path d="M12 16.2v.2M9.8 9.2a2.2 2.2 0 1 1 3.3 1.9c-.8.5-1.1.9-1.1 1.8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </span>
              </span>
              <div className="qs-input-wrap">
                <span className="qs-input-prefix" aria-hidden="true">
                  {renderFlag(originCountry)}
                  <span className="qs-input-icon">
                    <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                      <path
                        d="M3 11l18-6-6 18-2.2-7.2L3 11z"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                      />
                      <path
                        d="M11 13l7-7"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                      />
                    </svg>
                  </span>
                </span>
                <input
                  className="qs-input qs-input-with-action"
                  role="combobox"
                  name="origin_iata"
                  autoComplete="off"
                  aria-autocomplete="list"
                  value={origin}
                  onFocus={() => {
                    onFieldFocus();
                    onAutocompleteFieldFocus("origin");
                  }}
                  onBlur={() => {
                    onFieldBlur();
                    setOriginTouched(true);
                    onAutocompleteFieldBlur();
                  }}
                  onChange={(e) => {
                    setOrigin(e.target.value.toUpperCase());
                    setOriginCountryOnly(null);
                    setOriginSelectedCountryCode(null);
                    setFieldErrors((prev) => ({ ...prev, origin_iata: undefined }));
                    setActiveAutocompleteField("origin");
                    setActiveAutocompleteIndex(-1);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "ArrowDown") {
                      event.preventDefault();
                      if (originSuggestions.length === 0) return;
                      setActiveAutocompleteField("origin");
                      setActiveAutocompleteIndex((prev) => {
                        if (prev < 0) return 0;
                        return (prev + 1) % originSuggestions.length;
                      });
                      return;
                    }
                    if (event.key === "ArrowUp") {
                      event.preventDefault();
                      if (originSuggestions.length === 0) return;
                      setActiveAutocompleteField("origin");
                      setActiveAutocompleteIndex((prev) => {
                        if (prev <= 0) return originSuggestions.length - 1;
                        return prev - 1;
                      });
                      return;
                    }
                    if (event.key === "Escape") {
                      setActiveAutocompleteField(null);
                      setActiveAutocompleteIndex(-1);
                      return;
                    }
                    if (event.key === "Enter") {
                      const selected = activeAutocompleteField === "origin" && activeAutocompleteIndex >= 0
                        ? originSuggestions[activeAutocompleteIndex]
                        : originSuggestions[0] || null;
                      if (selected) {
                        event.preventDefault();
                        selectAutocompleteSuggestion("origin", selected.iata, true);
                        return;
                      }
                      if (!origin.trim() && !destination.trim() && !originCountryOnly && !destinationCountryOnly) {
                        event.preventDefault();
                        onEmptySearchValidation();
                      }
                    }
                  }}
                  placeholder={originCountryOnly ? originCountryOnly.name : t("placeholderOrigin")}
                  aria-invalid={(originTouched && !originValid) || Boolean(fieldErrors.origin_iata)}
                  aria-describedby="origin-help"
                  aria-expanded={activeAutocompleteField === "origin"}
                  aria-controls="origin-suggestions"
                  aria-activedescendant={activeAutocompleteField === "origin" ? activeSuggestionId : undefined}
                />
                <button
                  type="button"
                  className="qs-input-inline-action"
                  onClick={(event) => {
                    lastPickerTriggerRef.current = event.currentTarget;
                    openPicker("origin");
                  }}
                  aria-label={t("pickAirportOriginAria")}
                >
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <path
                      d="M12 21s7-7.4 7-12a7 7 0 1 0-14 0c0 4.6 7 12 7 12z"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinejoin="round"
                    />
                    <circle cx="12" cy="9" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.6" />
                  </svg>
                </button>
                {activeAutocompleteField === "origin" && originSuggestions.length > 0 ? (
                  <ul className="qs-autocomplete" id="origin-suggestions" role="listbox">
                    {originSuggestions.map((suggestion, index) => {
                      const isActive = index === activeAutocompleteIndex;
                      return (
                        <li key={`origin-${suggestion.iata}`} role="option" aria-selected={isActive}>
                          <button
                            id={`origin-suggestion-${suggestion.iata}`}
                            type="button"
                            className={isActive ? "qs-autocomplete-item active" : "qs-autocomplete-item"}
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => selectAutocompleteSuggestion("origin", suggestion.iata)}
                          >
                            <strong>{suggestion.iata}</strong>
                            <span>{suggestion.name}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </div>
              <small id="origin-help">{t("originHelp")} {t("iataHelp")}</small>
              {!originValid && originSuggestions.length > 0 ? (
                <small className="muted">{t("iataSuggest")}</small>
              ) : null}
              {originCountryOnly ? (
                <div className="qs-country-row">
                  <span className="qs-chip">{t("countryOnlySelected").replace("{country}", originCountryOnly.name)}</span>
                  <button type="button" className="btn-ghost btn-compact" onClick={() => setOriginCountryOnly(null)}>
                    {t("countryOnlyClear")}
                  </button>
                </div>
              ) : null}
              {(originTouched && !originValid) || fieldErrors.origin_iata ? (
                <small className="qs-error">
                  {fieldErrors.origin_iata || (origin.trim() ? t("iataInvalid") : t("originRequired"))}
                </small>
              ) : null}
            </label>
          </div>

          <div className="qs-route-line" aria-hidden="true">
            <span className="qs-route-plane">
              <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                <path
                  d="M3 13l18-6-6 18-2.2-7.2L3 13z"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              </svg>
            </span>
          </div>

          <div className="qs-route-card">
            <label className="qs-label">
              <span>
                {t("destinationLabel")}
                <span className="qs-tip" data-tip={t("destinationTip")} tabIndex={0} role="note" aria-label={t("destinationTip")}>
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.8" />
                    <path d="M12 16.2v.2M9.8 9.2a2.2 2.2 0 1 1 3.3 1.9c-.8.5-1.1.9-1.1 1.8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </span>
              </span>
              <div className="qs-input-wrap">
                <span className="qs-input-prefix" aria-hidden="true">
                  {renderFlag(destinationCountry)}
                  <span className="qs-input-icon">
                    <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                      <path
                        d="M12 21s7-7.4 7-12a7 7 0 1 0-14 0c0 4.6 7 12 7 12z"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinejoin="round"
                      />
                      <circle cx="12" cy="9" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.6" />
                    </svg>
                  </span>
                </span>
                <input
                  className="qs-input qs-input-with-action"
                  role="combobox"
                  name="destination_iata"
                  autoComplete="off"
                  aria-autocomplete="list"
                  value={destination}
                  onFocus={() => {
                    onFieldFocus();
                    onAutocompleteFieldFocus("destination");
                  }}
                  onBlur={() => {
                    onFieldBlur();
                    setDestinationTouched(true);
                    onAutocompleteFieldBlur();
                  }}
                  onChange={(e) => {
                    setDestination(e.target.value.toUpperCase());
                    setDestinationCountryOnly(null);
                    setDestinationSelectedCountryCode(null);
                    setFieldErrors((prev) => ({ ...prev, destination_iata: undefined }));
                    setActiveAutocompleteField("destination");
                    setActiveAutocompleteIndex(-1);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "ArrowDown") {
                      event.preventDefault();
                      if (destinationSuggestions.length === 0) return;
                      setActiveAutocompleteField("destination");
                      setActiveAutocompleteIndex((prev) => {
                        if (prev < 0) return 0;
                        return (prev + 1) % destinationSuggestions.length;
                      });
                      return;
                    }
                    if (event.key === "ArrowUp") {
                      event.preventDefault();
                      if (destinationSuggestions.length === 0) return;
                      setActiveAutocompleteField("destination");
                      setActiveAutocompleteIndex((prev) => {
                        if (prev <= 0) return destinationSuggestions.length - 1;
                        return prev - 1;
                      });
                      return;
                    }
                    if (event.key === "Escape") {
                      setActiveAutocompleteField(null);
                      setActiveAutocompleteIndex(-1);
                      return;
                    }
                    if (event.key === "Enter") {
                      const selected = activeAutocompleteField === "destination" && activeAutocompleteIndex >= 0
                        ? destinationSuggestions[activeAutocompleteIndex]
                        : destinationSuggestions[0] || null;
                      if (selected) {
                        event.preventDefault();
                        selectAutocompleteSuggestion("destination", selected.iata, true);
                        return;
                      }
                      if (!origin.trim() && !destination.trim() && !originCountryOnly && !destinationCountryOnly) {
                        event.preventDefault();
                        onEmptySearchValidation();
                      }
                    }
                  }}
                  placeholder={destinationCountryOnly ? destinationCountryOnly.name : t("placeholderDestination")}
                  aria-invalid={(destinationTouched && !destinationValid) || Boolean(fieldErrors.destination_iata)}
                  aria-describedby="destination-help"
                  aria-expanded={activeAutocompleteField === "destination"}
                  aria-controls="destination-suggestions"
                  aria-activedescendant={activeAutocompleteField === "destination" ? activeSuggestionId : undefined}
                />
                <button
                  type="button"
                  className="qs-input-inline-action"
                  onClick={(event) => {
                    lastPickerTriggerRef.current = event.currentTarget;
                    openPicker("destination");
                  }}
                  aria-label={t("pickAirportDestinationAria")}
                >
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <path
                      d="M12 21s7-7.4 7-12a7 7 0 1 0-14 0c0 4.6 7 12 7 12z"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinejoin="round"
                    />
                    <circle cx="12" cy="9" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.6" />
                  </svg>
                </button>
                {activeAutocompleteField === "destination" && destinationSuggestions.length > 0 ? (
                  <ul className="qs-autocomplete" id="destination-suggestions" role="listbox">
                    {destinationSuggestions.map((suggestion, index) => {
                      const isActive = index === activeAutocompleteIndex;
                      return (
                        <li key={`destination-${suggestion.iata}`} role="option" aria-selected={isActive}>
                          <button
                            id={`destination-suggestion-${suggestion.iata}`}
                            type="button"
                            className={isActive ? "qs-autocomplete-item active" : "qs-autocomplete-item"}
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => selectAutocompleteSuggestion("destination", suggestion.iata)}
                          >
                            <strong>{suggestion.iata}</strong>
                            <span>{suggestion.name}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </div>
              <small id="destination-help">{t("destinationHelp")} {t("iataHelp")}</small>
              {!destinationValid && destinationSuggestions.length > 0 ? (
                <small className="muted">{t("iataSuggest")}</small>
              ) : null}
              {destinationCountryOnly ? (
                <div className="qs-country-row">
                  <span className="qs-chip">{t("countryOnlySelected").replace("{country}", destinationCountryOnly.name)}</span>
                  <button type="button" className="btn-ghost btn-compact" onClick={() => setDestinationCountryOnly(null)}>
                    {t("countryOnlyClear")}
                  </button>
                </div>
              ) : null}
              {(destinationTouched && !destinationValid) || fieldErrors.destination_iata ? (
                <small className="qs-error">
                  {fieldErrors.destination_iata || (destination.trim() ? t("iataInvalid") : t("destinationRequired"))}
                </small>
              ) : null}
            </label>
          </div>
        </div>
        <div className="qs-flex-row">
          <div className="qs-flex-control">
            <div className="qs-flex-header">
              <span className="qs-label-title">{t("flexTitle")}</span>
              <span className="qs-flex-summary">{summaryFlex}</span>
            </div>
            <p className="qs-flex-helper">{flexHelperText}</p>
            <div className="qs-flex-presets" role="group" aria-label={t("flexTitle")}>
              <button
                type="button"
                className={`qs-flex-preset ${!effectiveFlexCustomPanelOpen && flexPreset === "exact" ? "is-active" : ""}`}
                aria-pressed={!effectiveFlexCustomPanelOpen && flexPreset === "exact"}
                onClick={() => setFlexPreset("exact")}
              >
                {t("flexPresetExact")}
              </button>
              <button
                type="button"
                className={`qs-flex-preset ${!effectiveFlexCustomPanelOpen && flexPreset === "plus-1" ? "is-active" : ""}`}
                aria-pressed={!effectiveFlexCustomPanelOpen && flexPreset === "plus-1"}
                onClick={() => setFlexPreset("plus-1")}
              >
                {t("flexPresetOne")}
              </button>
              <button
                type="button"
                className={`qs-flex-preset ${!effectiveFlexCustomPanelOpen && flexPreset === "plus-2" ? "is-active" : ""}`}
                aria-pressed={!effectiveFlexCustomPanelOpen && flexPreset === "plus-2"}
                onClick={() => setFlexPreset("plus-2")}
              >
                {t("flexPresetTwo")}
              </button>
              <button
                type="button"
                className={`qs-flex-preset ${!effectiveFlexCustomPanelOpen && flexPreset === "plus-3" ? "is-active" : ""}`}
                aria-pressed={!effectiveFlexCustomPanelOpen && flexPreset === "plus-3"}
                onClick={() => setFlexPreset("plus-3")}
              >
                {t("flexPresetThree")}
              </button>
              <button
                type="button"
                className={`qs-flex-preset ${effectiveFlexCustomPanelOpen ? "is-active" : ""}`}
                aria-pressed={effectiveFlexCustomPanelOpen}
                onClick={() => setFlexCustomPanelOpen(true)}
              >
                {t("flexPresetCustom")}
              </button>
            </div>
            {effectiveFlexCustomPanelOpen ? (
              <div className="qs-flex-panel">
                <div className="qs-flex-grid">
                  <div className="qs-flex-field">
                    <span>{t("flexBeforeControl")}</span>
                    <div className="qs-flex-stepper">
                      <button
                        type="button"
                        className="qs-flex-stepper-btn"
                        aria-label={`${t("daysBefore")}: -1`}
                        onClick={() => updateDaysBefore(-1)}
                        disabled={daysBefore <= 0}
                      >
                        -
                      </button>
                      <div className="qs-flex-stepper-value">
                        <strong>{daysBefore}</strong>
                        <span>{t("daysBefore")}</span>
                      </div>
                      <button
                        type="button"
                        className="qs-flex-stepper-btn"
                        aria-label={`${t("daysBefore")}: +1`}
                        onClick={() => updateDaysBefore(1)}
                        disabled={daysBefore >= 7}
                      >
                        +
                      </button>
                    </div>
                  </div>
                  <div className="qs-flex-field">
                    <span>{t("flexAfterControl")}</span>
                    <div className="qs-flex-stepper">
                      <button
                        type="button"
                        className="qs-flex-stepper-btn"
                        aria-label={`${t("daysAfter")}: -1`}
                        onClick={() => updateDaysAfter(-1)}
                        disabled={daysAfter <= 0}
                      >
                        -
                      </button>
                      <div className="qs-flex-stepper-value">
                        <strong>{daysAfter}</strong>
                        <span>{t("daysAfter")}</span>
                      </div>
                      <button
                        type="button"
                        className="qs-flex-stepper-btn"
                        aria-label={`${t("daysAfter")}: +1`}
                        onClick={() => updateDaysAfter(1)}
                        disabled={daysAfter >= 7}
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
                {isReturn ? (
                  <label className="qs-check">
                    <input
                      type="checkbox"
                      name="flex_apply_return"
                      checked={applyFlexReturn}
                      onChange={(e) => setApplyFlexReturn(e.target.checked)}
                    />
                    <span className="qs-check-ui" aria-hidden="true">
                      <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                        <path
                          d="M5.5 12.5 10 17l8.5-9"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </span>
                    {t("flexApplyReturn")}
                  </label>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
        <span className="sr-only" aria-live="polite">{autocompleteLiveText}</span>

        <div className="qs-date-grid">
          <label className="date-field qs-label">
            <span>
              {t("dateLabel")}
              <span className="qs-tip" data-tip={t("dateTip")} tabIndex={0} role="note" aria-label={t("dateTip")}>
                <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.8" />
                  <path d="M12 16.2v.2M9.8 9.2a2.2 2.2 0 1 1 3.3 1.9c-.8.5-1.1.9-1.1 1.8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </span>
            </span>
            <QuickSearchDatePicker
              name="travel_date"
              label={t("dateLabel")}
              value={travelDate}
              placeholder={t("placeholderDates")}
              localeTag={localeTag}
              variant="outbound"
              invalid={(dateTouched && !travelDate) || Boolean(fieldErrors.travel_date)}
              onBlur={() => setDateTouched(true)}
              onChange={(value) => {
                setTravelDate(value);
                setFieldErrors((prev) => ({ ...prev, travel_date: undefined }));
              }}
            />
            {(dateTouched && !travelDate) || fieldErrors.travel_date ? (
              <small className="qs-error">{fieldErrors.travel_date || t("selectOutbound")}</small>
            ) : null}
          </label>

          <label className="qs-check qs-check-inline">
            <input
              type="checkbox"
              name="is_return"
              checked={isReturn}
              onChange={(e) => setIsReturn(e.target.checked)}
            />
            <span className="qs-check-ui" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                <path
                  d="M5.5 12.5 10 17l8.5-9"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            {t("roundTrip")}
          </label>

          {isReturn ? (
            <label className="date-field qs-label">
              <span>{t("returnLabel")}</span>
              <QuickSearchDatePicker
                name="return_date"
                label={t("returnLabel")}
                value={returnDate}
                placeholder={t("placeholderDates")}
                localeTag={localeTag}
                variant="return"
                min={travelDate || undefined}
                onChange={setReturnDate}
              />
              {tripType === "round_trip_incomplete" ? (
                <small className="qs-search-hint qs-return-hint">{t("selectReturnHint")}</small>
              ) : null}
            </label>
          ) : null}
        </div>

        <div className="qs-passengers">
          <span>{t("passengers")}</span>
          <div className="qs-stepper">
            <button type="button" onClick={() => changeAdults(-1)} disabled={adults <= 1}>
              -
            </button>
            <span className="qs-stepper-value">{adults}</span>
            <button type="button" onClick={() => changeAdults(1)} disabled={adults >= 9}>
              +
            </button>
          </div>
        </div>

        <section className="panel panel-soft qs-setup-critical-filters">
          <div className="panel-header">
            <h3>{t("filtersTitle")}</h3>
            <button type="button" className="btn-ghost btn-compact" onClick={() => setIsFiltersOpen(true)}>
              {t("toolbarFilters")}
            </button>
          </div>
          <div className="qs-filter-grid">
            <label className="qs-check">
              <input
                type="checkbox"
                name="include_stops_quick"
                checked={includeStops}
                onChange={(e) => setIncludeStops(e.target.checked)}
              />
              <span className="qs-check-ui" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5.5 12.5 10 17l8.5-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
              {t("includeStops")}
            </label>
            <label className="field">
              {t("maxStops")}
              <select value={maxStops} onChange={(e) => setMaxStops(Number(e.target.value))} className="qs-input" disabled={!includeStops}>
                <option value={1}>{t("stopsOne")}</option>
                <option value={2}>{t("stopsTwo")}</option>
              </select>
            </label>
            <label className="field">
              {t("durationMax")}
              <input className="qs-input" type="number" min={1} step={1} value={durationMax} onChange={(e) => setDurationMax(e.target.value)} placeholder="240" aria-invalid={Boolean(fieldErrors.duration_max)} />
              {fieldErrors.duration_max ? <small className="qs-error">{fieldErrors.duration_max}</small> : null}
            </label>
            <label className="field">
              {t("riskAllowed")}
              <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value as "all" | "low" | "medium" | "high")} className="qs-input">
                <option value="all">{t("riskAll")}</option>
                <option value="low">{t("riskLow")}</option>
                <option value="medium">{t("riskMedium")}</option>
                <option value="high">{t("riskHigh")}</option>
              </select>
            </label>
            <label className="field">
              {t("radiusLabel")}
              <input className="qs-input" type="number" min={0} value={radiusKm} onChange={(e) => setRadiusKm(Math.max(0, Number(e.target.value)))} disabled={!radiusActive} />
            </label>
          </div>
        </section>

        <div className="qs-actions">
          <div className="qs-search-cta">
            <button className="btn-search" type="submit" disabled={!isReady || !routeInputsValid}>
              {isLoading ? t("loadingAria") : t("search")}
            </button>
            {!isReady && searchDisabledHint ? (
              <small className="qs-search-hint">{searchDisabledHint}</small>
            ) : null}
          </div>
          <div className="qs-summary">
            <strong>{summaryTrip}</strong>
            <span>{summaryMeta}</span>
            <div className="qs-summary-detail-row">
              <span className={`qs-summary-chip ${summaryHighlightKey === "strict" ? "qs-summary-chip-highlight" : ""}`}>
                {summaryStrict}
              </span>
              <span className={`qs-summary-chip ${summaryHighlightKey === "duration" ? "qs-summary-chip-highlight" : ""}`}>
                {summaryDuration}
              </span>
              <span className={`qs-summary-chip ${summaryHighlightKey === "radius" ? "qs-summary-chip-highlight" : ""}`}>
                {summaryRadius}
              </span>
              <span className={`qs-summary-chip ${summaryHighlightKey === "exclusions" ? "qs-summary-chip-highlight" : ""}`}>
                {summaryExclusions}
              </span>
            </div>
            <span>{summaryFlex}</span>
            {summaryMissingBadges.length > 0 ? (
              <div className="qs-summary-missing">
                {summaryMissingBadges.map((badge) => (
                  <span key={badge} className="qs-summary-missing-badge">{badge}</span>
                ))}
              </div>
            ) : null}
          </div>
          <div className="qs-ready" aria-live="polite">
            <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
              <path
                d="M5.5 12.5 10 17l8.5-9"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {t("ready")}
          </div>
        </div>
        </QuickSearchSearchForm>
      </section>

      {hasSearched ? (
      <QuickSearchResultsWorkspace>
      <div id="qs-workspace-hint" className="qs-workspace-hint">
        {pageWorkspaceHint}
      </div>
      <div className="qs-workspace">
        {isFiltersOpen && typeof document !== "undefined"
        ? createPortal((
          <button
            type="button"
            className="qs-filters-backdrop"
            aria-label={t("pickClose")}
            onClick={closeFiltersDrawer}
          />
        ), document.body) : null}
        <aside
          id="qs-filters-drawer"
          role="dialog"
          aria-modal={isFiltersOpen}
          aria-label={t("filtersTitle")}
          className={`panel panel-soft qs-filters-panel ${isFiltersOpen ? "open" : ""}`}
        >
          <div className="qs-filters-header">
            <div>
              <h2>{t("filtersTitle")}</h2>
              <span className="muted">{t("filtersSubtitle")}</span>
            </div>
            <button
              type="button"
              className="btn-ghost qs-filters-close"
              aria-label={t("pickClose")}
              ref={filtersCloseRef}
              onClick={closeFiltersDrawer}
            >
              {t("pickClose")}
            </button>
          </div>
          <div className="qs-filters-grid">
            <div className="qs-filter-group qs-filter-core">
              <div className="qs-filter-head">
                <h3>{t("infoSectionTitle")}</h3>
              </div>
              <div className="qs-filter-grid">
                <label className="field">
                  {t("priceMin")}
                  <input
                    type="number"
                    min={0}
                    step={1}
                    name="price_min"
                    autoComplete="off"
                    value={priceMin}
                    onChange={(e) => setPriceMin(e.target.value)}
                    placeholder="10"
                    className="qs-input"
                    aria-invalid={Boolean(fieldErrors.price_min)}
                  />
                  {fieldErrors.price_min ? <small className="qs-error">{fieldErrors.price_min}</small> : null}
                </label>
                <label className="field">
                  {t("durationMax")}
                  <input
                    type="number"
                    min={1}
                    step={1}
                    name="duration_max"
                    autoComplete="off"
                    value={durationMax}
                    onChange={(e) => setDurationMax(e.target.value)}
                    placeholder="240"
                    className="qs-input"
                    aria-invalid={Boolean(fieldErrors.duration_max)}
                  />
                  {fieldErrors.duration_max ? <small className="qs-error">{fieldErrors.duration_max}</small> : null}
                </label>
                <label className="field">
                  {t("priceMax")}
                  <input
                    type="number"
                    min={0}
                    step={1}
                    name="price_max"
                    autoComplete="off"
                    value={priceMax}
                    onChange={(e) => setPriceMax(e.target.value)}
                    placeholder="120"
                    className="qs-input"
                    aria-invalid={Boolean(fieldErrors.price_max)}
                  />
                  {fieldErrors.price_max ? <small className="qs-error">{fieldErrors.price_max}</small> : null}
                </label>
              </div>
            </div>

            <details className="qs-filter-accordion" open>
              <summary className="qs-filter-summary">
                <div className="qs-filter-head">
                  <h3>{t("alternatesTitle")}</h3>
                  {prefBadge ? <span className="badge badge-control">{t("appliedPref")}</span> : null}
                </div>
              </summary>
              <div className="qs-filter-group">
                <div className="qs-filter-grid">
                  <label className="field">
                    {t("radiusLabel")}
                    <div className="qs-range">
                      <input
                        type="range"
                        name="radius_km_range"
                        min={0}
                        max={300}
                        value={radiusKm}
                        onChange={(e) => setRadiusKm(Math.max(0, Number(e.target.value)))}
                        disabled={!radiusActive}
                      />
                      <input
                        name="radius_km"
                        autoComplete="off"
                        value={radiusKm}
                        onChange={(e) => setRadiusKm(Math.max(0, Number(e.target.value)))}
                        className="qs-input"
                        disabled={!radiusActive}
                      />
                    </div>
                    <small className="muted">{radiusActive ? t("radiusHint") : t("radiusInactive")}</small>
                  </label>
                <label className="qs-check">
                  <input
                    type="checkbox"
                    name="include_nearby_origins"
                    checked={includeNearbyOrigins}
                    onChange={(e) => setIncludeNearbyOrigins(e.target.checked)}
                  />
                  <span className="qs-check-ui" aria-hidden="true">
                    <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                      <path
                        d="M5.5 12.5 10 17l8.5-9"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  {t("nearbyOrigins")}
                </label>
                <label className="qs-check">
                  <input
                    type="checkbox"
                    name="include_nearby_destinations"
                    checked={includeNearbyDestinations}
                    onChange={(e) => setIncludeNearbyDestinations(e.target.checked)}
                  />
                  <span className="qs-check-ui" aria-hidden="true">
                    <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                      <path
                        d="M5.5 12.5 10 17l8.5-9"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  {t("nearbyDestinations")}
                </label>
              </div>
              </div>
            </details>

            <details className="qs-filter-accordion">
              <summary className="qs-filter-summary">
                <div className="qs-filter-head">
                  <h3>{t("timeTitle")}</h3>
                  <span className="muted">{t("timeSubtitle")}</span>
                </div>
              </summary>
              <div className="qs-filter-group">
              <div className="qs-filter-grid">
                <label className="field">
                  {t("departAfter")}
                  <input
                    type="time"
                    name="depart_after"
                    autoComplete="off"
                    value={departAfter}
                    onChange={(e) => setDepartAfter(e.target.value)}
                    className="qs-input"
                  />
                </label>
                <label className="field">
                  {t("departBefore")}
                  <input
                    type="time"
                    name="depart_before"
                    autoComplete="off"
                    value={departBefore}
                    onChange={(e) => setDepartBefore(e.target.value)}
                    className="qs-input"
                  />
                </label>
                <label className="qs-check">
                  <input
                    type="checkbox"
                    name="strict_filters"
                    checked={strictFilters}
                    onChange={(e) => setStrictFilters(e.target.checked)}
                  />
                  <span className="qs-check-ui" aria-hidden="true">
                    <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                      <path
                        d="M5.5 12.5 10 17l8.5-9"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  {t("strictMode")}
                </label>
              </div>
              {!strictFilters ? (
                <div className="qs-warning">
                  {t("strictWarning")}
                </div>
              ) : null}
              </div>
            </details>

            <details className="qs-filter-accordion">
              <summary className="qs-filter-summary">
                <div className="qs-filter-head">
                  <h3>{t("stopsTitle")}</h3>
                  <span className="muted">{t("stopsSubtitle")}</span>
                </div>
              </summary>
              <div className="qs-filter-group">
              <div className="qs-filter-grid">
                <label className="qs-check">
                  <input
                    type="checkbox"
                    name="include_stops"
                    checked={includeStops}
                    onChange={(e) => setIncludeStops(e.target.checked)}
                  />
                  <span className="qs-check-ui" aria-hidden="true">
                    <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                      <path
                        d="M5.5 12.5 10 17l8.5-9"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  {t("includeStops")}
                </label>
                <label className="field">
                  {t("maxStops")}
                  <select
                    name="max_stops"
                    autoComplete="off"
                    value={maxStops}
                    onChange={(e) => setMaxStops(Number(e.target.value))}
                    className="qs-input"
                    disabled={!includeStops}
                  >
                    <option value={1}>{t("stopsOne")}</option>
                    <option value={2}>{t("stopsTwo")}</option>
                  </select>
                </label>
                <label className="field">
                  {t("riskAllowed")}
                  <select
                    name="risk_filter"
                    autoComplete="off"
                    value={riskFilter}
                    onChange={(e) => setRiskFilter(e.target.value as "all" | "low" | "medium" | "high")}
                    className="qs-input"
                  >
                    <option value="all">{t("riskAll")}</option>
                    <option value="low">{t("riskLow")}</option>
                    <option value="medium">{t("riskMedium")}</option>
                    <option value="high">{t("riskHigh")}</option>
                  </select>
                </label>
                <label className="field">
                  {t("bufferMin")}
                  <input
                    type="number"
                    min={0}
                    step={1}
                    name="buffer_min"
                    autoComplete="off"
                    value={bufferMin}
                    onChange={(e) => setBufferMin(e.target.value)}
                    placeholder="45"
                    className="qs-input"
                    disabled={!includeStops}
                    aria-invalid={Boolean(fieldErrors.buffer_min)}
                  />
                  {fieldErrors.buffer_min ? <small className="qs-error">{fieldErrors.buffer_min}</small> : null}
                  <small className="muted">{t("bufferMinHint")}</small>
                </label>
                <div className="field">
                  <span>{t("excludeOrigins")}</span>
                  <div className="qs-chip-input">
                    {excludeOrigins.map((iata) => (
                      <button
                        key={`origin-${iata}`}
                        type="button"
                        className="qs-chip"
                        onClick={() => removeChip(iata, excludeOrigins, setExcludeOrigins)}
                        aria-label={t("ariaRemoveFilter").replace("{value}", iata)}
                      >
                        {iata} <span aria-hidden="true">x</span>
                      </button>
                    ))}
                    <input
                      name="exclude_origins"
                      autoComplete="off"
                      value={excludeOriginInput}
                      onChange={(e) => setExcludeOriginInput(e.target.value.toUpperCase())}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === "," || e.key === " ") {
                          e.preventDefault();
                          addChip(excludeOriginInput, excludeOrigins, setExcludeOrigins, setExcludeOriginInput);
                        }
                      }}
                      onBlur={() => addChip(excludeOriginInput, excludeOrigins, setExcludeOrigins, setExcludeOriginInput)}
                      placeholder="MAD, BCN"
                      className="qs-input"
                    />
                  </div>
                </div>
                <div className="field">
                  <span>{t("excludeDestinations")}</span>
                  <div className="qs-chip-input">
                    {excludeDestinations.map((iata) => (
                      <button
                        key={`dest-${iata}`}
                        type="button"
                        className="qs-chip"
                        onClick={() => removeChip(iata, excludeDestinations, setExcludeDestinations)}
                        aria-label={t("ariaRemoveFilter").replace("{value}", iata)}
                      >
                        {iata} <span aria-hidden="true">x</span>
                      </button>
                    ))}
                    <input
                      name="exclude_destinations"
                      autoComplete="off"
                      value={excludeDestinationInput}
                      onChange={(e) => setExcludeDestinationInput(e.target.value.toUpperCase())}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === "," || e.key === " ") {
                          e.preventDefault();
                          addChip(excludeDestinationInput, excludeDestinations, setExcludeDestinations, setExcludeDestinationInput);
                        }
                      }}
                      onBlur={() => addChip(excludeDestinationInput, excludeDestinations, setExcludeDestinations, setExcludeDestinationInput)}
                      placeholder="DUB, LIS"
                      className="qs-input"
                    />
                  </div>
                </div>
              </div>
              {includeStops ? (
                <div className="qs-warning qs-warning-warm">
                  {t("selfConnectWarning")}
                </div>
              ) : null}
              </div>
            </details>
          </div>
          <div className="qs-filter-actions">
            <button type="button" className="btn-ghost qs-reset-all" onClick={clearAllFilters} disabled={activeChips.length === 0}>
              {t("resetAll")}
            </button>
            <button type="button" className="btn-ghost" onClick={applyPreferences} disabled={!pref}>
              {t("resetPrefs")}
            </button>
          </div>
        </aside>
        <div className="qs-workspace-grid">
        <section className="panel panel-soft qs-results-panel">
          <div className="qs-results-stagehead">
            <div className="qs-results-stagehead__copy">
              <span className="qs-results-stagehead__eyebrow">{t("searchSummaryTitle")}</span>
              <h2>{hasSearched ? `${visibleResults.length} ${t("results")}` : t("searchReadyTitle")}</h2>
              <p>
                {executedCriteria
                  ? `${executedCriteria.route} - ${executedCriteria.dateLabel}`
                  : `${summaryTrip} - ${summaryMeta}`}
              </p>
            </div>
            <div className="qs-results-stagehead__meta">
              <span className="qs-summary-chip">{summaryFlex}</span>
              <span className="qs-summary-chip">{showDegradedState ? t("degradedBadge") : summaryStrict}</span>
              {pendingSearchChanges ? (
                <span className="qs-summary-chip qs-results-stagehead__chip-warning">{t("pendingChangesTitle")}</span>
              ) : null}
            </div>
          </div>
          <div className="qs-results-toolbar" ref={resultsToolbarRef} tabIndex={-1}>
            <div className="qs-results-summary">
              <strong>{visibleResults.length}</strong> {t("results")}
              {hasSearched ? <span className="muted"> - {t("orderedBy")} {sortLabel[sortBy]}</span> : null}
              {searchMeta?.truncated ? <span className="chip chip-warn">{t("truncated")}</span> : null}
              {hasSearched ? (
                <span className="qs-freshness-global">
                  {searchMeta?.freshness_ts ? (
                    <span>
                      {t("freshnessLabel")} {formatFreshness(searchMeta.freshness_ts)}
                    </span>
                  ) : (
                    <span className="qs-freshness-global-unknown">
                      {t("freshnessUnavailableGlobal")}
                      <span
                        className="qs-tip"
                        tabIndex={0}
                        role="img"
                        aria-label={t("freshnessUnavailableTooltip")}
                        data-tip={t("freshnessUnavailableTooltip")}
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.7" />
                          <path d="M12 8v.2M12 11v5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                        </svg>
                      </span>
                    </span>
                  )}
                </span>
              ) : null}

            </div>
            <div className="qs-results-controls">
              {pendingSearchChanges ? (
                <button type="button" className="btn-search qs-apply-sticky" onClick={runSearch}>
                  {t("applyAndSearch")}
                </button>
              ) : null}
              <label className="field">
                {t("orderBy")}
                <select
                  name="sort_by"
                  autoComplete="off"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as "ranking" | "price" | "duration" | "risk" | "freshness")}
                  className="qs-input"
                >
                  <option value="ranking">{t("sortRanking")}</option>
                  <option value="price">{t("sortPrice")}</option>
                  <option value="duration">{t("sortDuration")}</option>
                  <option value="risk">{t("sortRisk")}</option>
                  <option value="freshness">{t("sortFreshness")}</option>
                </select>
              </label>
              <details
                className="qs-explain-popover qs-how-order"
                ref={explainPopoverRef}
                onToggle={(event) => setIsExplainOpen(event.currentTarget.open)}
              >
                <summary className={`qs-explain-trigger qs-results-explain-chip qs-how-order__summary ${showDegradedState ? "qs-degraded-chip" : ""}`} role="button" aria-label={t("explainTitle")} ref={explainTriggerRef}>
                  <span aria-hidden="true">ⓘ</span> {explainChipLabel}
                </summary>
                <div className="panel panel-soft qs-explain-panel qs-how-order__panel">
                  <div className="panel-header">
                    <h2>{t("explainTitle")}</h2>
                    <span className="muted">{t("explainSubtitle")}</span>
                  </div>
                  <div className="qs-explain-grid">
                    <div>
                      <strong>{t("explainPriceTitle")}</strong>
                      <p>{t("explainPrice")}</p>
                    </div>
                    <div>
                      <strong>{t("explainTimeTitle")}</strong>
                      <p>{t("explainTime")}</p>
                    </div>
                    <div>
                      <strong>{t("explainAltTitle")}</strong>
                      <p>{t("explainAlt")}</p>
                    </div>
                    <div>
                      <strong>{t("explainRiskTitle")}</strong>
                      <p>{t("explainRisk")}</p>
                    </div>
                  </div>
                  <div className="qs-explain-note">
                    <span>{t("detailsNote")}</span>
                  </div>
                  {selectedResult ? (
                    <div className="qs-explain-selected">
                      <strong>{selectedResult.origin} {" → "} {selectedResult.destination}</strong>
                      <span>{t("score")}: {selectedResult.ranking_score ? formatScore(selectedResult.ranking_score) : "--"}</span>
                      <span>{t("riskAllowed")}: {formatRiskLabel(selectedResult.risk_label)}</span>
                      <span>{t("freshnessLabel")} {formatFreshness(selectedResult.freshness_ts)}</span>
                    </div>
                  ) : null}
                </div>
              </details>
              <button
                type="button"
                className={`btn-ghost ${compactView ? "is-active" : ""}`}
                onClick={() => {
                  setCompactView((prev) => {
                    const next = !prev;
                    trackEvent("quicksearch_compact_toggled", { compact: next });
                    return next;
                  });
                }}
              >
                {compactView ? t("toolbarExpanded") : t("toolbarCompact")}
              </button>
              <button
                type="button"
                className="btn-ghost qs-filters-toggle"
                aria-expanded={isFiltersOpen}
                aria-controls="qs-filters-drawer"
                aria-label={t("ariaFiltersToggle").replace("{count}", String(activeChips.length))}
                ref={filtersToggleRef}
                onClick={() => {
                  if (isFiltersOpen) {
                    closeFiltersDrawer();
                  } else {
                    trackEvent("quicksearch_filters_opened", { active_filters: activeChips.length });
                    setIsFiltersOpen(true);
                  }
                }}
              >
                {t("ariaFiltersToggle").replace("{count}", String(activeChips.length))}
              </button>
            </div>
          </div>

          {activeChips.length > 0 ? (
            <div className="qs-active-chips">
              <span className="muted">{t("toolbarActiveFilters")}</span>
              <button type="button" className="btn-ghost qs-reset-all-inline" onClick={clearAllFilters}>
                {t("resetAll")}
              </button>
              {activeChips.map((chip) => (
                <button
                  key={chip.id}
                  type="button"
                  className="qs-chip"
                  onClick={chip.onClear}
                  aria-label={t("ariaRemoveFilter").replace("{value}", chip.label)}
                >
                  {chip.label} <span aria-hidden="true">x</span>
                </button>
              ))}
            </div>
          ) : null}

          <QuickSearchLoadingProgress
            show={showLoader}
            loadingVisualHold={loadingVisualHold}
            loadingAria={t("loadingAria")}
            loadingPhaseLabel={loadingPhaseLabel}
            progressPercent={progressPercent}
            loadingSubcheckTitle={t("loadingSubcheckTitle")}
            loadingSubchecks={loadingSubchecks}
            loadingSubcheckDone={t("loadingSubcheckDone")}
            loadingSubcheckActive={t("loadingSubcheckActive")}
            prefersReducedMotion={prefersReducedMotion}
            boardedCount={boardedCount}
            showBoarding={showBoarding}
            boardingPassengers={boardingPassengers}
            loadingTitle={t("loadingTitle")}
            loadingText={t("loadingText")}
          />
          {relaxPreviewOpen ? (
            <section className="panel panel-soft section-gap-sm" aria-live="polite">
              <div className="panel-header">
                <h3>{t("relaxPreviewTitle")}</h3>
                <span className="muted">{t("relaxPreviewImpact")}</span>
              </div>
              <div className="qs-summary-detail-row">
                {relaxPreviewChanges.length > 0 ? (
                  relaxPreviewChanges.map((item) => (
                    <span key={item.id} className="qs-summary-chip">
                      {item.label}: {item.before} → {item.after}
                    </span>
                  ))
                ) : (
                  <span className="muted">{t("relaxPreviewNoChanges")}</span>
                )}
              </div>
              <div className="qs-results-controls">
                <button type="button" className="btn-search" onClick={applyRelaxPreview}>{t("relaxPreviewConfirm")}</button>
                <button type="button" className="btn-ghost" onClick={cancelRelaxPreview}>{t("relaxPreviewCancel")}</button>
              </div>
            </section>
          ) : null}

          <QuickSearchStatePanels
            searchState={searchState}
            rateLimitSeconds={rateLimitSeconds}
            searchError={searchError}
            emptyStateMainTitle={emptyStateMainTitle}
            locale={locale}
            zeroResultCauses={zeroResultCauses}
            visibleZeroResultCauses={visibleZeroResultCauses}
            canExpandZeroResultCauses={canExpandZeroResultCauses}
            emptyCausesExpanded={emptyCausesExpanded}
            zeroResultActions={zeroResultActions}
            onToggleEmptyCauses={() => setEmptyCausesExpanded((prev) => !prev)}
            onRelaxAction={onZeroResultRelaxAction}
            onRunSearch={runSearch}
            onEmptyCta={openRelaxPreview}
            t={t}
          />
          <QuickSearchResultsList
            visibleResults={visibleResults}
            compactView={compactView}
            expandedRows={expandedRows}
            openRowMenuId={openRowMenuId}
            deeplinkUrl={deeplinkUrl}
            hiddenHighRiskResults={hiddenHighRiskResults}
            showHighRisk={showHighRisk}
            origin={origin}
            destination={destination}
            radiusKm={radiusKm}
            departAfter={departAfter}
            departBefore={departBefore}
            localeTag={localeTag}
            getCopyPayload={getCopyPayload}
            rowMenuTriggerRefs={rowMenuTriggerRefs}
            t={t}
            formatMoney={formatMoney}
            formatScore={formatScore}
            formatRiskLabel={formatRiskLabel}
            formatFreshness={formatFreshness}
            formatMinutes={formatMinutes}
            resultKey={resultKey}
            getResultTags={getResultTags}
            addToWatchlist={addToWatchlist}
            setExpandedRows={setExpandedRows}
            setSelectedResultId={setSelectedResultId}
            setOpenRowMenuId={setOpenRowMenuId}
            setCopyModalPayload={setCopyModalPayload}
            setCopyModalOpen={setCopyModalOpen}
            closeRowMenu={closeRowMenu}
            onTrackOpenRyanair={trackOpenRyanair}
            onToggleHighRisk={() => setShowHighRisk((prev) => !prev)}
            onTrackRowOverflow={(rowId) => trackEvent("quicksearch_row_overflow_opened", { row_id: rowId })}
            onTrackCopyParams={(rowId) => trackEvent("quicksearch_row_copy_params_clicked", { row_id: rowId })}
          />

        </section>
        <aside className="qs-context-rail">
          {pendingSearchChanges ? (
            <div className="notice notice-warning qs-pending-changes" role="status" aria-live="polite">
              <strong>{t("pendingChangesTitle")}</strong>
              <span>{t("pendingChangesBody")}</span>
              <button type="button" className="btn-search" onClick={runSearch}>
                {t("applyAndSearch")}
              </button>
            </div>
          ) : null}
          <section className="panel panel-soft qs-search-summary-compact" aria-live="polite">
            <div className="panel-header">
              <h3>{t("searchSummaryTitle")}</h3>
            </div>
            <div className="qs-summary-detail-row">
              <span className="qs-summary-chip">{summaryTrip}</span>
              <span className="qs-summary-chip">{summaryMeta}</span>
              <span className="qs-summary-chip">{summaryFlex}</span>
              <span className="qs-summary-chip">{summaryStrict}</span>
            </div>
            {executedCriteria ? (
              <div className="qs-context-applied">
                <strong>{t("appliedCriteriaTitle")}:</strong>
                <span>{executedCriteria.route}</span>
                <span>{executedCriteria.dateLabel}</span>
                <span>{executedCriteria.paxLabel}</span>
              </div>
            ) : null}
          </section>
          <details
            className="panel panel-soft qs-info-stack"
            open={infoExpanded}
            onToggle={(event) => {
              const open = event.currentTarget.open;
              setInfoExpanded(open);
              if (open) {
                trackEvent("quicksearch_info_panel_opened", { items_count: infoItemsCount });
              }
            }}
          >
            <summary className="qs-info-summary">
              <strong>{t("infoSectionTitle")}</strong>
              <span className="qs-info-count">{infoItemsCount}</span>
            </summary>
            <div className="qs-info-body">
              {warningSeverity.critical.length > 0 ? (
                <div className="notice notice-compact notice-error qs-warning-grouped qs-warning-grouped-critical">
                  <div className="qs-warning-grouped-head">
                    <strong>{warningProblemTitle}</strong>
                    <span className="qs-warning-grouped-count">{warningSeverity.critical.length}</span>
                    <button
                      type="button"
                      className="btn-ghost btn-compact"
                      aria-expanded={criticalWarningsExpanded}
                      aria-controls="qs-warning-critical-details"
                      onClick={() => setCriticalWarningsExpanded((prev) => !prev)}
                    >
                      {criticalWarningsExpanded ? warningDetailCloseLabel : warningDetailOpenLabel}
                    </button>
                  </div>
                  {groupedCriticalWarnings.length > 0 ? (
                    <div className="qs-warning-grouped-summary" aria-live="polite">
                      {groupedCriticalWarnings.map((group) => (
                        <span key={group.message} className="qs-warning-group-chip">
                          {group.message} ({group.count})
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {criticalWarningsExpanded ? (
                    <div id="qs-warning-critical-details" className="qs-warning-grouped-details">
                      <ul>
                        {warningSeverity.critical.map((notice, idx) => (
                          <li key={`${notice}-${idx}`}>{notice}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : null}
              {filtersMeta?.relaxed && filtersMeta.relaxed.length > 0 ? (
                <div className="notice notice-compact notice-success">
                  {t("filtersRelaxed")}: {filtersMeta.relaxed.join(", ")}.
                </div>
              ) : null}
              {sourcesSummary.entries.length > 0 ? (
                <details
                  className="qs-sources-popover"
                  onToggle={(event) => {
                    if (!event.currentTarget.open) return;
                    trackEvent("quicksearch_sources_detail_opened", { sources_count: sourcesSummary.entries.length });
                  }}
                >
                  <summary className="qs-sources-trigger" aria-label={t("sourcesDetailAria")}>
                    <span>{t("sourcesLabel")}: {sourcesSummary.preview || `${t("sourceUnknown")} (0)`}</span>
                    <span className="qs-sources-detail-link">{t("viewDetail")}</span>
                  </summary>
                  <div className="panel panel-soft qs-sources-panel">
                    <strong>{t("sourcesDetailTitle")}</strong>
                    <ul>
                      {sourcesSummary.entries.map(([source, count]) => (
                        <li key={`${source}-${count}`}>
                          <span>{source}</span>
                          <strong>{count}</strong>
                        </li>
                      ))}
                    </ul>
                  </div>
                </details>
              ) : null}
              {warningSeverity.neutral.length > 0 ? (
                <div className="notice notice-compact notice-info qs-warning-grouped qs-warning-grouped-neutral">
                  <div className="qs-warning-grouped-head">
                    <strong>{warningGroupedTitle}</strong>
                    <span className="qs-warning-grouped-count">{warningSeverity.neutral.length}</span>
                    <button
                      type="button"
                      className="btn-ghost btn-compact"
                      aria-expanded={warningsExpanded}
                      aria-controls="qs-warning-details"
                      onClick={() => setWarningsExpanded((prev) => !prev)}
                    >
                      {warningsExpanded ? warningDetailCloseLabel : warningDetailOpenLabel}
                    </button>
                  </div>
                  {groupedNeutralWarnings.length > 0 ? (
                    <div className="qs-warning-grouped-summary" aria-live="polite">
                      {groupedNeutralWarnings.map((group) => (
                        <span key={group.message} className="qs-warning-group-chip">
                          {group.message} ({group.count})
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {warningsExpanded ? (
                    <div id="qs-warning-details" className="qs-warning-grouped-details">
                      <ul>
                        {warningSeverity.neutral.map((notice, idx) => (
                          <li key={`${notice}-${idx}`}>{notice}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : null}
              {showDegradedState ? (
                <p className="panel-note qs-degraded-inline">
                  <strong>{t("degradedBadge")}</strong>: {t("degradedHint")}
                  {searchMeta?.freshness_ts ? (
                    <span> · {t("lastData")}: {new Date(searchMeta.freshness_ts).toLocaleTimeString(localeTag, { hour: "2-digit", minute: "2-digit" })}</span>
                  ) : null}
                </p>
              ) : null}
              {weatherMessage ? <div className="notice notice-compact notice-warning">{weatherMessage}</div> : null}
              <p className="panel-note qs-disclaimer">
                {t("disclaimer")} {t("disclaimerWatchlistCta")}
              </p>
            </div>
          </details>
        </aside>
        </div>
      </div>
      {copyModalOpen ? (
        <div className="airport-modal-overlay" onClick={() => setCopyModalOpen(false)}>
          <section className="modal-card" role="dialog" aria-modal="true" aria-label={t("deepLinkModalTitle")} onClick={(event) => event.stopPropagation()}>
            <div className="modal-card-header">
              <h3>{t("deepLinkModalTitle")}</h3>
              <button type="button" className="btn-ghost" onClick={() => setCopyModalOpen(false)}>
                {t("pickClose")}
              </button>
            </div>
            <p className="panel-note">{t("deepLinkModalBody")}</p>
            <textarea
              className="qs-input qs-copy-area"
              name="deeplink_payload"
              autoComplete="off"
              value={copyModalPayload}
              readOnly
              rows={5}
            />
            <div className="modal-card-actions">
              <button
                type="button"
                className="btn-primary"
                onClick={async () => {
                  await navigator.clipboard.writeText(copyModalPayload);
                  setToast({ message: t("deepLinkCopied") });
                  setCopyModalOpen(false);
                }}
              >
                {t("deepLinkCopy")}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {toast ? (
        <div className="notice notice-success qs-toast">
          <span>{toast.message}</span>
          {toast.actionLabel && toast.onAction ? (
            <button type="button" className="btn-ghost" onClick={toast.onAction}>
              {toast.actionLabel}
            </button>
          ) : null}
          <button type="button" className="btn-ghost" aria-label={t("pickClose")} onClick={() => setToast(null)}>x</button>
        </div>
      ) : null}

      {deepLinkError ? <div className="notice notice-error section-gap-sm">{deepLinkError}</div> : null}
      {message ? (
        <div className={`notice section-gap ${messageType === "success" ? "notice-success" : "notice-error"}`}>
          {message}
        </div>
      ) : null}

      </QuickSearchResultsWorkspace>
      ) : (
        <section className="panel panel-soft section-gap-sm" aria-live="polite">
          <div className="panel-header">
            <h2>{t("searchReadyTitle")}</h2>
            <span className="muted">{t("searchReadyHint")}</span>
          </div>
        </section>
      )}

      {airportPickerModal}

      {(weatherOrigin || weatherDestination) ? (
        <details className="panel panel-soft section-gap qs-secondary-weather">
          <summary className="qs-info-summary">
            <strong>{t("weatherTitle")}</strong>
            <span className="muted">{t("viewDetail")}</span>
          </summary>
          <div className="panel-header">
            <h2>{t("weatherTitle")}</h2>
            <span className="muted">{t("weatherSubtitle")}</span>
          </div>
          <div className="weather-grid">
            {weatherOrigin ? (
              <div className="weather-group">
                <h3>
                  {weatherOrigin.city} ({weatherOrigin.iata}) - {t("weatherOrigin")}
                </h3>
                <div className="weather-days">
                  {weatherOrigin.days.map((day) => {
                    const dateLabel = new Date(day.date).toLocaleDateString(localeTag, { weekday: "short", day: "2-digit", month: "short" });
                    return (
                      <div key={`${weatherOrigin.iata}-${day.date}`} className="cardm">
                        <div className="card">
                          <div className="weather">
                            <strong>{dateLabel}</strong>
                            <div className="main">{Math.round(day.tempMax)} C</div>
                            <div className="mainsub">{Math.round(day.tempMin)} C</div>
                          </div>
                          <div className="upper">
                            <span>{day.description}</span>
                            <span>{day.precipProb ?? 0}%</span>
                          </div>
                          <div className="humiditytext">precip</div>
                          <div className="airtext">clima</div>
                        </div>
                        <div className="card2">
                          <div className="lower">
                            <div className="aqi">Max {Math.round(day.tempMax)} C</div>
                            <div className="realfeel">Min {Math.round(day.tempMin)} C</div>
                            <div>Prob {day.precipProb ?? 0}%</div>
                          </div>
                        </div>
                        <div className="card3">{t("weatherDepart")}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}
            {weatherDestination ? (
              <div className="weather-group">
                <h3>
                  {weatherDestination.city} ({weatherDestination.iata}) - {t("weatherDestination")}
                </h3>
                <div className="weather-days">
                  {weatherDestination.days.map((day) => {
                    const dateLabel = new Date(day.date).toLocaleDateString(localeTag, { weekday: "short", day: "2-digit", month: "short" });
                    return (
                      <div key={`${weatherDestination.iata}-${day.date}`} className="cardm">
                        <div className="card">
                          <div className="weather">
                            <strong>{dateLabel}</strong>
                            <div className="main">{Math.round(day.tempMax)} C</div>
                            <div className="mainsub">{Math.round(day.tempMin)} C</div>
                          </div>
                          <div className="upper">
                            <span>{day.description}</span>
                            <span>{day.precipProb ?? 0}%</span>
                          </div>
                          <div className="humiditytext">precip</div>
                          <div className="airtext">clima</div>
                        </div>
                        <div className="card2">
                          <div className="lower">
                            <div className="aqi">Max {Math.round(day.tempMax)} C</div>
                            <div className="realfeel">Min {Math.round(day.tempMin)} C</div>
                            <div>Prob {day.precipProb ?? 0}%</div>
                          </div>
                        </div>
                        <div className="card3">{t("weatherArrive")}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>
        </details>
      ) : null}

    </main>
  );
}
