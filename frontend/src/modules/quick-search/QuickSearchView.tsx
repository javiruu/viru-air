"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { Download } from "lucide-react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { apiFetch, apiFetchWithStatus, LONG_RUNNING_API_BASE } from "@/modules/shared/api";
import type { ApiError } from "@/modules/shared/api";
import { buildJsonExportFilename, downloadJson } from "@/modules/shared/jsonExport";
import { getQuickSearchCopy } from "@/modules/shared/quickSearchCopy";
import { useFtueHint } from "@/lib/ftue";
import { trackUxEvent } from "@/lib/uxTracking";
import { trackEvent } from "@/modules/shared/analytics";
import { formatCurrency, formatNumber } from "@/modules/shared/format";
import { buildDateRange } from "@/modules/quick-search/utils";
import {
  buildAppliedCriteriaSignature,
  buildCriteriaSignature,
  parseNumericInput,
} from "@/modules/quick-search/searchCriteria";
import {
  QUICK_SEARCH_PROVIDER_ERROR_WARNING_CODES,
  QUICK_SEARCH_PROVIDER_PARTIAL_INLINE_WARNING_CODES,
  QUICK_SEARCH_PROVIDER_TOTAL_OUTAGE_WARNING_CODES,
} from "@/modules/quick-search/quick-search-warning-codes";
import {
  clampQuickSearchFlexDays,
  formatQuickSearchFlexSummary,
  getQuickSearchFlexPreset,
} from "@/modules/quick-search/flexibility";
import {
  clampQuickSearchRadius,
  mergeQuickSearchIataTokens,
  parseQuickSearchIataTokens,
  QUICK_SEARCH_RADIUS_DEFAULT,
} from "@/modules/quick-search/filterUtils";
import { resolveQuickSearchPreferenceDefaults } from "@/modules/quick-search/preferences";
import {
  buildRecentAirportSuggestions,
  forgetRecentAirport,
  migrateRecentAirports,
  readRecentAirports,
  rememberRecentAirport,
  RECENT_AIRPORTS_ORIGIN_KEY,
  RECENT_AIRPORTS_DESTINATION_KEY,
  writeRecentAirports,
} from "@/modules/quick-search/recentAirports";

function isTransientChunkLoadError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  return /ChunkLoadError|Loading chunk|Failed to fetch dynamically imported module/i.test(error.message);
}

function retryQuickSearchChunk<T>(loader: () => Promise<T>): Promise<T> {
  return loader().catch((error: unknown) => {
    if (!isTransientChunkLoadError(error)) {
      throw error;
    }
    return new Promise<T>((resolve, reject) => {
      setTimeout(() => {
        loader().then(resolve).catch(reject);
      }, 250);
    });
  });
}

const QuickSearchLoadingProgress = dynamic(() =>
  retryQuickSearchChunk(() =>
    import("@/modules/quick-search/components/QuickSearchLoadingProgress")
  ).then((m) => m.QuickSearchLoadingProgress),
  { ssr: false },
);
const QuickSearchResultsList = dynamic(() =>
  retryQuickSearchChunk(() =>
    import("@/modules/quick-search/components/QuickSearchResultsList")
  ).then((m) => m.QuickSearchResultsList),
  { ssr: false },
);
const QuickSearchSearchForm = dynamic(() =>
  retryQuickSearchChunk(() =>
    import("@/modules/quick-search/components/QuickSearchSearchForm")
  ).then((m) => m.QuickSearchSearchForm),
);
const QuickSearchStatePanels = dynamic(() =>
  retryQuickSearchChunk(() =>
    import("@/modules/quick-search/components/QuickSearchStatePanels")
  ).then((m) => m.QuickSearchStatePanels),
);
import {
  buildQuickSearchCanonicalPayload,
  buildQuickSearchExpectedSignatures,
  prepareQuickSearchRequest,
  type QuickSearchCanonicalPayload,
} from "@/modules/quick-search/api/buildQuickSearchRequest";
import { buildQuickSearchSaveResultPayload } from "@/modules/quick-search/api/buildSaveResultPayload";
import {
  createEmptyFareComparisonProfile,
  type FareComparisonProfile,
} from "@/modules/shared/fareComparison";
import { getOfficialRyanairRouteDeepLink } from "@/modules/quick-search/api/quickSearchDeepLinks";
import {
  buildQuickSearchExportPagePayload,
  buildQuickSearchExportPayload,
  type QuickSearchExportCriteria,
} from "@/modules/quick-search/exportQuickSearchJson";
import { QuickSearchDatePicker } from "@/modules/quick-search/components/QuickSearchDatePicker";
import { QuickSearchResultsWorkspace } from "@/modules/quick-search/components/QuickSearchResultsWorkspace";
import { QuickSearchSummaryChips, type QuickSearchSummaryChip } from "@/modules/quick-search/components/QuickSearchSummaryChips";
import { QuickSearchAdvancedDrawer } from "@/modules/quick-search/components/QuickSearchAdvancedDrawer";
import { QuickSearchNearbyBand } from "@/modules/quick-search/components/QuickSearchNearbyBand";
import { QuickSearchAdditionalAirports } from "@/modules/quick-search/components/QuickSearchAdditionalAirports";
import { PopularDestinationsChips } from "@/modules/community-routes/PopularDestinationsChips";
import {
  buildRouteSeedList,
  type QuickSearchAdditionalAirport,
} from "@/modules/quick-search/multiple-airports";

import {
  AirportIataEntry,
  CountryAirports,
  DeepLinkResponse,
  Pref,
  QuickSearchCalendarAggregationMode,
  QuickSearchCalendarBucketMode,
  QuickSearchCalendarDayHint,
  QuickSearchCalendarGuidelineThresholds,
  QuickSearchCalendarHintsResponse,
  QuickSearchCalendarScopeMode,
  QuickSearchAutocompleteField,
  QuickSearchField,
  QuickSearchFieldErrors,
  QuickSearchLoadingPhase,
  QuickSearchLoadingSubcheckStatus,
  QuickSearchMode,
  QuickSearchSortBy,
  QuickSearchTripType,
  QuickSearchVisibleFiltersState,
  RegionPref,
  SearchResult,
  SearchResponse,
  SearchResponseRaw,
  SummaryHighlightKey,
  ZeroResultRelaxAction,
} from "@/modules/quick-search/types";
import { collectQuickSearchWarningCodes, normalizeQuickSearchResponse } from "@/modules/quick-search/responseNormalizer";
import { getQuickSearchFreshnessPresentation } from "@/modules/quick-search/freshnessPresentation";
import { useQuickSearchMainState } from "@/modules/quick-search/state/useQuickSearchController";
import { getQuickSearchVisualState } from "@/modules/quick-search/state/getQuickSearchVisualState";
import { useQuickSearchLoadingFlow } from "@/modules/quick-search/state/useQuickSearchLoadingFlow";
import { useQuickSearchSide } from "@/modules/quick-search/state/useQuickSearchSide";
import { useQuickSearchWatchlist } from "@/modules/quick-search/state/useQuickSearchWatchlist";
import { useSaveCombination, type SaveResult } from "@/modules/quick-search/state/useSaveCombination";
import { QuickSearchDualWorkspace } from "@/modules/quick-search/components/QuickSearchDualWorkspace";
import { buildDualSearchParams, findCombinationResult } from "@/modules/quick-search/utils-dual";
import { QuickSearchSidePanel } from "@/modules/quick-search/components/QuickSearchSidePanel";
import { QuickSearchCombinedBanner } from "@/modules/quick-search/components/QuickSearchCombinedBanner";
import { QuickSearchProviderBadge } from "@/modules/quick-search/components/QuickSearchProviderBadge";
import type { ProviderSearchStatus } from "@/modules/quick-search/components/QuickSearchLoadingProgress";
import { useQuickSearchScreenState } from "@/modules/quick-search/state/useQuickSearchScreenState";
import { QuickSearchSideViewControls } from "@/modules/quick-search/components/QuickSearchSideViewControls";
import { getPendingActionVisibility } from "@/modules/quick-search/state/pendingActionPolicy";
import { getApiSearchQuery } from "@/modules/shared/cityTranslations";
import { buildAirportSuggestions, normalizeText } from "@/modules/quick-search/airportSuggestions";
import { INITIAL_PROVIDER_SEARCH_STATUSES } from "@/modules/quick-search/providerPresentation";
import { fetchWeather as fetchWeatherApi, isWeatherRangeSupported as isWeatherRangeSupportedCheck } from "@/modules/quick-search/weatherUtils";
import {
  buildResumeSearchSnapshot,
  loadResumeSearchSnapshot,
  saveResumeSearchSnapshot,
} from "@/modules/quick-search/resume-search";
import { buildWatchlistUrl, buildQuickSearchSearchParams, readQuickSearchUrlState } from "@/modules/shared/useRouteState";
import { useEscapeClose } from "@/modules/shared/useEscapeClose";

const RELAX_HIGHLIGHT_BY_ACTION: Record<ZeroResultRelaxAction, Exclude<SummaryHighlightKey, null>> = {
  disable_strict: "strict",
  increase_duration: "duration",
  open_radius_150: "radius",
  clear_exclusions: "exclusions",
  open_date_flex: "date_flex",
  try_plus_1_day: "date_flex",
  open_nearby: "radius",
  max_coverage: "radius",
  open_more_options: "advanced",
};

const IATA_TO_MAC: Record<string, string> = {
  BRU: "BRL",
};

const NON_FATAL_QS_SCOPES = new Set<string>([
  "seed_countries_fallback_used",
  "seed_bootstrap_failed",
  "origin_suggestions_failed",
  "destination_suggestions_failed",
  "origin_code_validation_failed",
  "destination_code_validation_failed",
  "calendar_hints_failed",
  "calendar_hints_exception",
  "calendar_hints_return_failed",
  "calendar_hints_return_exception",
]);
const EMPTY_SEARCH_VALIDATION_MESSAGE = "Please enter a search";
const RYANAIR_TOP_CITIES = [
  "Madrid",
  "Barcelona",
  "Dublin",
  "London",
  "Milan",
  "Rome",
  "Paris",
  "Berlin",
  "Lisbon",
  "Porto",
  "Brussels",
  "Amsterdam",
  "Vienna",
  "Prague",
  "Budapest",
  "Warsaw",
  "Athens",
  "Malaga",
  "Palma",
  "Valencia",
];

type QuickSearchCountrySeed = {
  code: string;
  name: string;
  airport_count: number;
};

type ExecutedCriteriaSnapshot = {
  route: string;
  dateLabel: string;
  paxLabel: string;
};

type BulkWatchCreateResponse = {
  status: string;
  created_dates: string[];
  existing_dates: string[];
};

type QuickSearchCountrySeedResponse = {
  items: QuickSearchCountrySeed[];
  count: number;
  source: string;
};

type CalendarHintsCacheEntry = {
  dayHintsByIso: Record<string, QuickSearchCalendarDayHint>;
  scopeMode: QuickSearchCalendarScopeMode;
};

function buildEmptyCalendarHintsCacheEntry(scopeMode: QuickSearchCalendarScopeMode): CalendarHintsCacheEntry {
  return {
    dayHintsByIso: {},
    scopeMode,
  };
}

async function apiFetchWithRetry<T>(
  path: string,
  init?: RequestInit,
  options?: { timeoutMs?: number; maxRetries?: number; apiBase?: string },
): Promise<
  | { ok: true; data: T; status: number; headers: Headers }
  | { ok: false; error: ApiError; status: number; headers: Headers }
> {
  const maxRetries = options?.maxRetries ?? 2;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    if (init?.signal && (init.signal as AbortSignal).aborted) {
      return {
        ok: false,
        status: 0,
        headers: new Headers(),
        error: { status: 0, code: "ABORTED", message: "" },
      };
    }
    if (attempt > 0) {
      await new Promise((r) => setTimeout(r, 1000 * Math.pow(2, attempt - 1)));
      if (init?.signal && (init.signal as AbortSignal).aborted) {
        return {
          ok: false,
          status: 0,
          headers: new Headers(),
          error: { status: 0, code: "ABORTED", message: "" },
        };
      }
    }
    const result = await apiFetchWithStatus<T>(path, init, options);
    if (result.ok) return result;
    if (result.status >= 500 && result.status < 600 && attempt < maxRetries) {
      continue;
    }
    return result;
  }
  throw new Error("apiFetchWithRetry unreachable");
}

function currentMonthIso(): string {
  const now = new Date();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  return `${now.getFullYear()}-${month}`;
}

function currentDateIso(): string {
  const now = new Date();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  const day = `${now.getDate()}`.padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function monthFromDateIso(dateIso: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateIso)) {
    return currentMonthIso();
  }
  return dateIso.slice(0, 7);
}

let _cachedDisplayNames: Intl.DisplayNames | null = null;
let _cachedDisplayNamesLocale = "";

function _getDisplayNames(): Intl.DisplayNames | null {
  if (typeof Intl === "undefined" || typeof Intl.DisplayNames !== "function") return null;
  const locale = typeof navigator !== "undefined" && navigator.language ? navigator.language : "en";
  if (_cachedDisplayNames && _cachedDisplayNamesLocale === locale) return _cachedDisplayNames;
  try {
    _cachedDisplayNames = new Intl.DisplayNames([locale], { type: "region" });
    _cachedDisplayNamesLocale = locale;
    return _cachedDisplayNames;
  } catch {
    return null;
  }
}

function getPageNumbers(current: number, total: number) {
  const pages: (number | string)[] = [];
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    if (current > 3) {
      pages.push("...");
    }
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    if (current < total - 2) {
      pages.push("...");
    }
    pages.push(total);
  }
  return pages;
}

export function QuickSearchView({ mode = "quick-search" }: { mode?: QuickSearchMode }) {
  const router = useRouter();
  const { notify } = useNotificationCenter();
  const expectedQuerySignaturesRef = useRef<Set<string> | null>(null);
  const [seedAirports, setSeedAirports] = useState<AirportIataEntry[]>([]);
  const [seedCountries, setSeedCountries] = useState<QuickSearchCountrySeed[]>([]);
  const [originSuggestions, setOriginSuggestions] = useState<Array<{ iata: string; name: string }>>([]);
  const [destinationSuggestions, setDestinationSuggestions] = useState<Array<{ iata: string; name: string }>>([]);
  const [additionalOrigins, setAdditionalOrigins] = useState<QuickSearchAdditionalAirport[]>([]);
  const [additionalDestinations, setAdditionalDestinations] = useState<QuickSearchAdditionalAirport[]>([]);
  const [additionalFocusEntryId, setAdditionalFocusEntryId] = useState<string | null>(null);
  const [additionalPickerTarget, setAdditionalPickerTarget] = useState<{
    readonly side: "origin" | "destination";
    readonly id: string;
  } | null>(null);
  const additionalAirportIdRef = useRef(0);
  const [countryAirports, setCountryAirports] = useState<AirportIataEntry[]>([]);
  const [, setExecutedCriteria] = useState<ExecutedCriteriaSnapshot | null>(null);
  const [loaderPlannedTotalFlights, setLoaderPlannedTotalFlights] = useState(0);
  const [loaderResolvedTotalFlights, setLoaderResolvedTotalFlights] = useState<number | null>(null);
  const [loaderScopeRoutes, setLoaderScopeRoutes] = useState(0);
  const [loaderScopeDates, setLoaderScopeDates] = useState(0);
  const [isPageChanging, setIsPageChanging] = useState(false);
  // signature of the last successfully executed criteria (used to detect pending changes)
  const [appliedCriteriaSignature, setAppliedCriteriaSignature] = useState<string | null>(null);
  const [countrySearchInput, setCountrySearchInput] = useState("");
  const [calendarVisibleMonth, setCalendarVisibleMonth] = useState<string>(currentMonthIso);
  const [calendarVisibleMonthReturn, setCalendarVisibleMonthReturn] = useState<string>(currentMonthIso);
  const [calendarHintsByKey, setCalendarHintsByKey] = useState<Record<string, CalendarHintsCacheEntry>>({});
  const [calendarHintsByKeyReturn, setCalendarHintsByKeyReturn] = useState<Record<string, CalendarHintsCacheEntry>>({});
  const [calendarHintsLoadingKey, setCalendarHintsLoadingKey] = useState<string | null>(null);
  const [calendarHintsLoadingKeyReturn, setCalendarHintsLoadingKeyReturn] = useState<string | null>(null);
  const [selectedTravelDates, setSelectedTravelDates] = useState<string[]>([]);
  const initialOrigin = "";
  const initialDestination = "";
  const originCodeLookupRef = useRef<string | null>(null);
  const destinationCodeLookupRef = useRef<string | null>(null);
  const randomOriginPlaceholder = useMemo(
    () => RYANAIR_TOP_CITIES[Math.floor(Math.random() * RYANAIR_TOP_CITIES.length)],
    [],
  );
  const randomDestinationPlaceholder = useMemo(
    () => RYANAIR_TOP_CITIES[Math.floor(Math.random() * RYANAIR_TOP_CITIES.length)],
    [],
  );
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const advancedCloseRef = useRef<HTMLButtonElement>(null);
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
    filtersWarningCodes,
    setFiltersWarningCodes,
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
    originRecentAirports,
    setOriginRecentAirports,
    destinationRecentAirports,
    setDestinationRecentAirports,
    originCountryOnly,
    setOriginCountryOnly,
    destinationCountryOnly,
    setDestinationCountryOnly,
    originSelectedCountryCode,
    setOriginSelectedCountryCode,
    destinationSelectedCountryCode,
    setDestinationSelectedCountryCode,
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
    sortBy,
    setSortBy,
    isDegraded,
    setIsDegraded,
    compactView,
    setCompactView,
    expandedRows,
    setExpandedRows,
    selectedResultId,
    setSelectedResultId,
    pref,
    setPref,
    regionPref,
    setRegionPref,
    setPrefBadge,
    deepLink,
    setDeepLink,
    deepLinkError,
    setDeepLinkError,
    copyModalOpen,
    setCopyModalOpen,
    copyModalPayload,
    setCopyModalPayload,
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
    isMobileViewport,
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
    resultsToolbarRef,
    formRef,
    filtersToggleRef,
    explainPopoverRef,
    explainTriggerRef,
    relaxUndoRef,
    lastPickerTriggerRef,
    airportSearchInputRef,
    rowMenuTriggerRefs,
    sourcesShownKeyRef,
    freshnessShownKeyRef,
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
  const addAdditionalAirport = useCallback((side: "origin" | "destination") => {
    additionalAirportIdRef.current += 1;
    const nextEntry: QuickSearchAdditionalAirport = {
      id: `${side}-${additionalAirportIdRef.current}`,
      value: "",
    };
    setAdditionalFocusEntryId(nextEntry.id);
    if (side === "origin") {
      setAdditionalOrigins((current) => [...current, nextEntry]);
    } else {
      setAdditionalDestinations((current) => [...current, nextEntry]);
    }
  }, []);
  const updateAdditionalAirport = useCallback((side: "origin" | "destination", id: string, value: string) => {
    const updateEntries = (current: QuickSearchAdditionalAirport[]) => current.map((entry) => (
      entry.id === id ? { ...entry, value } : entry
    ));
    if (side === "origin") {
      setAdditionalOrigins(updateEntries);
    } else {
      setAdditionalDestinations(updateEntries);
    }
  }, []);
  const removeAdditionalAirport = useCallback((side: "origin" | "destination", id: string) => {
    const removeEntry = (current: QuickSearchAdditionalAirport[]) => current.filter((entry) => entry.id !== id);
    if (side === "origin") {
      setAdditionalOrigins(removeEntry);
    } else {
      setAdditionalDestinations(removeEntry);
    }
    setAdditionalFocusEntryId((current) => current === id ? null : current);
  }, []);
  const searchSubmitInFlightRef = useRef(false);
  const lastQuickSearchPayloadRef = useRef<QuickSearchCanonicalPayload | null>(null);
  const normalizedRadiusKm = clampQuickSearchRadius(radiusKm);
  const minTravelDate = useMemo(() => currentDateIso(), []);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isExportingQuickSearch, setIsExportingQuickSearch] = useState(false);
  const [returnDateTouched, setReturnDateTouched] = useState(false);
  const [resumeWasRestored, setResumeWasRestored] = useState(false);
  const [refreshingResultId, setRefreshingResultId] = useState<string | null>(null);
  const [providerSearchStatuses, setProviderSearchStatuses] = useState<ProviderSearchStatus[]>([]);
  const { isInWatchlist, getWatchId, markAsSaved } = useQuickSearchWatchlist();

  // ── URL state: read search params on mount (Fase URL State) ────────
  const searchParams = useSearchParams();
  const hasRestoredUrlState = useRef(false);
  const hasRestoredResumeSnapshot = useRef(false);
  useEffect(() => {
    if (hasRestoredUrlState.current) return;
    hasRestoredUrlState.current = true;
    const shouldRestoreResume = searchParams.get("resume") === "1";
    const resumeSnapshot = shouldRestoreResume ? loadResumeSearchSnapshot() : null;
    if (resumeSnapshot) {
      hasRestoredResumeSnapshot.current = true;
      setOrigin(resumeSnapshot.origin);
      setDestination(resumeSnapshot.destination);
      setTravelDate(resumeSnapshot.travelDate);
      setReturnDate(resumeSnapshot.returnDate);
      setIsReturn(resumeSnapshot.isReturn);
      setAdults(resumeSnapshot.adults);
      setDaysBefore(resumeSnapshot.daysBefore);
      setDaysAfter(resumeSnapshot.daysAfter);
      setRadiusKm(resumeSnapshot.radiusKm);
      setStrictFilters(resumeSnapshot.strictFilters);
      setDepartAfter(resumeSnapshot.departAfter);
      setDepartBefore(resumeSnapshot.departBefore);
      setIncludeStops(resumeSnapshot.includeStops);
      setMaxStops(resumeSnapshot.maxStops);
      setBufferMin(resumeSnapshot.bufferMin);
      setIncludeNearbyOrigins(resumeSnapshot.includeNearbyOrigins);
      setIncludeNearbyDestinations(resumeSnapshot.includeNearbyDestinations);
      setExcludeOrigins(resumeSnapshot.excludeOrigins);
      setExcludeDestinations(resumeSnapshot.excludeDestinations);
      setPriceMin(resumeSnapshot.priceMin);
      setPriceMax(resumeSnapshot.priceMax);
      setDurationMax(resumeSnapshot.durationMax);
      setSortBy(resumeSnapshot.sortBy);
      setResumeWasRestored(true);
      return;
    }
    const state = readQuickSearchUrlState(searchParams);
    if (state.origin) setOrigin(state.origin);
    if (state.destination) setDestination(state.destination);
    if (state.additionalOrigins.length > 0) {
      setAdditionalOrigins(state.additionalOrigins.map((value) => ({
        id: `origin-${++additionalAirportIdRef.current}`,
        value,
      })));
    }
    if (state.additionalDestinations.length > 0) {
      setAdditionalDestinations(state.additionalDestinations.map((value) => ({
        id: `destination-${++additionalAirportIdRef.current}`,
        value,
      })));
    }
    if (state.travelDate) setTravelDate(state.travelDate);
    if (state.returnDate) setReturnDate(state.returnDate);
    if (state.isReturn) setIsReturn(true);
    if (state.adults !== 1) setAdults(state.adults);
    if (state.flexBefore) { setDaysBefore(state.flexBefore); }
    if (state.flexAfter) { setDaysAfter(state.flexAfter); }
    if (state.radius !== 150) setRadiusKm(state.radius);
    if (!state.strict) setStrictFilters(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // ── URL state: persist form state to URL on change (Fase URL State) ─
  const qsUrlRef = useRef("");
  const qsUrlTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!hasRestoredUrlState.current) return;
    // Debounce 300ms: avoid router.replace on every keystroke
    if (qsUrlTimeoutRef.current) clearTimeout(qsUrlTimeoutRef.current);
    qsUrlTimeoutRef.current = setTimeout(() => {
      const qs = buildQuickSearchSearchParams({
        origin,
        destination,
        additionalOrigins: additionalOrigins.map((entry) => entry.value),
        additionalDestinations: additionalDestinations.map((entry) => entry.value),
        travelDate,
        returnDate,
        isReturn,
        adults,
        flexBefore: daysBefore,
        flexAfter: daysAfter,
        radius: radiusKm,
        strict: strictFilters,
      });
      if (qs === qsUrlRef.current) return;
      qsUrlRef.current = qs;
      const url = `/quick-search${qs ? `?${qs}` : ""}`;
      router.replace(url, { scroll: false });
    }, 300);
    return () => {
      if (qsUrlTimeoutRef.current) clearTimeout(qsUrlTimeoutRef.current);
    };
  }, [origin, destination, additionalOrigins, additionalDestinations, travelDate, returnDate, isReturn, adults, daysBefore, daysAfter, radiusKm, strictFilters, router]);

  // ── Dual-mode hooks (Fase 6) ───────────────────────────────────────
  const outboundSide = useQuickSearchSide("outbound");
  const returnSide = useQuickSearchSide("return");
  const saveCombination = useSaveCombination();
  const [outboundFareProfile, setOutboundFareProfile] = useState(() => createEmptyFareComparisonProfile(adults));
  const [returnFareProfile, setReturnFareProfile] = useState(() => createEmptyFareComparisonProfile(adults));
  const pendingCombinationResultsRef = useRef<{ outbound: SearchResult; return: SearchResult } | null>(null);
  const submittedRouteSeedsRef = useRef<{ readonly origin: string[]; readonly destination: string[] }>({
    origin: [],
    destination: [],
  });
  const defaultSideViewState = useMemo<QuickSearchVisibleFiltersState>(() => ({
    priceMin: "",
    priceMax: "",
    durationMax: "",
    sortBy: "price",
  }), []);
  const [outboundViewState, setOutboundViewState] = useState<QuickSearchVisibleFiltersState>(() => ({
    priceMin: "",
    priceMax: "",
    durationMax: "",
    sortBy: "price",
  }));
  const [returnViewState, setReturnViewState] = useState<QuickSearchVisibleFiltersState>(() => ({
    priceMin: "",
    priceMax: "",
    durationMax: "",
    sortBy: "price",
  }));
  const [dualHoverSide, setDualHoverSide] = useState<"outbound" | "return" | null>(null);
  // ── Per-side emptyCausesExpanded (Fase 11) ──────────────────────────
  const [outboundEmptyCausesExpanded, setOutboundEmptyCausesExpanded] = useState(false);
  const [returnEmptyCausesExpanded, setReturnEmptyCausesExpanded] = useState(false);
  // Reset per-side empty causes when exiting dual mode
  // ── Per-side relax action handler (Fase 11) ────────────────────────
  const handleDualRelaxAction = useCallback(
    (action: ZeroResultRelaxAction, side: "outbound" | "return") => {
      // View-only filter change: just update state, no re-search needed
      if (action === "increase_duration") {
        setDurationMax((prev) => {
          const current = Number(prev) || 0;
          return String(Math.max(current + 60, 180));
        });
        return;
      }

      // Search-level filter changes: update state and re-run the search
      if (action === "disable_strict") setStrictFilters(false);
      if (action === "open_radius_150") {
        setIncludeNearbyOrigins(true);
        setIncludeNearbyDestinations(true);
        setRadiusKm(150);
      }
      if (action === "clear_exclusions") {
        setExcludeOrigins([]);
        setExcludeDestinations([]);
        setExcludeOriginInput("");
        setExcludeDestinationInput("");
      }
      if (action === "open_date_flex") {
        setDaysBefore(2);
        setDaysAfter(2);
      }

      // Compute side-specific origin/destination/date (return leg is inverted)
      const sideOrigin = side === "outbound" ? origin : destination;
      const sideDest = side === "outbound" ? destination : origin;
      const sideOriginSeeds = side === "outbound" ? submittedRouteSeedsRef.current.origin : submittedRouteSeedsRef.current.destination;
      const sideDestinationSeeds = side === "outbound" ? submittedRouteSeedsRef.current.destination : submittedRouteSeedsRef.current.origin;
      const sideDate = side === "outbound" ? travelDate : returnDate;
      const targetSide = side === "outbound" ? outboundSide : returnSide;

      const sideParams = buildDualSearchParams({
        origin: sideOriginSeeds.length > 0 ? sideOriginSeeds : sideOrigin,
        destination: sideDestinationSeeds.length > 0 ? sideDestinationSeeds : sideDest,
        travelDate: sideDate,
        flexDaysBefore: action === "open_date_flex" ? 2 : daysBefore,
        flexDaysAfter: action === "open_date_flex" ? 2 : daysAfter,
        radiusKm: action === "open_radius_150" ? 150 : normalizedRadiusKm,
        includeStops,
        includeNearbyOrigins: action === "open_radius_150" ? true : includeNearbyOrigins,
        includeNearbyDestinations: action === "open_radius_150" ? true : includeNearbyDestinations,
        departAfter, departBefore, maxStops,
        excludeOrigins: action === "clear_exclusions" ? [] : excludeOrigins,
        excludeDestinations: action === "clear_exclusions" ? [] : excludeDestinations,
        strictFilters: action === "disable_strict" ? false : strictFilters,
      });
      void targetSide.runSearch(sideParams);
    }, [
      outboundSide, returnSide, origin, destination, travelDate, returnDate,
      daysBefore, daysAfter, normalizedRadiusKm, includeStops,
      includeNearbyOrigins, includeNearbyDestinations, departAfter, departBefore,
      maxStops, excludeOrigins, excludeDestinations, strictFilters,
      setStrictFilters, setDurationMax, setIncludeNearbyOrigins, setIncludeNearbyDestinations,
      setRadiusKm, setExcludeOrigins, setExcludeDestinations, setExcludeOriginInput,
      setExcludeDestinationInput, setDaysBefore, setDaysAfter,
    ],
  );
  const copy = useMemo(
    () => getQuickSearchCopy(regionPref?.language ?? pref?.language),
    [regionPref?.language, pref?.language],
  );
  const { locale, localeTag, t, tWarn } = copy;
  const resumableRouteLabel = useMemo(() => {
    if (!origin || !destination) return "";
    return `${origin} -> ${destination}`;
  }, [destination, origin]);
  const resumableDetail = useMemo(() => {
    if ((daysBefore > 0 || daysAfter > 0) && (includeNearbyOrigins || includeNearbyDestinations)) {
      return t("resumeDetailFlexNearby");
    }
    if (daysBefore > 0 || daysAfter > 0) {
      return t("resumeDetailFlex");
    }
    if (includeNearbyOrigins || includeNearbyDestinations) {
      return t("resumeDetailNearby");
    }
    if (results.length > 0) {
      return t("resumeDetailResults", { count: results.length });
    }
    return t("resumeDetailBasic");
  }, [daysAfter, daysBefore, includeNearbyDestinations, includeNearbyOrigins, results.length, t]);
  const resumableSummary = useMemo(() => {
    if (!resumableRouteLabel) return "";
    if (isReturn) {
      return t("resumeSummaryRoundTrip", { route: resumableRouteLabel });
    }
    return t("resumeSummaryRoute", { route: resumableRouteLabel });
  }, [isReturn, resumableRouteLabel, t]);
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
    if (!resumeWasRestored) return;
    notify({
      tone: "info",
      title: t("resumeRestoredTitle"),
      description: t("resumeRestoredBody"),
      durationMs: 3600,
    });
    setResumeWasRestored(false);
  }, [notify, resumeWasRestored, t]);

  useEffect(() => {
    if (!hasRestoredUrlState.current) return;
    const snapshot = buildResumeSearchSnapshot({
      origin,
      destination,
      travelDate,
      returnDate,
      isReturn,
      adults,
      daysBefore,
      daysAfter,
      radiusKm,
      strictFilters,
      departAfter,
      departBefore,
      includeStops,
      maxStops,
      bufferMin,
      includeNearbyOrigins,
      includeNearbyDestinations,
      excludeOrigins,
      excludeDestinations,
      priceMin,
      priceMax,
      durationMax,
      sortBy,
      resultsCount: results.length,
      summary: resumableSummary,
      detail: resumableDetail,
    });
    saveResumeSearchSnapshot(snapshot);
  }, [
    adults,
    bufferMin,
    daysAfter,
    daysBefore,
    departAfter,
    departBefore,
    destination,
    durationMax,
    excludeDestinations,
    excludeOrigins,
    includeNearbyDestinations,
    includeNearbyOrigins,
    includeStops,
    isReturn,
    maxStops,
    origin,
    priceMax,
    priceMin,
    radiusKm,
    results.length,
    resumableDetail,
    resumableSummary,
    returnDate,
    sortBy,
    strictFilters,
    travelDate,
  ]);

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

  const logQuickSearchApiError = useCallback((scope: string, meta: Record<string, unknown>) => {
    if (typeof window === "undefined") return;
    const nonFatal = NON_FATAL_QS_SCOPES.has(scope);
    if (process.env.NODE_ENV === "production") {
      // eslint-disable-next-line no-console
      console.warn(`[qs] ${scope}`, meta);
      return;
    }
    if (nonFatal) {
      // eslint-disable-next-line no-console
      console.warn(`[qs] ${scope}`, meta);
      return;
    }
    // eslint-disable-next-line no-console
    console.error(`[qs] ${scope}`, meta);
  }, []);

  const [flexCustomPanelOpen, setFlexCustomPanelOpen] = useState(false);
  const isRecommendations = mode === "recommendations";
  const pageTitle = isRecommendations ? t("titleRecommendations") : t("title");
  const pageSubtitle = isRecommendations ? t("subtitleRecommendations") : t("subtitle");
  const pageWorkspaceHint = isRecommendations ? t("workspaceHintRecommendations") : t("workspaceHint");
  const relaxedLabels = useMemo(() => {
    if (!filtersMeta?.relaxed || filtersMeta.relaxed.length === 0) return [];
    return filtersMeta.relaxed.map((item) => {
      if (item === "date_flex_auto") return t("relaxedDateFlexAuto");
      if (item === "nearby_auto") return t("relaxedNearbyAuto");
      if (item === "departure_window_auto") return t("relaxedDepartureWindowAuto");
      return item;
    });
  }, [filtersMeta?.relaxed, t]);
  const formatScore = (value: number) => formatNumber(value, { maximumFractionDigits: 2 }, localeTag);
  const formatMoney = (value: number, currency?: string) => {
    const code = currency ?? searchMeta?.currency ?? "EUR";
    return formatCurrency(value, code, localeTag);
  };

  // ── Per-side formatMoney (Fase 6) ────────────────────────────────────
  const formatMoneyOutbound = useCallback(
    (value: number, currency?: string) => {
      const code = currency ?? outboundSide.searchMeta?.currency ?? "EUR";
      return formatCurrency(value, code, localeTag);
    },
    [outboundSide.searchMeta?.currency, localeTag],
  );
  const formatMoneyReturn = useCallback(
    (value: number, currency?: string) => {
      const code = currency ?? returnSide.searchMeta?.currency ?? "EUR";
      return formatCurrency(value, code, localeTag);
    },
    [returnSide.searchMeta?.currency, localeTag],
  );
  const countryDisplayNames = useMemo(() => {
    try {
      return new Intl.DisplayNames([localeTag], { type: "region" });
    } catch {
      return null;
    }
  }, [localeTag]);

  const mergeSeedAirportEntries = useCallback((entries: AirportIataEntry[]) => {
    if (!Array.isArray(entries) || entries.length === 0) return;
    setSeedAirports((prev) => {
      const byIata = new Map(prev.map((item) => [item.iata, item]));
      for (const entry of entries) {
        if (!entry?.iata) continue;
        byIata.set(entry.iata, entry);
      }
      return Array.from(byIata.values());
    });
  }, []);

  const fetchSeedAirports = useCallback(async (params: {
    q?: string;
    country_code?: string;
    limit?: number;
    offset?: number;
  }) => {
    const search = new URLSearchParams();
    if (params.q) search.set("q", params.q);
    if (params.country_code) search.set("country_code", params.country_code);
    if (params.limit) search.set("limit", String(params.limit));
    if (params.offset) search.set("offset", String(params.offset));
    const query = search.toString();
    type QuickSearchSeedAirportResponse = { items?: AirportIataEntry[]; total?: number; next_offset?: number };
    const data = await apiFetch<QuickSearchSeedAirportResponse>(`/airports/seeds${query ? `?${query}` : ""}`);
    const items = Array.isArray(data?.items) ? data.items : [];
    mergeSeedAirportEntries(items);
    return data;
  }, [mergeSeedAirportEntries]);

  const fetchSeedCountriesFromSeeds = useCallback(async (): Promise<Array<{ code: string; name: string; airport_count: number }>> => {
    const byCode = new Map<string, number>();
    const pageLimit = 500;
    let offset = 0;
    let guard = 0;

    while (guard < 20) {
      guard += 1;
      const data = await fetchSeedAirports({ limit: pageLimit, offset });
      const items = Array.isArray(data?.items) ? data.items : [];
      for (const airport of items) {
        const code = (airport.country_code || "").trim().toUpperCase();
        if (!code) continue;
        byCode.set(code, (byCode.get(code) || 0) + 1);
      }
      const nextOffset = typeof data?.next_offset === "number" ? data.next_offset : null;
      if (nextOffset !== null && nextOffset > offset) {
        offset = nextOffset;
        continue;
      }
      const total = typeof data?.total === "number" ? data.total : null;
      if (total !== null && offset + items.length < total && items.length > 0) {
        offset += items.length;
        continue;
      }
      break;
    }

    const resolveCountryNameCached = (code: string): string => {
      const display = _getDisplayNames();
      if (!display) return code;
      try {
        return display.of(code) || code;
      } catch {
        return code;
      }
    };

    return Array.from(byCode.entries())
      .map(([code, airport_count]) => ({
        code,
        name: resolveCountryNameCached(code),
        airport_count,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [fetchSeedAirports]);

  useEffect(() => {
    let cancelled = false;
    apiFetch<QuickSearchCountrySeedResponse>("/airports/countries")
      .then((data) => {
        if (cancelled) return;
        setSeedCountries(Array.isArray(data?.items) ? data.items : []);
      })
      .catch(async (error) => {
        try {
          const fallbackItems = await fetchSeedCountriesFromSeeds();
          if (cancelled) return;
          setSeedCountries(fallbackItems);
          logQuickSearchApiError("seed_countries_fallback_used", {
            countries: fallbackItems.length,
          });
        } catch (fallbackError) {
          if (cancelled) return;
          setSeedCountries([]);
          logQuickSearchApiError("seed_countries_failed", { error, fallbackError });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [fetchSeedCountriesFromSeeds, logQuickSearchApiError]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchSeedAirports({ q: "MAD", limit: 6 }),
      fetchSeedAirports({ q: "DUB", limit: 6 }),
    ]).catch((error) => {
      if (cancelled) return;
      logQuickSearchApiError("seed_bootstrap_failed", { error });
    });
    return () => {
      cancelled = true;
    };
  }, [fetchSeedAirports, logQuickSearchApiError]);

  const airportsByCountry = useMemo(() => {
    const next = new Map<string, AirportIataEntry[]>();
    for (const airport of seedAirports) {
      const key = airport.country_code || "";
      const list = next.get(key) || [];
      list.push(airport);
      next.set(key, list);
    }
    return next;
  }, [seedAirports]);

  const airportsByIata = useMemo(() => {
    const next = new Map<string, AirportIataEntry>();
    for (const airport of seedAirports) {
      next.set(airport.iata, airport);
    }
    return next;
  }, [seedAirports]);

  const countryOptions = useMemo(() => {
    const list = seedCountries.map((country) => ({
      code: country.code,
      name: countryDisplayNames?.of(country.code) || country.name || country.code,
      airports: airportsByCountry.get(country.code) || [],
    }));
    list.sort((a, b) => a.name.localeCompare(b.name));
    return list;
  }, [seedCountries, airportsByCountry, countryDisplayNames]);

  const filteredCountryOptions = useMemo(() => {
    if (!countrySearchInput.trim()) return countryOptions;
    const q = normalizeText(countrySearchInput.trim());
    return countryOptions.filter(c => normalizeText(c.name).includes(q) || normalizeText(c.code).includes(q));
  }, [countryOptions, countrySearchInput]);

  const countryByCode = useMemo(() => {
    return new Map(countryOptions.map((country) => [country.code, country]));
  }, [countryOptions]);

  useEffect(() => {
    if (selectedCountry || countryOptions.length === 0) return;
    const mad = airportsByIata.get("MAD");
    const next = (mad && countryByCode.get(mad.country_code)) || countryOptions[0] || null;
    setSelectedCountry(next);
  }, [airportsByIata, selectedCountry, countryOptions, countryByCode, setSelectedCountry]);

  useEffect(() => {
    if (!selectedCountry) return;
    const next = countryByCode.get(selectedCountry.code);
    if (next && next !== selectedCountry) {
      setSelectedCountry(next);
    }
  }, [countryByCode, selectedCountry, setSelectedCountry]);

  // ── Migrate old shared key + load per-field recents on mount ─────
  useEffect(() => {
    const storage = typeof window !== "undefined" ? window.localStorage : null;
    // One-time migration: split old shared key into field-specific keys
    migrateRecentAirports(storage);
    setOriginRecentAirports(readRecentAirports(storage, RECENT_AIRPORTS_ORIGIN_KEY));
    setDestinationRecentAirports(readRecentAirports(storage, RECENT_AIRPORTS_DESTINATION_KEY));
  }, [setOriginRecentAirports, setDestinationRecentAirports]);

  // ── Fetch seed metadata for recent airports so names display ─────
  // All unique IATA codes across both lists get looked up so that
  // buildRecentAirportSuggestions can resolve municipality names.
  useEffect(() => {
    const allRecent = [...originRecentAirports, ...destinationRecentAirports];
    const missing = allRecent.filter((iata) => !airportsByIata.has(iata));
    if (missing.length === 0) return;
    // Deduplicate and fire one lookup per unique code
    const seen = new Set<string>();
    for (const iata of missing) {
      const norm = iata.trim().toUpperCase();
      if (!norm || seen.has(norm)) continue;
      seen.add(norm);
      fetchSeedAirports({ q: norm, limit: 6 }).catch(() => {});
    }
  }, [airportsByIata, originRecentAirports, destinationRecentAirports, fetchSeedAirports]);

  const fetchAutocompleteSuggestions = useCallback(async (value: string) => {
    const query = value.trim();
    if (!query) return [];

    const candidates = Array.from(new Set([getApiSearchQuery(query), query]));
    for (const candidate of candidates) {
      const data = await fetchSeedAirports({ q: candidate, limit: 6 });
      const suggestions = buildAirportSuggestions(data.items || [], query, 6, pref?.language || "en");
      if (suggestions.length > 0) {
        return suggestions;
      }
    }

    return [];
  }, [fetchSeedAirports, pref?.language]);

  const originRecentAirportSuggestions = useMemo(
    () => buildRecentAirportSuggestions(originRecentAirports, airportsByIata, ""),
    [airportsByIata, originRecentAirports],
  );

  const destinationRecentAirportSuggestions = useMemo(
    () => buildRecentAirportSuggestions(destinationRecentAirports, airportsByIata, ""),
    [airportsByIata, destinationRecentAirports],
  );

  useEffect(() => {
    const value = origin.trim();
    if (!value) {
      setOriginSuggestions([]);
      return;
    }
    const timeout = window.setTimeout(() => {
      fetchAutocompleteSuggestions(value)
        .then((suggestions) => {
          setOriginSuggestions(suggestions);
        })
        .catch((error) => {
          setOriginSuggestions([]);
          logQuickSearchApiError("origin_suggestions_failed", { error, value });
        });
    }, 120);
    return () => window.clearTimeout(timeout);
  }, [fetchAutocompleteSuggestions, logQuickSearchApiError, origin]);

  useEffect(() => {
    const value = destination.trim();
    if (!value) {
      setDestinationSuggestions([]);
      return;
    }
    const timeout = window.setTimeout(() => {
      fetchAutocompleteSuggestions(value)
        .then((suggestions) => {
          setDestinationSuggestions(suggestions);
        })
        .catch((error) => {
          setDestinationSuggestions([]);
          logQuickSearchApiError("destination_suggestions_failed", { error, value });
        });
    }, 120);
    return () => window.clearTimeout(timeout);
  }, [destination, fetchAutocompleteSuggestions, logQuickSearchApiError]);

  useEffect(() => {
    const code = origin.trim().toUpperCase();
    if (code.length !== 3) {
      originCodeLookupRef.current = null;
      return;
    }
    if (airportsByIata.has(code)) {
      originCodeLookupRef.current = null;
      return;
    }
    if (originCodeLookupRef.current === code) return;
    originCodeLookupRef.current = code;
    fetchSeedAirports({ q: code, limit: 6 }).catch((error) => {
      logQuickSearchApiError("origin_code_validation_failed", { error, code });
    });
  }, [origin, airportsByIata, fetchSeedAirports, logQuickSearchApiError]);

  useEffect(() => {
    const code = destination.trim().toUpperCase();
    if (code.length !== 3) {
      destinationCodeLookupRef.current = null;
      return;
    }
    if (airportsByIata.has(code)) {
      destinationCodeLookupRef.current = null;
      return;
    }
    if (destinationCodeLookupRef.current === code) return;
    destinationCodeLookupRef.current = code;
    fetchSeedAirports({ q: code, limit: 6 }).catch((error) => {
      logQuickSearchApiError("destination_code_validation_failed", { error, code });
    });
  }, [destination, airportsByIata, fetchSeedAirports, logQuickSearchApiError]);

  useEffect(() => {
    apiFetch<Pref>("/preferences/search")
      .then((data) => {
        const normalized: Pref = {
          ...data,
          country_price_hint_mode_default: data.country_price_hint_mode_default || "min",
          calendar_hint_bucket_mode_default: data.calendar_hint_bucket_mode_default || "contextual",
          calendar_hint_guideline_low_max_default: Number(data.calendar_hint_guideline_low_max_default ?? 90),
          calendar_hint_guideline_mid_max_default: Number(data.calendar_hint_guideline_mid_max_default ?? 150),
          preferred_currency: data.preferred_currency || "EUR",
        };
        const defaults = resolveQuickSearchPreferenceDefaults(normalized);
        setPref(normalized);
        if (hasRestoredResumeSnapshot.current) {
          setPrefBadge(true);
          return;
        }
        setRadiusKm(defaults.radiusKm);
        setIncludeStops(defaults.includeStops);
        setDepartAfter(defaults.departAfter);
        setDepartBefore(defaults.departBefore);
        setIncludeNearbyOrigins(defaults.includeNearbyOrigins);
        setIncludeNearbyDestinations(defaults.includeNearbyDestinations);
        setStrictFilters(defaults.strictFilters);
        setPrefBadge(true);
      })
      .catch(() => {
        setPref(null);
      });
  }, [
    setDepartAfter,
    setDepartBefore,
    setIncludeNearbyDestinations,
    setIncludeNearbyOrigins,
    setIncludeStops,
    setPref,
    setPrefBadge,
    setRadiusKm,
    setStrictFilters,
  ]);

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

  // ── Fallback Ryanair URL for return leg in dual mode (Fase 13) ──────
  const buildReturnFallbackUrl = useCallback(() => {
    if (!returnDate || originCountryOnly || destinationCountryOnly) return "";
    const originMac = IATA_TO_MAC[origin] || "";
    const destinationMac = IATA_TO_MAC[destination] || "";
    const params = new URLSearchParams({
      adults: String(adults),
      teens: "0",
      children: "0",
      infants: "0",
      dateOut: returnDate,
      dateIn: "",
      isConnectedFlight: "false",
      discount: "0",
      promoCode: "",
      isReturn: "false",
      originIata: destination,
      destinationIata: origin,
      originMac: destinationMac,
      destinationMac: originMac,
      tpAdults: String(adults),
      tpTeens: "0",
      tpChildren: "0",
      tpInfants: "0",
      tpStartDate: returnDate,
      tpEndDate: "",
      tpDiscount: "0",
      tpPromoCode: "",
      tpOriginIata: destination,
      tpDestinationIata: origin,
      tpOriginMac: destinationMac,
      tpDestinationMac: originMac,
    });
    return `https://www.ryanair.com/es/es/trip/flights/select?${params.toString()}`;
  }, [adults, destination, destinationCountryOnly, origin, originCountryOnly, returnDate]);

  const originCode = origin.trim().toUpperCase();
  const destinationCode = destination.trim().toUpperCase();
  const originValid = originCountryOnly ? originCountryOnly.airports.length > 0 : (
    originCode.length === 3 && airportsByIata.has(originCode)
  );
  const destinationValid = destinationCountryOnly ? destinationCountryOnly.airports.length > 0 : (
    destinationCode.length === 3 && airportsByIata.has(destinationCode)
  );
  const originCalendarHintPool = useMemo(() => {
    if (originCountryOnly?.airports?.length) {
      return Array.from(
        new Set(
          originCountryOnly.airports
            .map((airport) => (airport?.iata || "").trim().toUpperCase())
            .filter((iata) => iata.length === 3),
        ),
      );
    }
    if (!originValid) return [];
    return [originCode];
  }, [originCode, originCountryOnly, originValid]);
  const destinationCalendarHintPool = useMemo(() => {
    if (destinationCountryOnly?.airports?.length) {
      return Array.from(
        new Set(
          destinationCountryOnly.airports
            .map((airport) => (airport?.iata || "").trim().toUpperCase())
            .filter((iata) => iata.length === 3),
        ),
      );
    }
    if (!destinationValid) return [];
    return [destinationCode];
  }, [destinationCode, destinationCountryOnly, destinationValid]);
  const hasCountryScopeForCalendarHints = Boolean(originCountryOnly || destinationCountryOnly);
  const calendarHintsScopeMode = useMemo<QuickSearchCalendarScopeMode>(() => {
    const hasOriginCountry = Boolean(originCountryOnly);
    const hasDestinationCountry = Boolean(destinationCountryOnly);
    if (hasOriginCountry && hasDestinationCountry) return "country_country";
    if (hasOriginCountry || hasDestinationCountry) return "country_mixed";
    return "iata";
  }, [destinationCountryOnly, originCountryOnly]);
  const calendarHintAggregationMode = useMemo<QuickSearchCalendarAggregationMode>(() => {
    if (!hasCountryScopeForCalendarHints) return "min";
    const mode = pref?.country_price_hint_mode_default || "min";
    if (mode === "median" || mode === "fixed_route") return mode;
    return "min";
  }, [hasCountryScopeForCalendarHints, pref?.country_price_hint_mode_default]);
  const calendarHintBucketMode = useMemo<QuickSearchCalendarBucketMode>(() => {
    const mode = pref?.calendar_hint_bucket_mode_default || "contextual";
    if (mode === "guidelines" || mode === "monthly_terciles") return mode;
    return "contextual";
  }, [pref?.calendar_hint_bucket_mode_default]);
  const calendarHintCurrency = useMemo<"EUR" | "USD" | "GBP">(() => {
    const currency = (pref?.preferred_currency || "EUR").toUpperCase();
    return currency === "USD" || currency === "GBP" ? currency : "EUR";
  }, [pref?.preferred_currency]);
  const calendarHintGuidelineThresholds = useMemo<QuickSearchCalendarGuidelineThresholds | null>(() => {
    if (calendarHintBucketMode !== "guidelines") return null;
    const rawLow = Number(pref?.calendar_hint_guideline_low_max_default ?? 90);
    const safeLow = Number.isFinite(rawLow) && rawLow >= 0 ? rawLow : 90;
    const rawMid = Number(pref?.calendar_hint_guideline_mid_max_default ?? 150);
    const safeMid = Number.isFinite(rawMid) && rawMid > safeLow ? rawMid : Math.max(safeLow + 1, 150);
    const rawCurrency = (pref?.preferred_currency || "EUR").toUpperCase();
    const safeCurrency = rawCurrency === "USD" || rawCurrency === "GBP" || rawCurrency === "EUR" ? rawCurrency : "EUR";
    return {
      low_max: Number(safeLow.toFixed(2)),
      mid_max: Number(safeMid.toFixed(2)),
      currency: safeCurrency,
    };
  }, [
    calendarHintBucketMode,
    pref?.calendar_hint_guideline_low_max_default,
    pref?.calendar_hint_guideline_mid_max_default,
    pref?.preferred_currency,
  ]);
  const calendarHintGuidelineSignature = useMemo(() => {
    if (!calendarHintGuidelineThresholds) return "none";
    return [
      calendarHintGuidelineThresholds.low_max.toFixed(2),
      calendarHintGuidelineThresholds.mid_max.toFixed(2),
      calendarHintGuidelineThresholds.currency,
    ].join(":");
  }, [calendarHintGuidelineThresholds]);
  const calendarHintsScopeSignature = useMemo(() => {
    const originScope = originCalendarHintPool.join(",");
    const destinationScope = destinationCalendarHintPool.join(",");
    return `o:${originScope}|d:${destinationScope}`;
  }, [destinationCalendarHintPool, originCalendarHintPool]);
  const canRequestCalendarHints = originValid
    && destinationValid
    && originCalendarHintPool.length > 0
    && destinationCalendarHintPool.length > 0;
  const calendarHintsRequestKey = useMemo(() => {
    if (!calendarVisibleMonth) return "";
    if (!canRequestCalendarHints) return "";
    return `${calendarVisibleMonth}|${calendarHintsScopeSignature}|${calendarHintAggregationMode}|${calendarHintBucketMode}|${calendarHintGuidelineSignature}|${calendarHintCurrency}|outbound|${adults}`;
  }, [
    adults,
    calendarHintAggregationMode,
    calendarHintBucketMode,
    calendarHintCurrency,
    calendarHintGuidelineSignature,
    calendarHintsScopeSignature,
    calendarVisibleMonth,
    canRequestCalendarHints,
  ]);
  const calendarHintsActive = calendarHintsRequestKey ? calendarHintsByKey[calendarHintsRequestKey] : undefined;

  // ── Return-side calendar hints (Fase 4) ────────────────────────────
  const calendarHintsScopeSignatureReturn = useMemo(() => {
    // Invert IATA pair for return leg: destination → origin
    const originScope = destinationCalendarHintPool.join(",");
    const destinationScope = originCalendarHintPool.join(",");
    return `o:${originScope}|d:${destinationScope}`;
  }, [destinationCalendarHintPool, originCalendarHintPool]);
  const calendarHintsRequestKeyReturn = useMemo(() => {
    if (!calendarVisibleMonthReturn) return "";
    if (!canRequestCalendarHints) return "";
    return `${calendarVisibleMonthReturn}|${calendarHintsScopeSignatureReturn}|${calendarHintAggregationMode}|${calendarHintBucketMode}|${calendarHintGuidelineSignature}|${calendarHintCurrency}|return|${adults}`;
  }, [
    adults,
    calendarHintAggregationMode,
    calendarHintBucketMode,
    calendarHintCurrency,
    calendarHintGuidelineSignature,
    calendarHintsScopeSignatureReturn,
    calendarVisibleMonthReturn,
    canRequestCalendarHints,
  ]);
  const calendarHintsActiveReturn = calendarHintsRequestKeyReturn ? calendarHintsByKeyReturn[calendarHintsRequestKeyReturn] : undefined;

  useEffect(() => {
    setCalendarHintsByKey({});
    setCalendarHintsByKeyReturn({});
    setCalendarHintsLoadingKeyReturn(null);
    setCalendarHintsLoadingKey(null);
  }, [adults, calendarHintAggregationMode, calendarHintBucketMode, calendarHintGuidelineSignature, calendarHintsScopeSignature]);

  useEffect(() => {
    if (!canRequestCalendarHints) return;
    if (!calendarVisibleMonth) return;
    if (!calendarHintsRequestKey) return;
    if (calendarHintsByKey[calendarHintsRequestKey]) return;

    const controller = new AbortController();
    const requestedMonth = calendarVisibleMonth;
    const requestKey = calendarHintsRequestKey;
    setCalendarHintsLoadingKey(requestKey);

    apiFetchWithRetry<QuickSearchCalendarHintsResponse>("/search/quick/calendar-hints", {
      method: "POST",
      signal: controller.signal,
      body: JSON.stringify({
        origin_iata: originCountryOnly
          ? originCalendarHintPool
          : originCalendarHintPool[0] || originCode,
        destination_iata: destinationCountryOnly
          ? destinationCalendarHintPool
          : destinationCalendarHintPool[0] || destinationCode,
        month: requestedMonth,
        adults,
        currency: calendarHintCurrency,
        leg: "outbound",
        cabin: "economy",
        aggregation_mode: calendarHintAggregationMode,
        bucket_mode: calendarHintBucketMode,
        guideline_thresholds: calendarHintBucketMode === "guidelines" ? calendarHintGuidelineThresholds : undefined,
      }),
    }, { maxRetries: 2, apiBase: LONG_RUNNING_API_BASE })
      .then((result) => {
        if (controller.signal.aborted) return;
        if (!result.ok) {
          setCalendarHintsByKey((prev) => ({
            ...prev,
            [requestKey]: buildEmptyCalendarHintsCacheEntry(calendarHintsScopeMode),
          }));
          logQuickSearchApiError("calendar_hints_failed", {
            status: result.status,
            error: result.error,
            origin_iata: originCountryOnly ? originCalendarHintPool : originCode,
            destination_iata: destinationCountryOnly ? destinationCalendarHintPool : destinationCode,
            month: requestedMonth,
            aggregation_mode: calendarHintAggregationMode,
            bucket_mode: calendarHintBucketMode,
            guideline_thresholds: calendarHintBucketMode === "guidelines" ? calendarHintGuidelineThresholds : undefined,
          });
          return;
        }
        const days = Array.isArray(result.data.days) ? result.data.days : [];
        const hintsForMonth = days.reduce<Record<string, QuickSearchCalendarDayHint>>((acc, day) => {
          if (!day?.date) return acc;
          acc[day.date] = day;
          return acc;
        }, {});
        const scopeMode = result.data.meta?.scope_mode || calendarHintsScopeMode;
        setCalendarHintsByKey((prev) => ({
          ...prev,
          [requestKey]: {
            dayHintsByIso: hintsForMonth,
            scopeMode,
          },
        }));
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        setCalendarHintsByKey((prev) => ({
          ...prev,
          [requestKey]: buildEmptyCalendarHintsCacheEntry(calendarHintsScopeMode),
        }));
        logQuickSearchApiError("calendar_hints_exception", {
          error,
          origin_iata: originCountryOnly ? originCalendarHintPool : originCode,
          destination_iata: destinationCountryOnly ? destinationCalendarHintPool : destinationCode,
          month: requestedMonth,
          aggregation_mode: calendarHintAggregationMode,
          bucket_mode: calendarHintBucketMode,
          guideline_thresholds: calendarHintBucketMode === "guidelines" ? calendarHintGuidelineThresholds : undefined,
        });
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setCalendarHintsLoadingKey((current) => (current === requestKey ? null : current));
      });

    return () => controller.abort();
  }, [
    adults,
    calendarHintAggregationMode,
    calendarHintBucketMode,
    calendarHintCurrency,
    calendarHintGuidelineThresholds,
    calendarHintsByKey,
    calendarHintsRequestKey,
    calendarHintsScopeMode,
    calendarVisibleMonth,
    canRequestCalendarHints,
    destinationCode,
    destinationCalendarHintPool,
    destinationCountryOnly,
    isReturn,
    logQuickSearchApiError,
    originCode,
    originCalendarHintPool,
    originCountryOnly,
  ]);

  // ── Return-side calendar hints fetch (Fase 4) ──────────────────────
  useEffect(() => {
    if (!canRequestCalendarHints) return;
    if (!isReturn) return;
    if (!calendarVisibleMonthReturn) return;
    if (!calendarHintsRequestKeyReturn) return;
    if (calendarHintsByKeyReturn[calendarHintsRequestKeyReturn]) return;

    const controller = new AbortController();
    const requestedMonth = calendarVisibleMonthReturn;
    const requestKey = calendarHintsRequestKeyReturn;
    setCalendarHintsLoadingKeyReturn(requestKey);

    apiFetchWithRetry<QuickSearchCalendarHintsResponse>("/search/quick/calendar-hints", {
      method: "POST",
      signal: controller.signal,
      body: JSON.stringify({
        // Invert IATA pair for return leg: destination → origin
        origin_iata: destinationCountryOnly
          ? destinationCalendarHintPool
          : destinationCalendarHintPool[0] || destinationCode,
        destination_iata: originCountryOnly
          ? originCalendarHintPool
          : originCalendarHintPool[0] || originCode,
        month: requestedMonth,
        adults,
        currency: calendarHintCurrency,
        leg: "return",
        cabin: "economy",
        aggregation_mode: calendarHintAggregationMode,
        bucket_mode: calendarHintBucketMode,
        guideline_thresholds: calendarHintBucketMode === "guidelines" ? calendarHintGuidelineThresholds : undefined,
      }),
    }, { maxRetries: 2, apiBase: LONG_RUNNING_API_BASE })
      .then((result) => {
        if (controller.signal.aborted) return;
        if (!result.ok) {
          setCalendarHintsByKeyReturn((prev) => ({
            ...prev,
            [requestKey]: buildEmptyCalendarHintsCacheEntry(calendarHintsScopeMode),
          }));
          logQuickSearchApiError("calendar_hints_return_failed", {
            status: result.status,
            error: result.error,
            origin_iata: destinationCountryOnly ? destinationCalendarHintPool : destinationCode,
            destination_iata: originCountryOnly ? originCalendarHintPool : originCode,
            month: requestedMonth,
            aggregation_mode: calendarHintAggregationMode,
            bucket_mode: calendarHintBucketMode,
            guideline_thresholds: calendarHintBucketMode === "guidelines" ? calendarHintGuidelineThresholds : undefined,
          });
          return;
        }
        const days = Array.isArray(result.data.days) ? result.data.days : [];
        const hintsForMonth = days.reduce<Record<string, QuickSearchCalendarDayHint>>((acc, day) => {
          if (!day?.date) return acc;
          acc[day.date] = day;
          return acc;
        }, {});
        const scopeMode = result.data.meta?.scope_mode || calendarHintsScopeMode;
        setCalendarHintsByKeyReturn((prev) => ({
          ...prev,
          [requestKey]: {
            dayHintsByIso: hintsForMonth,
            scopeMode,
          },
        }));
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        setCalendarHintsByKeyReturn((prev) => ({
          ...prev,
          [requestKey]: buildEmptyCalendarHintsCacheEntry(calendarHintsScopeMode),
        }));
        logQuickSearchApiError("calendar_hints_return_exception", {
          error,
          origin_iata: destinationCountryOnly ? destinationCalendarHintPool : destinationCode,
          destination_iata: originCountryOnly ? originCalendarHintPool : originCode,
          month: requestedMonth,
          aggregation_mode: calendarHintAggregationMode,
          bucket_mode: calendarHintBucketMode,
          guideline_thresholds: calendarHintBucketMode === "guidelines" ? calendarHintGuidelineThresholds : undefined,
        });
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setCalendarHintsLoadingKeyReturn((current) => (current === requestKey ? null : current));
      });

    return () => controller.abort();
  }, [
    adults,
    calendarHintAggregationMode,
    calendarHintBucketMode,
    calendarHintCurrency,
    calendarHintGuidelineThresholds,
    calendarHintsByKeyReturn,
    calendarHintsRequestKeyReturn,
    calendarHintsScopeMode,
    calendarVisibleMonthReturn,
    canRequestCalendarHints,
    destinationCode,
    destinationCalendarHintPool,
    destinationCountryOnly,
    isReturn,
    logQuickSearchApiError,
    originCode,
    originCalendarHintPool,
    originCountryOnly,
  ]);


  useEffect(() => {
    if (!travelDate || originCountryOnly || destinationCountryOnly || !originValid || !destinationValid) {
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
    params.set("origin_iata", originCode);
    params.set("destination_iata", destinationCode);
    params.set("date_out", travelDate);
    if (isReturn && returnDate) {
      params.set("date_in", returnDate);
    }
    params.set("adults", String(adults));
    params.set("teens", "0");
    params.set("children", "0");
    params.set("infants", "0");
    params.set("locale", locale === "en" ? "en-us" : "es-es");
    apiFetchWithStatus<DeepLinkResponse>(`/search/deeplink?${params.toString()}`, {
      method: "GET",
      signal: controller.signal,
    })
      .then((result) => {
        if (controller.signal.aborted) {
          return;
        }
        if (result.ok) {
          setDeepLink(result.data);
          setDeepLinkError("");
          return;
        }
        logQuickSearchApiError("deeplink_failed", {
          status: result.status,
          error: result.error,
          params: Object.fromEntries(params.entries()),
        });
        setDeepLink(null);
        setDeepLinkError(t("deepLinkError"));
      })
      .catch((error) => {
        if (controller.signal.aborted) {
          return;
        }
        logQuickSearchApiError("deeplink_exception", {
          error,
          params: Object.fromEntries(params.entries()),
        });
        setDeepLink(null);
        setDeepLinkError(t("deepLinkError"));
      });
    return () => controller.abort();
  }, [
    adults,
    destinationCode,
    destinationCountryOnly,
    destinationValid,
    isReturn,
    locale,
    originCode,
    originCountryOnly,
    originValid,
    returnDate,
    setDeepLink,
    setDeepLinkError,
    t,
    travelDate,
    logQuickSearchApiError,
  ]);

  const findCountryByIataLocal = useCallback((iata: string): CountryAirports | null => {
    const code = iata.trim().toUpperCase();
    const entry = airportsByIata.get(code);
    if (!entry) return null;
    return countryByCode.get(entry.country_code) || null;
  }, [airportsByIata, countryByCode]);

  // weatherLabel imported from @/modules/quick-search/weatherUtils

  // isWeatherRangeSupported imported from @/modules/quick-search/weatherUtils

  // fetchWeather imported from @/modules/quick-search/weatherUtils
  const fetchWeather = (iata: string, start: string, end: string) => fetchWeatherApi(iata, start, end, t);

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

  async function onSubmit(
    event: FormEvent,
    options?: { page?: number; sortBy?: QuickSearchSortBy; presentation?: "search" | "page" },
  ) {
    event.preventDefault();
    if (searchSubmitInFlightRef.current) return;
    const isPageChange = options?.presentation === "page";
    searchSubmitInFlightRef.current = true;
    setIsSubmitting(true);
    const releaseSearchSubmit = () => {
      searchSubmitInFlightRef.current = false;
      setIsSubmitting(false);
      setIsPageChanging(false);
    };
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
    setIsPageChanging(isPageChange);

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
      releaseSearchSubmit();
      return;
    }
    if (!travelDate) {
      setSearchState("error");
      setSearchError(t("errorText"));
      setDateTouched(true);
      setFieldErrors({ travel_date: t("selectOutbound") });
      releaseSearchSubmit();
      return;
    }
    const ensureSeedCode = async (code: string) => {
      const normalized = code.trim().toUpperCase();
      if (!normalized || normalized.length !== 3) return false;
      if (airportsByIata.has(normalized)) return true;
      try {
        const response = await fetchSeedAirports({ q: normalized, limit: 6 });
        return Array.isArray(response.items) && response.items.some((item) => item.iata === normalized);
      } catch {
        return false;
      }
    };

    let originValidNow = originValid;
    let destinationValidNow = destinationValid;
    if (!originCountryOnly && !originValidNow) {
      originValidNow = await ensureSeedCode(originCode);
    }
    if (!destinationCountryOnly && !destinationValidNow) {
      destinationValidNow = await ensureSeedCode(destinationCode);
    }

    if (!originValidNow || !destinationValidNow) {
      setSearchState("error");
      setSearchError(t("errorText"));
      if (!originValidNow) setOriginTouched(true);
      if (!destinationValidNow) setDestinationTouched(true);
      setFieldErrors({
        origin_iata: !originValidNow ? t("iataInvalid") : undefined,
        destination_iata: !destinationValidNow ? t("iataInvalid") : undefined,
      });
      releaseSearchSubmit();
      return;
    }
    const optionalOriginCodes = additionalOrigins.map((entry) => entry.value.trim().toUpperCase()).filter(Boolean);
    const optionalDestinationCodes = additionalDestinations.map((entry) => entry.value.trim().toUpperCase()).filter(Boolean);
    const optionalCodes = Array.from(new Set([...optionalOriginCodes, ...optionalDestinationCodes]));
    const optionalValidity = await Promise.all(optionalCodes.map(async (code) => [code, await ensureSeedCode(code)] as const));
    const knownAirportsForSubmit = new Set(airportsByIata.keys());
    for (const [code, isValid] of optionalValidity) {
      if (isValid) knownAirportsForSubmit.add(code);
    }
    const originSeeds = buildRouteSeedList(
      originCountryOnly ? originCountryOnly.airports.map((item) => item.iata) : originCode,
      optionalOriginCodes,
      knownAirportsForSubmit,
    );
    const destinationSeeds = buildRouteSeedList(
      destinationCountryOnly ? destinationCountryOnly.airports.map((item) => item.iata) : destinationCode,
      optionalDestinationCodes,
      knownAirportsForSubmit,
    );
    const validOptionalOriginCodes = Array.from(new Set(optionalOriginCodes.filter((code) => knownAirportsForSubmit.has(code))));
    const validOptionalDestinationCodes = Array.from(new Set(optionalDestinationCodes.filter((code) => knownAirportsForSubmit.has(code))));
    const appliedCriteriaSignature = buildAppliedCriteriaSignature(
      currentCriteriaSignature,
      validOptionalOriginCodes,
      validOptionalDestinationCodes,
    );
    const originRequestValue = originSeeds.length === 1 ? originSeeds[0] ?? "" : originSeeds;
    const destinationRequestValue = destinationSeeds.length === 1 ? destinationSeeds[0] ?? "" : destinationSeeds;
    submittedRouteSeedsRef.current = { origin: originSeeds, destination: destinationSeeds };
    if (isReturn && !returnDate) {
      setSearchState("error");
      setReturnDateTouched(true);
      setSearchError(t("selectReturn"));
      releaseSearchSubmit();
      return;
    }
    if (isReturn && returnDate && returnDate < travelDate) {
      setSearchState("error");
      setSearchError(t("returnBefore"));
      setReturnDateTouched(true);
      releaseSearchSubmit();
      return;
    }
    if (Object.keys(nextFieldErrors).length > 0) {
      setSearchState("error");
      setSearchError(t("errorText"));
      setFieldErrors(nextFieldErrors);
      releaseSearchSubmit();
      return;
    }

    // ── Dual-mode: dispatch two independent searches in parallel (Fase 6) ──
    if (isDualMode) {
      setAppliedCriteriaSignature(appliedCriteriaSignature);
      setHasSearched(true);

      const dNextExcludeOrigins = [...excludeOrigins];
      const dNextExcludeDestinations = [...excludeDestinations];
      parseIataList(excludeOriginInput).forEach((v: string) => { if (!dNextExcludeOrigins.includes(v)) dNextExcludeOrigins.push(v); });
      parseIataList(excludeDestinationInput).forEach((v: string) => { if (!dNextExcludeDestinations.includes(v)) dNextExcludeDestinations.push(v); });
      if (excludeOriginInput) setExcludeOriginInput("");
      if (excludeDestinationInput) setExcludeDestinationInput("");

      const dualBaseParams = buildDualSearchParams({
        origin: originRequestValue,
        destination: destinationRequestValue,
        travelDate,
        flexDaysBefore: daysBefore,
        flexDaysAfter: daysAfter,
        radiusKm: normalizedRadiusKm,
        includeStops,
        includeNearbyOrigins,
        includeNearbyDestinations,
        departAfter,
        departBefore,
        maxStops,
        excludeOrigins: dNextExcludeOrigins,
        excludeDestinations: dNextExcludeDestinations,
        strictFilters,
      });

      void Promise.all([
        outboundSide.runSearch(dualBaseParams),
        returnSide.runSearch(
          buildDualSearchParams({
            origin: destinationRequestValue,
            destination: originRequestValue,
            travelDate: returnDate,
            flexDaysBefore: daysBefore,
            flexDaysAfter: daysAfter,
            radiusKm: normalizedRadiusKm,
            includeStops,
            includeNearbyOrigins,
            includeNearbyDestinations,
            departAfter,
            departBefore,
            maxStops,
            excludeOrigins: dNextExcludeOrigins,
            excludeDestinations: dNextExcludeDestinations,
            strictFilters,
          }),
        ),
      ]);
      releaseSearchSubmit();
      return;
    }

    setAppliedCriteriaSignature(appliedCriteriaSignature);
    if (!isPageChange) {
      setWeatherMessage("");
      setWeatherOrigin(null);
      setWeatherDestination(null);
      setFiltersNotice([]);
      setFiltersWarningCodes([]);
      setFiltersMeta(null);
      setSearchMeta(null);
      lastQuickSearchPayloadRef.current = null;
      setLoaderResolvedTotalFlights(null);
      setJobId(null);
      setIsDegraded(false);
      setSearchState("loading");
      setShowLoader(true);
      setLoadingVisualHold(false);
      setDisplayProgress(0);
      setProgress("requesting", 30);
      setProviderSearchStatuses(INITIAL_PROVIDER_SEARCH_STATUSES);
    }
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
    const exactTravelDates = !isReturn && selectedTravelDates.length > 1
      ? selectedTravelDates
      : [];
    const range = exactTravelDates.length > 0
      ? exactTravelDates
      : buildDateRange(travelDate, isReturn ? returnDate : travelDate);
    const payload = {
      origin_iata: originRequestValue,
      destination_iata: destinationRequestValue,
      travel_date: travelDate,
      date: travelDate,
      travel_dates: exactTravelDates,
      flex_days_before: exactTravelDates.length > 0 ? 0 : daysBefore,
      flex_days_after: exactTravelDates.length > 0 ? 0 : daysAfter,
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
      page: options?.page ?? 1,
      page_size: PAGE_SIZE,
      sort_by: options?.sortBy ?? sortBy,
    };
    const originScopeCount = Array.isArray(payload.origin_iata) ? payload.origin_iata.length : 1;
    const destinationScopeCount = Array.isArray(payload.destination_iata) ? payload.destination_iata.length : 1;
    const datesScopeCount = Math.max(1, range.length);
    const routesScopeCount = Math.max(1, originScopeCount * destinationScopeCount);
    const plannedTotalFlights = Math.max(1, routesScopeCount * datesScopeCount);
    setLoaderScopeRoutes(routesScopeCount);
    setLoaderScopeDates(datesScopeCount);
    setLoaderPlannedTotalFlights(plannedTotalFlights);
    const nextExecutedCriteria: ExecutedCriteriaSnapshot = {
      route: `${originCountryOnly ? originCountryOnly.name : originSeeds.join(", ")}${originCountryOnly && validOptionalOriginCodes.length > 0 ? ` + ${validOptionalOriginCodes.join(", ")}` : ""} â†’ ${destinationCountryOnly ? destinationCountryOnly.name : destinationSeeds.join(", ")}${destinationCountryOnly && validOptionalDestinationCodes.length > 0 ? ` + ${validOptionalDestinationCodes.join(", ")}` : ""}`,
      dateLabel: exactTravelDates.length > 0
        ? `${exactTravelDates.length} ${locale === "es" ? "días seleccionados" : "selected days"}`
        : isReturn && returnDate ? `${travelDate} â†’ ${returnDate}` : travelDate,
      paxLabel: `${adults} ${adults === 1 ? t("summaryPassengersSingular") : t("summaryPassengersPlural")}`,
    };
    trackEvent("quicksearch_search_submitted", {
      has_origin_country_scope: Boolean(originCountryOnly),
      has_destination_country_scope: Boolean(destinationCountryOnly),
      origin_count: originSeeds.length,
      destination_count: destinationSeeds.length,
      include_stops: includeStops,
      strict_filters: strictFilters,
      radius_km: normalizedRadiusKm,
      flex_days_before: daysBefore,
      flex_days_after: daysAfter,
      exact_dates_count: exactTravelDates.length,
    });
    const preparedRequest = prepareQuickSearchRequest(payload);
    if (preparedRequest.issues.length > 0) {
      setSearchError(t("errorText"));
      setSearchState("idle");
      setIsLoading(false);
      setIsPageChanging(false);
      trackEvent("quicksearch_contract_blocked", {
        issues: preparedRequest.issues.map((issue) => issue.code).join(","),
      });
      releaseSearchSubmit();
      return;
    }
    const canonicalPayload = buildQuickSearchCanonicalPayload(preparedRequest.params);
    try {
      expectedQuerySignaturesRef.current = await buildQuickSearchExpectedSignatures(canonicalPayload);
      if (!isCurrentRequest()) return;
      if (
        exactTravelDates.length > 0
        && !isPageChange
        && typeof originRequestValue === "string"
        && typeof destinationRequestValue === "string"
      ) {
        const watchResponse = await apiFetchWithStatus<BulkWatchCreateResponse>("/watchlist/bulk-create", {
          method: "POST",
          body: JSON.stringify({
            origin_iata: originRequestValue,
            destination_iata: destinationRequestValue,
            travel_dates: exactTravelDates,
          }),
        });
        if (watchResponse.ok) {
          const createdCount = watchResponse.data.created_dates.length;
          const existingCount = watchResponse.data.existing_dates.length;
          const title = locale === "es"
            ? `${createdCount} seguimiento${createdCount === 1 ? "" : "s"} creado${createdCount === 1 ? "" : "s"}${existingCount ? ` · ${existingCount} ya existente${existingCount === 1 ? "" : "s"}` : ""}`
            : `${createdCount} tracking ${createdCount === 1 ? "created" : "entries created"}${existingCount ? ` · ${existingCount} already existed` : ""}`;
          notify({
            tone: "success",
            title,
            actionLabel: t("viewWatchlist"),
            onAction: () => navigateToWatchlistWithContext(originRequestValue, destinationRequestValue),
            durationMs: 4200,
          });
        } else {
          notify({
            tone: "error",
            title: locale === "es"
              ? "No se han podido crear los seguimientos de los días elegidos. La búsqueda continúa."
              : "We could not create tracking for the selected days. The search will continue.",
            durationMs: 4200,
          });
        }
      }
      if (!isPageChange) {
        setIsLoading(true);
      }
      const originWeatherIata = originCountryOnly ? "" : originCode;
      const destinationWeatherIata = destinationCountryOnly ? "" : destinationCode;
      const weatherRangeSupported = range.length > 0 && isWeatherRangeSupportedCheck(range[0], range[range.length - 1]);
      if (!isPageChange && !weatherRangeSupported && (originWeatherIata || destinationWeatherIata)) {
        setWeatherMessage(t("weatherUnavailableRange"));
      }

      if (!isPageChange) {
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
      }
      const searchResult = await apiFetchWithStatus<SearchResponseRaw>("/search/quick", {
        method: "POST",
        body: JSON.stringify(canonicalPayload),
      }, { apiBase: LONG_RUNNING_API_BASE });
      if (!isCurrentRequest()) return;
      if (!isPageChange) {
        setProgress("response_parsed", 80);
      }
      if (searchResult.ok) {
          const data: SearchResponse = normalizeQuickSearchResponse(searchResult.data);
          lastQuickSearchPayloadRef.current = canonicalPayload;
          const responseSignature = data.meta?.query_signature;
          const expectedSignatures = expectedQuerySignaturesRef.current;
          if (
            typeof responseSignature === "string"
            && expectedSignatures
            && !expectedSignatures.has(responseSignature)
          ) {
            trackEvent("quicksearch_response_signature_mismatch", {
              response_signature: responseSignature,
              expected_count: expectedSignatures.size,
            });
          }
          setResults(data.results);
          setExecutedCriteria(nextExecutedCriteria);
          setFiltersMeta(data.filters || null);
          setSearchMeta(data.meta || null);
          setCurrentPage(data.meta?.pagination?.page ?? (options?.page ?? 1));
          if (typeof data.meta?.total_candidates === "number" && Number.isFinite(data.meta.total_candidates)) {
            setLoaderResolvedTotalFlights(Math.max(0, data.meta.total_candidates));
          }
          setJobId(data.job_id || null);
          const rawProviderStatuses = data.meta?.provider_status?.providers;
          if (rawProviderStatuses && rawProviderStatuses.length > 0) {
            setProviderSearchStatuses(
              rawProviderStatuses.map((p: { id?: string; status?: string; degraded?: boolean; errors?: number; results_count?: number }) => {
                let badgeStatus: ProviderSearchStatus["status"] = "found";
                if (p.degraded || (p.errors && p.errors > 0) || p.status === "failed") badgeStatus = "error";
                else if (p.status === "ok" || (p.results_count && p.results_count > 0)) badgeStatus = "found";
                const label = p.id
                  ? p.id.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
                  : "Unknown";
                return { id: p.id || "unknown", label, status: badgeStatus, resultsCount: p.results_count };
              }),
            );
          } else {
            // No per-provider data, mark all as found (search completed)
            setProviderSearchStatuses((prev) =>
              prev.map((p) => ({ ...p, status: "found" as ProviderSearchStatus["status"] })),
            );
          }
          const providerOverallStatus = data.meta?.provider_status?.overall_status ?? data.meta?.provider_status?.overall;
          setIsDegraded(
            Boolean(
              data.meta?.stale_data
              || data.meta?.search_cache?.freshness?.status === "stale"
              || data.meta?.search_cache?.freshness?.status === "expired"
              || data.meta?.search_cache?.freshness?.status === "negative_stale"
              || data.meta?.search_cache?.freshness?.status === "provider_error_stale"
              || data.results.find((item) => item.stale_data)
              || providerOverallStatus === "partial_degraded"
              || providerOverallStatus === "total_outage"
              || data.meta?.provider_status?.partial_results_served
              || data.meta?.provider_status?.total_outage,
            ),
          );
          const warningCodes = collectQuickSearchWarningCodes(data);
          setFiltersWarningCodes(warningCodes);
          setFiltersNotice(warningCodes.map((item) => tWarn(item)));
          if (!isPageChange) {
            setProgress("client_done", 95);
          }
          setHasSearched(true);
          const isEmptyResult = (data.meta?.pagination?.total_results ?? data.results.length) === 0;
          setSearchState(isEmptyResult ? "empty" : "success");
          const durationMs = Math.round((typeof performance !== "undefined" ? performance.now() : Date.now()) - startedAt);
          void trackUxEvent("quick_search_executed", { duration_ms: durationMs, result_count: data.results.length });
          if (isEmptyResult) {
            void trackUxEvent("search_empty_results", { duration_ms: durationMs });
          }
        } else {
          const { status, error } = searchResult;
          logQuickSearchApiError("quick_search_failed", {
            status,
            error,
            request: canonicalPayload,
          });
          const validationErrors = parseValidationErrors(error.details);
          if (Object.keys(validationErrors).length > 0) {
            setFieldErrors(validationErrors);
            if (validationErrors.origin_iata) setOriginTouched(true);
            if (validationErrors.destination_iata) setDestinationTouched(true);
            if (validationErrors.travel_date) setDateTouched(true);
          }
          if (!isPageChange) {
            setProgress("client_done", 95);
          }
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
        setProviderSearchStatuses([]);
        setHasSearched(true);
    }
    } catch (error) {
      if (!isCurrentRequest()) return;
      logQuickSearchApiError("quick_search_unhandled_exception", {
        error,
        request: canonicalPayload,
      });
      if (!isPageChange) {
        setProgress("client_done", 95);
      }
      setSearchState("error");
      setSearchError(t("searchFailed"));
      setProviderSearchStatuses([]);
      setHasSearched(true);
    } finally {
      if (isCurrentRequest()) {
        setIsLoading(false);
        setIsPageChanging(false);
      }
      releaseSearchSubmit();
    }
  }

  async function handleExportQuickSearch() {
    const basePayload = lastQuickSearchPayloadRef.current;
    if (!basePayload || totalResults === 0 || isExportingQuickSearch) return;

    setIsExportingQuickSearch(true);
    try {
      const collectedResults: SearchResult[] = [];
      let exportMeta: SearchResponse["meta"] | null = null;
      let exportFilters = filtersMeta;
      let exportJobId = jobId;
      let pagesFetched = 0;
      let totalPagesForExport = 1;

      for (let page = 1; page <= totalPagesForExport; page += 1) {
        const pagePayload = buildQuickSearchExportPagePayload(basePayload, page, sortBy);
        const response = await apiFetchWithStatus<SearchResponseRaw>("/search/quick", {
          method: "POST",
          body: JSON.stringify(pagePayload),
        }, { apiBase: LONG_RUNNING_API_BASE });
        if (!response.ok) {
          logQuickSearchApiError("quick_search_export_failed", {
            status: response.status,
            error: response.error,
            page,
          });
          setMessage(t("quickExportError"));
          setMessageType("error");
          notify({ tone: "error", title: t("quickExportError") });
          return;
        }

        const pageData = normalizeQuickSearchResponse(response.data);
        pagesFetched += 1;
        collectedResults.push(...pageData.results);
        if (page === 1) {
          exportMeta = pageData.meta ?? null;
          exportFilters = pageData.filters ?? null;
          exportJobId = pageData.job_id ?? null;
          totalPagesForExport = Math.max(1, Number(pageData.meta?.pagination?.total_pages || 1));
        }
      }

      const exportedAt = new Date().toISOString();
      const originScope = originCountryOnly
        ? originCountryOnly.airports.map((airport) => airport.iata)
        : originCode ? [originCode] : [];
      const destinationScope = destinationCountryOnly
        ? destinationCountryOnly.airports.map((airport) => airport.iata)
        : destinationCode ? [destinationCode] : [];
      const criteria: QuickSearchExportCriteria = {
        origin,
        destination,
        origin_scope_iata: originScope,
        destination_scope_iata: destinationScope,
        travel_date: travelDate,
        return_date: isReturn ? returnDate || null : null,
        trip_type: isReturn ? "round_trip" : "one_way",
        adults,
        departure_window: {
          after: departAfter || null,
          before: departBefore || null,
        },
        flexibility: {
          days_before: daysBefore,
          days_after: daysAfter,
          apply_to_return: applyFlexReturn,
        },
        route_scope: {
          include_nearby_origins: includeNearbyOrigins,
          include_nearby_destinations: includeNearbyDestinations,
          radius_km: normalizedRadiusKm,
        },
        constraints: {
          include_stops: includeStops,
          max_stops: includeStops ? maxStops : 0,
          buffer_min: bufferMin.trim() || null,
          strict_filters: strictFilters,
          exclude_origins: excludeOrigins,
          exclude_destinations: excludeDestinations,
        },
        visible_filters: {
          price_min: priceMin.trim() || null,
          price_max: priceMax.trim() || null,
          duration_max: durationMax.trim() || null,
          sort_by: sortBy,
        },
      };
      const payload = buildQuickSearchExportPayload({
        exportedAt,
        criteria,
        results: collectedResults,
        meta: exportMeta,
        filters: exportFilters,
        jobId: exportJobId,
        pagesFetched,
      });
      downloadJson(buildJsonExportFilename("viru-quick-search", exportedAt), payload);
      notify({
        tone: "success",
        title: t("quickExportSuccess", { count: payload.search.result_count }),
      });
      trackEvent("quicksearch_export_json_downloaded", {
        result_count: payload.search.result_count,
        pages_fetched: pagesFetched,
      });
    } catch (error) {
      logQuickSearchApiError("quick_search_export_exception", {
        error: error instanceof Error ? error.message : String(error),
      });
      setMessage(t("quickExportError"));
      setMessageType("error");
      notify({ tone: "error", title: t("quickExportError") });
    } finally {
      setIsExportingQuickSearch(false);
    }
  }

  async function saveQuickSearchResult(
    result: SearchResult,
    fallbackDeepLinkUrl?: string | null,
    fareProfile?: FareComparisonProfile,
  ) {
    const routeFallback = getOfficialRyanairRouteDeepLink(
      fallbackDeepLinkUrl,
      result.origin,
      result.destination,
      result.travel_date,
    ) || fallbackDeepLinkUrl;
    return apiFetch<SaveResult>("/search/save-result", {
      method: "POST",
      body: JSON.stringify(buildQuickSearchSaveResultPayload(result, {
        jobId,
        fallbackDeepLinkUrl: routeFallback,
        fareProfile,
      })),
    });
  }

  function canRefreshPrice(result: SearchResult) {
    const status = result.freshness?.status ?? null;
    return Boolean(result.origin && result.destination && result.travel_date) && (
      Boolean(result.freshness?.requires_revalidation)
      || result.stale_data
      || status === "provider_error_fresh"
      || status === "negative_fresh"
      || status === null
    );
  }

  async function refreshQuickSearchResult(result: SearchResult) {
    const rowId = resultKey(result, 0);
    setRefreshingResultId(rowId);
    setMessage("");
    try {
      const watchResponse = await saveQuickSearchResult(result, deeplinkUrl);
      const watchId = watchResponse.watch_id;
      if (!watchId) {
        notify({ tone: "error", title: t("refreshPriceError"), durationMs: 3200 });
        return;
      }

      const refreshResponse = await apiFetchWithStatus<{
        status: string;
        watch_id: string;
        stale_data?: boolean;
        provider_status?: string;
      }>(`/watchlist/${watchId}/refresh-now`, { method: "POST" });

      if (!refreshResponse.ok) {
        if (refreshResponse.status === 429) {
          notify({ tone: "info", title: t("refreshPriceRateLimited"), durationMs: 3200 });
          return;
        }
        notify({ tone: "error", title: t("refreshPriceError"), durationMs: 3200 });
        return;
      }

      if (refreshResponse.data.status === "no_flights") {
        notify({ tone: "info", title: t("refreshPriceNoFlights"), durationMs: 3200 });
        return;
      }

      if (refreshResponse.data.provider_status === "degraded" || refreshResponse.data.stale_data) {
        notify({ tone: "warning", title: t("refreshPriceProviderError"), durationMs: 3200 });
        return;
      }

      await onSubmit({ preventDefault: () => {} } as FormEvent, { page: 1 });
      notify({ tone: "success", title: t("refreshPriceSuccess"), durationMs: 3200 });
    } catch {
      notify({ tone: "error", title: t("refreshPriceError"), durationMs: 3200 });
    } finally {
      setRefreshingResultId((current) => (current === rowId ? null : current));
    }
  }

  const navigateToWatchlistWithContext = useCallback((origin?: string, destination?: string, travelDate?: string, watchId?: string) => {
    const url = buildWatchlistUrl({
      origin: origin || "",
      destination: destination || "",
      travelDate: travelDate || "",
      watchId: watchId || "",
    });
    router.push(url);
  }, [router]);

  const getResultWatchlistHref = useCallback((result: SearchResult): string => {
    return buildWatchlistUrl({
      origin: result.origin,
      destination: result.destination,
      travelDate: result.travel_date,
      watchId: getWatchId(result),
    });
  }, [getWatchId]);

  const viewResultInWatchlist = useCallback((result: SearchResult) => {
    const watchId = getWatchId(result);
    trackEvent("quicksearch_watchlist_view_clicked", {
      origin: result.origin,
      destination: result.destination,
      travel_date: result.travel_date,
      has_watch_id: Boolean(watchId),
    });
  }, [getWatchId]);

  async function addToWatchlist(result: SearchResult, fareProfile: FareComparisonProfile) {
    setMessage("");
    try {
      const response = await saveQuickSearchResult(result, deeplinkUrl, fareProfile);
      markAsSaved(result, response.watch_id);
      if (response.created_or_existing === "existing") {
        notify({
          tone: "success",
          title: t("watchExists"),
          actionLabel: t("viewWatchlist"),
          onAction: () => navigateToWatchlistWithContext(result.origin, result.destination, result.travel_date, response.watch_id),
          durationMs: 3200,
        });
      } else {
        trackEvent("quicksearch_watchlist_added", {
          origin: result.origin,
          destination: result.destination,
          travel_date: result.travel_date,
          source: result.source,
        });
        notify({
          tone: "success",
          title: t("watchAdded"),
          actionLabel: t("viewWatchlist"),
          onAction: () => navigateToWatchlistWithContext(result.origin, result.destination, result.travel_date, response.watch_id),
          durationMs: 3200,
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

  function openAdditionalPicker(side: "origin" | "destination", id: string, trigger: HTMLButtonElement) {
    lastPickerTriggerRef.current = trigger;
    setAdditionalPickerTarget({ side, id });
    openPicker(side);
  }

  const closePickerWithFocusReturn = useCallback(() => {
    setActivePicker(null);
    setAdditionalPickerTarget(null);
    if (typeof window !== "undefined") {
      window.requestAnimationFrame(() => {
        lastPickerTriggerRef.current?.focus();
      });
    }
  }, [lastPickerTriggerRef, setActivePicker]);

  function clearSelection() {
    if (additionalPickerTarget) {
      updateAdditionalAirport(additionalPickerTarget.side, additionalPickerTarget.id, "");
      return;
    }
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

  const loadCountryAirports = useCallback(async (countryCode: string) => {
    const all: AirportIataEntry[] = [];
    let offset = 0;
    let guard = 0;
    while (guard < 30) {
      guard += 1;
      const page = await fetchSeedAirports({
        country_code: countryCode,
        limit: 500,
        offset,
      });
      const items = Array.isArray(page.items) ? page.items : [];
      all.push(...items);
      if (typeof page.next_offset !== "number") break;
      offset = page.next_offset;
    }
    return all;
  }, [fetchSeedAirports]);

  const rememberAirportSelection = useCallback((field: QuickSearchAutocompleteField, iata: string) => {
    const storage = typeof window !== "undefined" ? window.localStorage : null;
    if (field === "origin") {
      const next = writeRecentAirports(rememberRecentAirport(originRecentAirports, iata), storage, undefined, RECENT_AIRPORTS_ORIGIN_KEY);
      setOriginRecentAirports(next);
    } else {
      const next = writeRecentAirports(rememberRecentAirport(destinationRecentAirports, iata), storage, undefined, RECENT_AIRPORTS_DESTINATION_KEY);
      setDestinationRecentAirports(next);
    }
  }, [originRecentAirports, setOriginRecentAirports, destinationRecentAirports, setDestinationRecentAirports]);

  const removeRecentAirportSelection = useCallback((field: QuickSearchAutocompleteField, iata: string) => {
    const storage = typeof window !== "undefined" ? window.localStorage : null;
    if (field === "origin") {
      const next = writeRecentAirports(forgetRecentAirport(originRecentAirports, iata), storage, undefined, RECENT_AIRPORTS_ORIGIN_KEY);
      setOriginRecentAirports(next);
    } else {
      const next = writeRecentAirports(forgetRecentAirport(destinationRecentAirports, iata), storage, undefined, RECENT_AIRPORTS_DESTINATION_KEY);
      setDestinationRecentAirports(next);
    }
    setActiveAutocompleteIndex(-1);
  }, [originRecentAirports, setOriginRecentAirports, destinationRecentAirports, setDestinationRecentAirports, setActiveAutocompleteIndex]);

  function selectAirport(iata: string) {
    setAirportSelectionTouched(true);
    const entry = airportsByIata.get(iata.trim().toUpperCase());
    const countryCode = entry ? entry.country_code : null;
    if (additionalPickerTarget) {
      updateAdditionalAirport(additionalPickerTarget.side, additionalPickerTarget.id, iata);
    } else if (activePicker === "origin") {
      setOrigin(iata);
      setOriginCountryOnly(null);
      setOriginSelectedCountryCode(countryCode);
    } else if (activePicker === "destination") {
      setDestination(iata);
      setDestinationCountryOnly(null);
      setDestinationSelectedCountryCode(countryCode);
    }
    rememberAirportSelection(activePicker === "origin" ? "origin" : "destination", iata);
    closePickerWithFocusReturn();
  }

  const selectCountryOnly = useCallback(async (country: CountryAirports | null) => {
    if (!country || additionalPickerTarget) return;
    const airports = await loadCountryAirports(country.code);
    const completeCountry: CountryAirports = { ...country, airports };
    if (activePicker === "origin") {
      setOrigin("");
      setOriginCountryOnly(completeCountry);
      setOriginSelectedCountryCode(null);
    }
    if (activePicker === "destination") {
      setDestination("");
      setDestinationCountryOnly(completeCountry);
      setDestinationSelectedCountryCode(null);
    }
    closePickerWithFocusReturn();
  }, [
    activePicker,
    additionalPickerTarget,
    loadCountryAirports,
    setDestination,
    setDestinationCountryOnly,
    setDestinationSelectedCountryCode,
    setOrigin,
    setOriginCountryOnly,
    setOriginSelectedCountryCode,
    closePickerWithFocusReturn,
  ]);

  const closePicker = useCallback(() => {
    if (activePicker && !additionalPickerTarget && countrySelectionTouched && !airportSelectionTouched && selectedCountry) {
      void selectCountryOnly(selectedCountry);
      return;
    }
    closePickerWithFocusReturn();
  }, [
    activePicker,
    additionalPickerTarget,
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

  // Escape closes the share/deeplink copy modal. The master handler above
  // does the same; this hook subscription is idempotent and lets us
  // progressively migrate each surface to its own Escape subscription.
  const closeCopyModal = useCallback(() => setCopyModalOpen(false), [setCopyModalOpen]);
  useEscapeClose(closeCopyModal, copyModalOpen);

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
    setSearchError(`${detail} / Por favor, introduce una bÃºsqueda.`);
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
    rememberAirportSelection(field, iata);
    setActiveAutocompleteField(null);
    setActiveAutocompleteIndex(-1);
    if (submitAfterSelect && typeof window !== "undefined") {
      window.requestAnimationFrame(() => formRef.current?.requestSubmit());
    }
  }

  const swapRouteInputs = useCallback(() => {
    const nextOrigin = destination;
    const nextDestination = origin;
    const nextOriginCountryOnly = destinationCountryOnly;
    const nextDestinationCountryOnly = originCountryOnly;
    const nextOriginSelectedCountryCode = destinationSelectedCountryCode;
    const nextDestinationSelectedCountryCode = originSelectedCountryCode;

    setOrigin(nextOrigin);
    setDestination(nextDestination);
    setOriginCountryOnly(nextOriginCountryOnly);
    setDestinationCountryOnly(nextDestinationCountryOnly);
    setOriginSelectedCountryCode(nextOriginSelectedCountryCode);
    setDestinationSelectedCountryCode(nextDestinationSelectedCountryCode);
    setAdditionalOrigins(additionalDestinations);
    setAdditionalDestinations(additionalOrigins);
    setFieldErrors((prev) => ({
      ...prev,
      origin_iata: undefined,
      destination_iata: undefined,
    }));
    setOriginTouched(false);
    setDestinationTouched(false);
    setOriginSuggestions([]);
    setDestinationSuggestions([]);
    setActiveAutocompleteField(null);
    setActiveAutocompleteIndex(-1);
    setRoutePulse(true);
    if (typeof window !== "undefined") {
      window.setTimeout(() => setRoutePulse(false), 140);
    }
  }, [
    destination,
    origin,
    destinationCountryOnly,
    originCountryOnly,
    destinationSelectedCountryCode,
    originSelectedCountryCode,
    additionalOrigins,
    additionalDestinations,
    setOrigin,
    setDestination,
    setOriginCountryOnly,
    setDestinationCountryOnly,
    setOriginSelectedCountryCode,
    setDestinationSelectedCountryCode,
    setFieldErrors,
    setOriginTouched,
    setDestinationTouched,
    setActiveAutocompleteField,
    setActiveAutocompleteIndex,
    setRoutePulse,
  ]);

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

  function parseIataList(raw: string): string[] {
    return parseQuickSearchIataTokens(raw);
  }

  function addChip(
    value: string,
    current: string[],
    setCurrent: (next: string[]) => void,
    setInput: (next: string) => void,
  ) {
    const parsed = parseQuickSearchIataTokens(value);
    if (parsed.length === 0) {
      setInput(value.toUpperCase());
      return;
    }
    setCurrent(mergeQuickSearchIataTokens(current, value));
    setInput("");
  }

  function removeChip(
    value: string,
    current: string[],
    setCurrent: (next: string[]) => void,
  ) {
    setCurrent(current.filter((item) => item !== value));
  }

  const updateRadiusKm = useCallback((value: number) => {
    setRadiusKm(clampQuickSearchRadius(value));
  }, [setRadiusKm]);

  const commitExcludeOriginInput = useCallback(() => {
    addChip(excludeOriginInput, excludeOrigins, setExcludeOrigins, setExcludeOriginInput);
  }, [excludeOriginInput, excludeOrigins, setExcludeOriginInput, setExcludeOrigins]);

  const commitExcludeDestinationInput = useCallback(() => {
    addChip(excludeDestinationInput, excludeDestinations, setExcludeDestinations, setExcludeDestinationInput);
  }, [excludeDestinationInput, excludeDestinations, setExcludeDestinationInput, setExcludeDestinations]);

  function formatMinutes(value?: number | null) {
    if (!value && value !== 0) return "--";
    return `${value} min`;
  }

  function formatFreshnessTime(value?: string | null) {
    if (!value) return null;
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.toLocaleTimeString(localeTag, { hour: "2-digit", minute: "2-digit" });
  }

  function getFreshnessLabel(result: SearchResult) {
    return getQuickSearchFreshnessPresentation({
      freshness: result.freshness,
      freshnessTs: result.freshness_ts,
      staleData: result.stale_data,
    }).label;
  }

  const globalFreshness = getQuickSearchFreshnessPresentation({
    freshness: searchMeta?.search_cache?.freshness,
    freshnessTs: searchMeta?.freshness_ts,
    staleData: searchMeta?.stale_data,
  });

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

  useEffect(() => {
    if (!activePicker || !selectedCountry?.code) {
      setCountryAirports([]);
      return;
    }
    let cancelled = false;
    fetchSeedAirports({
      country_code: selectedCountry.code,
      q: airportSearch.trim() || undefined,
      limit: 200,
    })
      .then((data) => {
        if (cancelled) return;
        setCountryAirports(Array.isArray(data.items) ? data.items : []);
      })
      .catch((error) => {
        if (cancelled) return;
        setCountryAirports([]);
        logQuickSearchApiError("country_airports_failed", {
          error,
          country_code: selectedCountry.code,
          q: airportSearch.trim() || undefined,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [activePicker, selectedCountry?.code, airportSearch, fetchSeedAirports, logQuickSearchApiError]);

  useEffect(() => {
    if (!activePicker) return;

    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;

    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
    };
  }, [activePicker]);

  const filteredCountryAirports = countryAirports;
  const airportPickerModal = activePicker ? (
    <div className="airport-modal-overlay" onClick={closePicker}>
      <section
        className="airport-modal qs-airport-modal"
        role="dialog"
        aria-modal="true"
        aria-label={t("modalPickTitle")}
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="qs-airport-modal__close"
          onClick={closePicker}
          aria-label={t("pickClose")}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
        <div className="qs-airport-modal__body">
          <div className="airport-modal-left qs-airport-modal__countries" role="region" aria-label={activePicker === "origin" ? t("modalOriginCountry") : t("modalDestinationCountry")}>
            <div className="qs-airport-modal__header" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <h2>{activePicker === "origin" ? t("modalOriginCountry") : t("modalDestinationCountry")}</h2>
              <div className="airport-search qs-airport-modal__search" role="search" style={{ padding: 0, border: "none" }}>
                <svg className="qs-airport-modal__search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" style={{ left: "12px", top: "14px" }}>
                  <circle cx="7" cy="7" r="5.25" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <input
                  className="qs-input qs-airport-modal__search-input"
                  name="country_search"
                  autoComplete="off"
                  value={countrySearchInput}
                  onChange={(e) => setCountrySearchInput(e.target.value)}
                  placeholder={t("pickCountrySearch")}
                  aria-label={t("pickCountrySearch")}
                />
              </div>
            </div>
            <div className="airport-country-grid" role="listbox" aria-label={activePicker === "origin" ? t("modalOriginCountry") : t("modalDestinationCountry")}>
              {filteredCountryOptions.map((country) => {
                const isActive = selectedCountry?.code === country.code;
                return (
                  <button
                    key={country.code}
                    type="button"
                    role="option"
                    aria-selected={isActive}
                    className={isActive ? "country-pill active" : "country-pill"}
                    onClick={() => {
                      setSelectedCountry(country);
                      setCountrySelectionTouched(true);
                    }}
                  >
                    {renderFlag(country.code)}
                    <span className="country-pill__name">{country.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <div className="airport-modal-right qs-airport-modal__airports" aria-live="polite">
            <div className="airport-modal-header qs-airport-modal__header">
              <h3>
                {t("modalPickTitle")}
                {filteredCountryAirports.length > 0 ? (
                  <span className="qs-airport-modal__count">{filteredCountryAirports.length}</span>
                ) : null}
              </h3>
              <button type="button" className="link-reset" onClick={clearSelection}>
                {t("modalClear")}
              </button>
            </div>
            {selectedCountry && !additionalPickerTarget ? (
              <div className="qs-airport-modal__country-action">
                <button type="button" className="btn-secondary btn-compact qs-airport-modal__use-country" onClick={() => void selectCountryOnly(selectedCountry)}>
                  {renderFlag(selectedCountry.code)}
                  <span>{t("pickCountryOnly").replace("{country}", selectedCountry.name)}</span>
                </button>
                <p className="panel-note">{t("pickCountryOnlyHint")}</p>
              </div>
            ) : null}
            <div className="airport-search qs-airport-modal__search" role="search">
              <svg className="qs-airport-modal__search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <circle cx="7" cy="7" r="5.25" stroke="currentColor" strokeWidth="1.5" />
                <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              <input
                ref={airportSearchInputRef}
                className="qs-input qs-airport-modal__search-input"
                name="airport_search"
                autoComplete="off"
                value={airportSearch}
                onChange={(e) => setAirportSearch(e.target.value)}
                placeholder={t("pickSearch")}
                aria-label={t("pickSearch")}
              />
            </div>
            {(activePicker === "origin" ? originRecentAirports : destinationRecentAirports).length > 0 ? (
              <div className="airport-recent qs-airport-modal__recents">
                <span className="qs-airport-modal__recents-label">{t("pickRecent")}</span>
                <div className="airport-recent-grid">
                  {(activePicker === "origin" ? originRecentAirports : destinationRecentAirports).map((iata) => (
                    <button key={`recent-${iata}`} type="button" className="qs-airport-modal__recent-chip" onClick={() => selectAirport(iata)}>
                      {iata}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="airport-list">
              {filteredCountryAirports.map((airport) => (
                <button key={airport.iata} type="button" className="qs-airport-modal__airport-item" onClick={() => selectAirport(airport.iata)}>
                  {renderFlag(selectedCountry?.code || null)}
                  <span className="qs-airport-modal__airport-name">{airport.municipality || airport.name}</span>
                  <span className="qs-airport-modal__airport-iata">{airport.iata}</span>
                </button>
              ))}
              {countryAirports.length === 0 ? (
                <div className="qs-airport-modal__empty">
                  <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                    <circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="1.5" opacity="0.35" />
                    <path d="M12 20c1.2-2.4 6.8-2.4 8 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
                    <circle cx="12" cy="14" r="1.2" fill="currentColor" opacity="0.4" />
                    <circle cx="20" cy="14" r="1.2" fill="currentColor" opacity="0.4" />
                  </svg>
                  <p>{t("pickEmpty")}</p>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </div>
  ) : null;
  const originVisibleSuggestions = origin.trim() ? originSuggestions : originRecentAirportSuggestions;
  const destinationVisibleSuggestions = destination.trim() ? destinationSuggestions : destinationRecentAirportSuggestions;
  const activeSuggestions = activeAutocompleteField === "origin"
    ? originVisibleSuggestions
    : activeAutocompleteField === "destination"
      ? destinationVisibleSuggestions
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
  const routeInputsValid = originValid && destinationValid;
  const returnDateInvalid = Boolean(isReturn && travelDate && returnDate && returnDate < travelDate);
  // Dual-mode flag (Fase 6) ─ after routeInputsValid to avoid TDZ
  const isDualMode = isReturn && !!returnDate && !!travelDate && routeInputsValid && !originCountryOnly && !destinationCountryOnly;

  // ── Per-side emptyCausesExpanded reset on dual mode exit (Fase 11) ──
  useEffect(() => {
    if (!isDualMode) {
      setDualHoverSide(null);
      setOutboundEmptyCausesExpanded(false);
      setReturnEmptyCausesExpanded(false);
    }
  }, [isDualMode]);

  // ── Side state cleanup when exiting dual mode (Fase 6) ─────────────
  const wasDualModeRef = useRef(isDualMode);
  useEffect(() => {
    if (wasDualModeRef.current && !isDualMode) {
      outboundSide.reset();
      returnSide.reset();
      saveCombination.reset();
      setOutboundFareProfile(createEmptyFareComparisonProfile(adults));
      setReturnFareProfile(createEmptyFareComparisonProfile(adults));
      setOutboundViewState(defaultSideViewState);
      setReturnViewState(defaultSideViewState);
    }
    wasDualModeRef.current = isDualMode;
  }, [adults, defaultSideViewState, isDualMode, outboundSide, returnSide, saveCombination]);

  useEffect(() => {
    if (saveCombination.status === "saved") {
      const savedResults = pendingCombinationResultsRef.current;
      if (savedResults?.outbound) markAsSaved(savedResults.outbound, saveCombination.outboundWatchId);
      if (savedResults?.return) markAsSaved(savedResults.return, saveCombination.returnWatchId);
      notify({
        tone: "success",
        title: t("combinationSaved"),
        actionLabel: t("viewWatchlist"),
        onAction: () => navigateToWatchlistWithContext(origin, destination, travelDate, saveCombination.outboundWatchId),
        durationMs: 3200,
      });
      pendingCombinationResultsRef.current = null;
      saveCombination.reset();
      return;
    }
    if (saveCombination.status === "partial") {
      notify({
        tone: "warning",
        title: t("combinationPartial"),
        durationMs: 3600,
      });
      pendingCombinationResultsRef.current = null;
      saveCombination.reset();
      return;
    }
    if (saveCombination.status === "error") {
      notify({
        tone: "error",
        title: t("combinationError"),
        durationMs: 3600,
      });
      pendingCombinationResultsRef.current = null;
      saveCombination.reset();
    }
  }, [
    destination,
    markAsSaved,
    navigateToWatchlistWithContext,
    notify,
    origin,
    saveCombination,
    t,
    travelDate,
  ]);

  // edited criteria signature drives the dirty-state check against last applied criteria
  const currentCriteriaSignature = useMemo(() => buildCriteriaSignature({
    origin,
    destination,
    additionalOrigins: additionalOrigins.map((entry) => entry.value),
    additionalDestinations: additionalDestinations.map((entry) => entry.value),
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
    additionalOrigins,
    additionalDestinations,
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
  const pendingActionVisibility = getPendingActionVisibility(pendingSearchChanges);

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
  const searchCtaHint = isLoading || isSubmitting
    ? t("searchHintLoading")
    : !isReady
      ? searchDisabledHint
      : radiusActive
        ? t("searchHintReadyNearby")
        : t("searchHintReadyExact");
  const summaryMissingBadges = [
    !origin.trim() && !originCountryOnly ? t("summaryMissingOrigin") : null,
    !destination.trim() && !destinationCountryOnly ? t("summaryMissingDestination") : null,
    !travelDate ? t("summaryMissingDate") : null,
    tripType === "round_trip_incomplete" ? t("summaryRoundTripMissingReturn") : null,
  ].filter((value): value is string => Boolean(value));
  const summaryDate = travelDate ? formatShortDate(travelDate) : "--";
  const summaryOriginLabel = originCountryOnly ? originCountryOnly.name : (origin || "---");
  const summaryDestinationLabel = destinationCountryOnly ? destinationCountryOnly.name : (destination || "---");
  const summaryTrip = `${summaryOriginLabel} -> ${summaryDestinationLabel}`;
  const summaryTripTypeLabel = tripType === "one_way"
    ? t("summaryOneWay")
    : tripType === "round_trip"
      ? t("summaryRoundTrip")
      : t("summaryRoundTripMissingReturn");
  const summaryMeta = `${adults} ${adults === 1 ? t("summaryPassengersSingular") : t("summaryPassengersPlural")} - ${
    summaryTripTypeLabel
  } - ${summaryDate}`;
  const roundTripHelperCopy = !isReturn
    ? t("roundTripToggleHint")
    : tripType === "round_trip"
      ? t("roundTripReadyHint")
      : t("selectReturnHint");
  const passengersSummaryLabel = `${adults} ${adults === 1 ? t("summaryPassengersSingular") : t("summaryPassengersPlural")}`;
  const flexPreset = getQuickSearchFlexPreset(daysBefore, daysAfter);
  const summaryFlex = formatQuickSearchFlexSummary(daysBefore, daysAfter, {
    exact: t("exactDate"),
    plusOne: t("flexPresetOne"),
    plusTwo: t("flexPresetTwo"),
    plusThree: t("flexPresetThree"),
    customTemplate: t("flexCustomSummary"),
  });
  const summaryDurationValue = parseNumericInput(durationMax, { min: 1 });
  const summaryDuration = summaryDurationValue !== null && Number.isFinite(summaryDurationValue)
    ? `${t("summaryDurationMax")} ${summaryDurationValue} min`
    : t("summaryDurationOpen");
  const compactSummaryChips = useMemo<QuickSearchSummaryChip[]>(() => {
    const chips: QuickSearchSummaryChip[] = [];
    const routeLabel = origin.trim() && destination.trim()
      ? `${origin.trim().toUpperCase()} -> ${destination.trim().toUpperCase()}`
      : `${summaryOriginLabel} -> ${summaryDestinationLabel}`;
    chips.push({
      id: "route",
      label: `${t("summaryRouteExact")}: ${routeLabel}`,
      tone: "route",
    });
    if (includeNearbyOrigins) {
      chips.push({ id: "nearby-origin", label: t("summaryNearbyOrigin"), tone: "search" });
    }
    if (includeNearbyDestinations) {
      chips.push({ id: "nearby-destination", label: t("summaryNearbyDestination"), tone: "search" });
    }
    if (radiusActive) {
      chips.push({
        id: "radius",
        label: t("summaryDistanceUpTo").replace("{km}", String(radiusKm)),
        tone: "search",
        emphasis: summaryHighlightKey === "radius",
      });
    }
    if (travelDate) {
      chips.push({ id: "date", label: `${t("summaryExactDateChip")}: ${summaryDate}`, tone: "route" });
    }
    if (daysBefore > 0 || daysAfter > 0) {
      if (daysBefore === daysAfter) {
        chips.push({
          id: "date-flex",
          label: t("summaryFlexChip").replace("{days}", `+/-${daysBefore}`),
          tone: "search",
        });
      } else {
        chips.push({
          id: "date-flex-custom",
          label: t("summaryFlexCustomChip").replace("{before}", String(daysBefore)).replace("{after}", String(daysAfter)),
          tone: "search",
        });
      }
    }
    if (durationMax) {
      chips.push({
        id: "duration",
        label: summaryDuration,
        tone: "search",
        emphasis: summaryHighlightKey === "duration",
      });
    }
    chips.push({ id: "passengers", label: passengersSummaryLabel, tone: "route" });
    if (includeStops) {
      chips.push({ id: "separate-flights", label: t("summarySeparateFlights"), tone: "advanced" });
    }
    if (!strictFilters) {
      chips.push({
        id: "strict",
        label: t("summaryIncompleteInfo"),
        tone: "advanced",
        emphasis: summaryHighlightKey === "strict",
      });
    }
    const avoidedIata = Array.from(new Set([...excludeOrigins, ...excludeDestinations])).join(", ");
    if (avoidedIata) {
      chips.push({
        id: "exclusions",
        label: t("summaryAvoids").replace("{iata}", avoidedIata),
        tone: "result",
        emphasis: summaryHighlightKey === "exclusions",
      });
    }
    return chips;
  }, [
    origin,
    destination,
    summaryOriginLabel,
    summaryDestinationLabel,
    includeNearbyOrigins,
    includeNearbyDestinations,
    radiusActive,
    radiusKm,
    daysBefore,
    daysAfter,
    durationMax,
    summaryDuration,
    travelDate,
    summaryDate,
    passengersSummaryLabel,
    includeStops,
    strictFilters,
    excludeOrigins,
    excludeDestinations,
    summaryHighlightKey,
    t,
  ]);
  const effectiveFlexCustomPanelOpen = flexCustomPanelOpen || flexPreset === "custom";
  const flexHelperText = effectiveFlexCustomPanelOpen
    ? t("flexHelperCustom")
    : flexPreset === "exact"
      ? t("flexHelperExact")
      : t("flexHelperFlexible");
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
  const totalFlightsForLoader = Math.max(0, loaderResolvedTotalFlights ?? loaderPlannedTotalFlights);
  const currentFlightsForLoader = totalFlightsForLoader > 0
    ? Math.min(totalFlightsForLoader, Math.round((progressPercent / 100) * totalFlightsForLoader))
    : 0;
  const loadingTotalText = t("loadingTotalFlights").replace("{count}", formatNumber(totalFlightsForLoader, {}, localeTag));
  const loadingProgressText = t("loadingProgressFlights")
    .replace("{current}", formatNumber(currentFlightsForLoader, {}, localeTag))
    .replace("{total}", formatNumber(totalFlightsForLoader, {}, localeTag));
  const loadingScopeText = t("loadingScope")
    .replace("{routes}", formatNumber(loaderScopeRoutes, {}, localeTag))
    .replace("{days}", formatNumber(loaderScopeDates, {}, localeTag));
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
    airportsByIata,
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
  const sortLabel = {
    ranking: t("sortRanking"),
    price: t("sortPrice"),
    duration: t("sortDuration"),
    freshness: t("sortFreshness"),
  } as const;
  const originCountry = resolveInputCountryCode(originCountryOnly?.code, originSelectedCountryCode);
  const destinationCountry = resolveInputCountryCode(destinationCountryOnly?.code, destinationSelectedCountryCode);
  const deeplinkUrl = deepLink?.url || deepLink?.fallback_url || localRyanairUrl;
  const {
    durationMaxNumber,
    visibleResults,
    warningSeverity,
    groupedNeutralWarnings,
    groupedCriticalWarnings,
    providerPartialInlineNotice,
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
    sortBy,
    filtersNotice,
    filtersWarningCodes,
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
  const updateOutboundViewState = useCallback((patch: Partial<QuickSearchVisibleFiltersState>) => {
    setOutboundViewState((prev) => ({ ...prev, ...patch }));
  }, []);
  const updateReturnViewState = useCallback((patch: Partial<QuickSearchVisibleFiltersState>) => {
    setReturnViewState((prev) => ({ ...prev, ...patch }));
  }, []);
  const resetOutboundViewState = useCallback(() => {
    setOutboundViewState(defaultSideViewState);
  }, [defaultSideViewState]);
  const resetReturnViewState = useCallback(() => {
    setReturnViewState(defaultSideViewState);
  }, [defaultSideViewState]);
  const outboundPanelState = useQuickSearchScreenState({
    results: outboundSide.results,
    priceMin: outboundViewState.priceMin,
    priceMax: outboundViewState.priceMax,
    durationMax: outboundViewState.durationMax,
    sortBy: outboundViewState.sortBy,
    filtersNotice: outboundSide.filtersNotice,
    filtersWarningCodes: outboundSide.filtersWarningCodes,
    filtersMeta: outboundSide.filtersMeta,
    isDegraded: outboundSide.isDegraded,
    searchMeta: outboundSide.searchMeta,
    weatherMessage: outboundSide.weatherMessage,
    strictFilters,
    includeStops,
    radiusActive,
    radiusKm,
    excludeOriginsCount: excludeOrigins.length,
    excludeDestinationsCount: excludeDestinations.length,
    departAfter,
    departBefore,
    emptyCausesExpanded: false,
    t,
    tWarn,
  });
  const returnPanelState = useQuickSearchScreenState({
    results: returnSide.results,
    priceMin: returnViewState.priceMin,
    priceMax: returnViewState.priceMax,
    durationMax: returnViewState.durationMax,
    sortBy: returnViewState.sortBy,
    filtersNotice: returnSide.filtersNotice,
    filtersWarningCodes: returnSide.filtersWarningCodes,
    filtersMeta: returnSide.filtersMeta,
    isDegraded: returnSide.isDegraded,
    searchMeta: returnSide.searchMeta,
    weatherMessage: returnSide.weatherMessage,
    strictFilters,
    includeStops,
    radiusActive,
    radiusKm,
    excludeOriginsCount: excludeOrigins.length,
    excludeDestinationsCount: excludeDestinations.length,
    departAfter,
    departBefore,
    emptyCausesExpanded: false,
    t,
    tWarn,
  });
  const dualCombinationVisible =
    outboundSide.searchState === "success"
    && returnSide.searchState === "success"
    && outboundPanelState.visibleResults.length > 0
    && returnPanelState.visibleResults.length > 0;

  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 10;

  const resultsSignature = useMemo(() => {
    return `${priceMin}:${priceMax}:${durationMax}:${sortBy}:${strictFilters}:${includeStops}:${radiusKm}:${departAfter}:${departBefore}:${daysBefore}:${daysAfter}:${origin}:${destination}:${travelDate}:${returnDate}:${isReturn}`;
  }, [
    priceMin,
    priceMax,
    durationMax,
    sortBy,
    strictFilters,
    includeStops,
    radiusKm,
    departAfter,
    departBefore,
    daysBefore,
    daysAfter,
    origin,
    destination,
    travelDate,
    returnDate,
    isReturn,
  ]);

  useEffect(() => {
    setCurrentPage(1);
  }, [resultsSignature]);

  const backendPagination = searchMeta?.pagination;
  const totalPages = Math.max(1, Number(backendPagination?.total_pages || 1));
  const activePage = Math.min(Math.max(1, currentPage), totalPages);
  const pageSize = Math.max(1, Number(backendPagination?.page_size || PAGE_SIZE));
  const totalResults = Math.max(0, Number(backendPagination?.total_results || visibleResults.length));
  const canExportQuickSearch = Boolean(lastQuickSearchPayloadRef.current)
    && searchState === "success"
    && totalResults > 0
    && !isLoading
    && !isExportingQuickSearch;

  const explainChipLabel = showDegradedState ? t("degradedChip") : t("toolbarExplain");
  const warningGroupedTitle = t("warningsGroupedTitle");
  const warningProblemTitle = t("warningProblemTitle");
  const providerPartialInlineMessages = QUICK_SEARCH_PROVIDER_PARTIAL_INLINE_WARNING_CODES.map((code) => tWarn(code));
  const providerTotalWarningMessages = [
    ...QUICK_SEARCH_PROVIDER_TOTAL_OUTAGE_WARNING_CODES,
    ...QUICK_SEARCH_PROVIDER_ERROR_WARNING_CODES,
  ].map((code) => tWarn(code));
  const providerPartialWarnings = groupedNeutralWarnings.filter((group) =>
    providerPartialInlineMessages.includes(group.message),
  );
  const providerPartialInlineText = providerPartialInlineNotice
    ?? (
      providerPartialWarnings.length > 0
        ? providerPartialWarnings.map((group) => `${group.message}${group.count > 1 ? ` (${group.count})` : ""}`).join(" ")
        : ""
    );
  const providerTotalWarnings = groupedCriticalWarnings.filter((group) =>
    providerTotalWarningMessages.includes(group.message),
  );

  useEffect(() => {
    if (!hasSearched || sourcesSummary.entries.length === 0) return;
    const key = `${jobId || "nojob"}:${sourcesSummary.entries.map((entry) => `${entry.label}:${entry.count}`).join("|")}`;
    if (sourcesShownKeyRef.current === key) return;
    trackEvent("quicksearch_sources_aggregated_shown", {
      sources_count: sourcesSummary.entries.length,
      results_count: visibleResults.length,
    });
    sourcesShownKeyRef.current = key;
  }, [hasSearched, jobId, sourcesSummary.entries, visibleResults.length, sourcesShownKeyRef]);

  useEffect(() => {
    if (!hasSearched) return;
    const freshnessMode = globalFreshness.isUnavailable ? "unavailable" : globalFreshness.status;
    const freshnessObservedAt = globalFreshness.observedAt || "none";
    const key = `${jobId || "nojob"}:${freshnessMode}:${freshnessObservedAt}`;
    if (freshnessShownKeyRef.current === key) return;
    trackEvent("quicksearch_freshness_global_shown", { mode: freshnessMode });
    freshnessShownKeyRef.current = key;
  }, [globalFreshness.isUnavailable, globalFreshness.observedAt, globalFreshness.status, hasSearched, jobId, freshnessShownKeyRef]);

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
    if (radiusActive && radiusKm !== QUICK_SEARCH_RADIUS_DEFAULT) {
      chips.push({
        id: "radius",
        label: `${t("radiusLabel")}: ${radiusKm} km`,
        onClear: () => setRadiusKm(QUICK_SEARCH_RADIUS_DEFAULT),
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
    if (departAfter !== "07:00") {
      chips.push({
        id: "depart-after",
        label: `${t("departAfter")}: ${departAfter}`,
        onClear: () => setDepartAfter("07:00"),
      });
    }
    if (departBefore !== "22:00") {
      chips.push({
        id: "depart-before",
        label: `${t("departBefore")}: ${departBefore}`,
        onClear: () => setDepartBefore("22:00"),
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
    if (bufferMin) {
      chips.push({
        id: "buffer-min",
        label: `${t("bufferMin")}: ${bufferMin}`,
        onClear: () => setBufferMin(""),
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
    departAfter,
    departBefore,
    strictFilters,
    includeStops,
    maxStops,
    bufferMin,
    excludeOrigins,
    excludeDestinations,
    t,
    setDaysAfter,
    setDaysBefore,
    setFlexCustomPanelOpen,
    setDurationMax,
    setDepartAfter,
    setDepartBefore,
    setExcludeDestinations,
    setExcludeOrigins,
    setIncludeNearbyDestinations,
    setIncludeNearbyOrigins,
    setIncludeStops,
    setBufferMin,
    setPriceMax,
    setPriceMin,
    setRadiusKm,
    setStrictFilters,
  ]);

  const [relaxPreviewOpen, setRelaxPreviewOpen] = useState(false);

  const relaxPreviewChanges = useMemo(() => {
    const rows: Array<{ id: string; label: string; before: string; after: string }> = [];
    if (strictFilters) {
      rows.push({ id: "strict", label: t("strictMode"), before: t("summaryStrictOn"), after: t("summaryStrictOff") });
    }
    if (priceMin) {
      rows.push({ id: "priceMin", label: t("priceMin"), before: priceMin, after: "â€”" });
    }
    if (priceMax) {
      rows.push({ id: "priceMax", label: t("priceMax"), before: priceMax, after: "â€”" });
    }
    return rows;
  }, [strictFilters, priceMin, priceMax, t]);

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
    } else if (undoPayload.action === "open_date_flex" || undoPayload.action === "try_plus_1_day") {
      setDaysBefore(undoPayload.daysBefore);
      setDaysAfter(undoPayload.daysAfter);
      setApplyFlexReturn(undoPayload.applyFlexReturn);
    } else if (undoPayload.action === "open_nearby" || undoPayload.action === "max_coverage") {
      setIncludeNearbyOrigins(undoPayload.includeNearbyOrigins);
      setIncludeNearbyDestinations(undoPayload.includeNearbyDestinations);
      setRadiusKm(undoPayload.radiusKm);
    } else if (undoPayload.action === "clear_exclusions") {
      setExcludeOrigins(undoPayload.excludeOrigins);
      setExcludeDestinations(undoPayload.excludeDestinations);
      setExcludeOriginInput(undoPayload.excludeOriginInput);
      setExcludeDestinationInput(undoPayload.excludeDestinationInput);
    }

    trackEvent("quicksearch_relax_undo_clicked", { action: undoPayload.action });
    setSummaryHighlightKey(RELAX_HIGHLIGHT_BY_ACTION[undoPayload.action]);
    relaxUndoRef.current = null;
  }, [
    relaxUndoRef,
    setDurationMax,
    setExcludeDestinationInput,
    setExcludeDestinations,
    setExcludeOriginInput,
    setExcludeOrigins,
    setDaysAfter,
    setDaysBefore,
    setIncludeNearbyDestinations,
    setIncludeNearbyOrigins,
    setRadiusKm,
    setApplyFlexReturn,
    setStrictFilters,
    setSummaryHighlightKey,
  ]);

  const onZeroResultRelaxAction = useCallback((action: ZeroResultRelaxAction) => {
    trackEvent("quicksearch_zero_results_relax_clicked", { action });
    const actionLabelMap: Record<ZeroResultRelaxAction, string> = {
        disable_strict: t("emptyActionDisableStrict"),
        increase_duration: t("emptyActionIncreaseDuration"),
        open_radius_150: t("emptyActionOpenRadius"),
        clear_exclusions: t("emptyActionClearExclusions"),
        open_date_flex: t("emptyActionDateFlex"),
        try_plus_1_day: t("emptyActionTryPlus1Day"),
        open_nearby: t("emptyActionOpenNearby"),
        max_coverage: t("emptyActionMaxCoverage"),
        open_more_options: t("emptyActionMoreOptions"),
      };

    if (action === "disable_strict") {
      relaxUndoRef.current = { action, strictFilters };
      setStrictFilters(false);
    } else if (action === "increase_duration") {
      if (durationMaxNumber === null) return;
      relaxUndoRef.current = { action, durationMax };
      setDurationMax(String(durationMaxNumber + 60));
    } else if (action === "open_radius_150") {
      relaxUndoRef.current = { action, includeNearbyOrigins, includeNearbyDestinations, radiusKm };
      setIncludeNearbyOrigins(true);
      setIncludeNearbyDestinations(true);
      setRadiusKm(150);
    } else if (action === "open_date_flex") {
      relaxUndoRef.current = { action, daysBefore, daysAfter, applyFlexReturn };
      setDaysBefore(Math.max(2, daysBefore));
      setDaysAfter(Math.max(2, daysAfter));
      setApplyFlexReturn(true);
    } else if (action === "clear_exclusions") {
      relaxUndoRef.current = { action, excludeOrigins, excludeDestinations, excludeOriginInput, excludeDestinationInput };
      setExcludeOrigins([]);
      setExcludeDestinations([]);
      setExcludeOriginInput("");
      setExcludeDestinationInput("");
    } else if (action === "try_plus_1_day") {
      relaxUndoRef.current = { action, daysBefore, daysAfter, applyFlexReturn };
      setDaysBefore(1);
      setDaysAfter(1);
    } else if (action === "open_nearby") {
      relaxUndoRef.current = { action, includeNearbyOrigins, includeNearbyDestinations, radiusKm };
      setIncludeNearbyOrigins(true);
      setIncludeNearbyDestinations(true);
    } else if (action === "max_coverage") {
      relaxUndoRef.current = { action, includeNearbyOrigins, includeNearbyDestinations, radiusKm };
      setIncludeNearbyOrigins(true);
      setIncludeNearbyDestinations(true);
      setRadiusKm(250);
    } else if (action === "open_more_options") {
      setIsAdvancedOpen(true);
      return; // UI action only
    }

    setSummaryHighlightKey(RELAX_HIGHLIGHT_BY_ACTION[action]);
    notify({
      tone: "success",
      title: `${t("relaxToastPrefix")} ${actionLabelMap[action]}`,
      actionLabel: t("undoAction"),
      onAction: () => undoZeroResultRelaxAction(action),
      durationMs: 3200,
    });
  }, [
    t,
    strictFilters,
    durationMax,
    durationMaxNumber,
    includeNearbyOrigins,
    includeNearbyDestinations,
    radiusKm,
    daysBefore,
    daysAfter,
    applyFlexReturn,
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
    setDaysAfter,
    setDaysBefore,
    setIncludeNearbyDestinations,
    setIncludeNearbyOrigins,
    setRadiusKm,
    setApplyFlexReturn,
    setStrictFilters,
    setSummaryHighlightKey,
    notify,
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
  const visualSearchState = getQuickSearchVisualState({
    searchState,
    showLoader,
    loadingVisualHold,
    visibleResultsCount: visibleResults.length,
  });
  const isVisualLoading = visualSearchState === "loading";
  const isIdleVisualState = visualSearchState === "idle";
  const hasFinalResults = visualSearchState === "success_with_results";
  const hasFinalEmptyState = visualSearchState === "success_empty";
  const showResultsWorkspace = !isIdleVisualState;
  const showResultsStagehead = !isVisualLoading;
  const showResultsList = hasFinalResults;
  const showResultsToolbar = hasFinalResults;
  const panelSearchState =
    hasFinalEmptyState
      ? "empty"
      : hasFinalResults
        ? "success"
        : visualSearchState;
  const resultsStageTitle =
    isVisualLoading
      ? t("loadingTitle")
      : hasFinalEmptyState
        ? emptyStateMainTitle
        : hasFinalResults
          ? `${totalResults} ${t("results")}`
          : visualSearchState === "error"
            ? t("errorTitle")
            : visualSearchState === "rate"
              ? t("rateLimitTitle")
              : t("searchReadyTitle");
  const runSearch = () => {
    void onSubmit({ preventDefault: () => {} } as FormEvent, { page: 1 });
  };

  const handleSortChange = (nextSortBy: QuickSearchSortBy) => {
    setSortBy(nextSortBy);
    setCurrentPage(1);
    if (hasSearched && !isDualMode) {
      void onSubmit({ preventDefault: () => {} } as FormEvent, { page: 1, sortBy: nextSortBy });
    }
  };

  const goToPage = (nextPage: number) => {
    const bounded = Math.min(totalPages, Math.max(1, nextPage));
    setCurrentPage(bounded);
    void onSubmit({ preventDefault: () => {} } as FormEvent, {
      page: bounded,
      sortBy,
      presentation: "page",
    });
    const el = document.querySelector(".qs-results-panel");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const removeExcludeOriginChip = useCallback((iata: string) => {
    removeChip(iata, excludeOrigins, setExcludeOrigins);
  }, [excludeOrigins, setExcludeOrigins]);

  const removeExcludeDestinationChip = useCallback((iata: string) => {
    removeChip(iata, excludeDestinations, setExcludeDestinations);
  }, [excludeDestinations, setExcludeDestinations]);

  const toggleEmptyCauses = useCallback(() => {
    setEmptyCausesExpanded((prev) => !prev);
  }, [setEmptyCausesExpanded]);

  const trackRowOverflow = useCallback((rowId: string) => {
    trackEvent("quicksearch_row_overflow_opened", { row_id: rowId });
  }, []);

  const trackCopyParams = useCallback((rowId: string) => {
    trackEvent("quicksearch_row_copy_params_clicked", { row_id: rowId });
  }, []);


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
                    const nextValue = e.target.value.toUpperCase();
                    setOrigin(nextValue);
                    setOriginCountryOnly(null);
                    setOriginSelectedCountryCode(null);
                    setFieldErrors((prev) => ({ ...prev, origin_iata: undefined }));
                    setActiveAutocompleteField("origin");
                    setActiveAutocompleteIndex(-1);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "ArrowDown") {
                      event.preventDefault();
                      if (originVisibleSuggestions.length === 0) return;
                      setActiveAutocompleteField("origin");
                      setActiveAutocompleteIndex((prev) => {
                        if (prev < 0) return 0;
                        return (prev + 1) % originVisibleSuggestions.length;
                      });
                      return;
                    }
                    if (event.key === "ArrowUp") {
                      event.preventDefault();
                      if (originVisibleSuggestions.length === 0) return;
                      setActiveAutocompleteField("origin");
                      setActiveAutocompleteIndex((prev) => {
                        if (prev <= 0) return originVisibleSuggestions.length - 1;
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
                        ? originVisibleSuggestions[activeAutocompleteIndex]
                        : originVisibleSuggestions[0] || null;
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
                  placeholder={originCountryOnly ? originCountryOnly.name : randomOriginPlaceholder}
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
                {activeAutocompleteField === "origin" && originVisibleSuggestions.length > 0 ? (
                  <ul
                    className={!origin.trim() ? "qs-autocomplete qs-autocomplete-recents" : "qs-autocomplete"}
                    id="origin-suggestions"
                    role="listbox"
                  >
                    {!origin.trim() ? (
                      <li className="qs-autocomplete-group-label">{t("recentAutocompleteLabel")}</li>
                    ) : null}
                    {originVisibleSuggestions.map((suggestion, index) => {
                      const isActive = index === activeAutocompleteIndex;
                      return (
                        <li key={`origin-${suggestion.iata}`} role="option" aria-selected={isActive}>
                          <div className={!origin.trim() ? "qs-recent-row" : undefined}>
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
                            {!origin.trim() ? (
                              <button
                                type="button"
                                className="qs-recent-remove"
                                aria-label={t("removeRecentAirportAria").replace("{iata}", suggestion.iata)}
                                onMouseDown={(event) => event.preventDefault()}
                                onClick={() => removeRecentAirportSelection("origin", suggestion.iata)}
                              >
                                <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                                  <path
                                    d="M7 7l10 10M17 7 7 17"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="1.8"
                                    strokeLinecap="round"
                                  />
                                </svg>
                              </button>
                            ) : null}
                          </div>
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
            <PopularDestinationsChips
              origin={origin}
              onSelectDestination={(iata) => selectAutocompleteSuggestion("destination", iata)}
              t={(key, params) => t(key as Parameters<typeof t>[0], params)}
            />
            <QuickSearchAdditionalAirports
              side="origin"
              entries={additionalOrigins}
              focusEntryId={additionalFocusEntryId}
              airportsByIata={airportsByIata}
              recentSuggestions={originRecentAirportSuggestions}
              addLabel={t("addAnotherOrigin")}
              inputLabel={t("additionalOriginInput")}
              removeLabel={t("removeAdditionalOrigin")}
              pickerLabel={t("pickAirportOriginAria")}
              invalidLabel={t("additionalAirportInvalid")}
              recentLabel={t("recentAutocompleteLabel")}
              maxEntries={5}
              fetchSuggestions={fetchAutocompleteSuggestions}
              onAdd={() => addAdditionalAirport("origin")}
              onChange={(id, value) => updateAdditionalAirport("origin", id, value)}
              onRemove={(id) => removeAdditionalAirport("origin", id)}
              onSelect={(id, iata) => {
                updateAdditionalAirport("origin", id, iata);
                rememberAirportSelection("origin", iata);
              }}
              onOpenPicker={(id, trigger) => openAdditionalPicker("origin", id, trigger)}
            />
          </div>

          <div className="qs-route-line">
            <button
              type="button"
              className="qs-route-swap"
              onClick={swapRouteInputs}
              aria-label={t("swapRouteAria")}
              title={t("swapRoute")}
            >
              <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                <path
                  d="M7 7h10m0 0-3-3m3 3-3 3M17 17H7m0 0 3 3m-3-3 3-3"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
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
                    const nextValue = e.target.value.toUpperCase();
                    setDestination(nextValue);
                    setDestinationCountryOnly(null);
                    setDestinationSelectedCountryCode(null);
                    setFieldErrors((prev) => ({ ...prev, destination_iata: undefined }));
                    setActiveAutocompleteField("destination");
                    setActiveAutocompleteIndex(-1);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "ArrowDown") {
                      event.preventDefault();
                      if (destinationVisibleSuggestions.length === 0) return;
                      setActiveAutocompleteField("destination");
                      setActiveAutocompleteIndex((prev) => {
                        if (prev < 0) return 0;
                        return (prev + 1) % destinationVisibleSuggestions.length;
                      });
                      return;
                    }
                    if (event.key === "ArrowUp") {
                      event.preventDefault();
                      if (destinationVisibleSuggestions.length === 0) return;
                      setActiveAutocompleteField("destination");
                      setActiveAutocompleteIndex((prev) => {
                        if (prev <= 0) return destinationVisibleSuggestions.length - 1;
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
                        ? destinationVisibleSuggestions[activeAutocompleteIndex]
                        : destinationVisibleSuggestions[0] || null;
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
                  placeholder={destinationCountryOnly ? destinationCountryOnly.name : randomDestinationPlaceholder}
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
                {activeAutocompleteField === "destination" && destinationVisibleSuggestions.length > 0 ? (
                  <ul
                    className={!destination.trim() ? "qs-autocomplete qs-autocomplete-recents" : "qs-autocomplete"}
                    id="destination-suggestions"
                    role="listbox"
                  >
                    {!destination.trim() ? (
                      <li className="qs-autocomplete-group-label">{t("recentAutocompleteLabel")}</li>
                    ) : null}
                    {destinationVisibleSuggestions.map((suggestion, index) => {
                      const isActive = index === activeAutocompleteIndex;
                      return (
                        <li key={`destination-${suggestion.iata}`} role="option" aria-selected={isActive}>
                          <div className={!destination.trim() ? "qs-recent-row" : undefined}>
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
                            {!destination.trim() ? (
                              <button
                                type="button"
                                className="qs-recent-remove"
                                aria-label={t("removeRecentAirportAria").replace("{iata}", suggestion.iata)}
                                onMouseDown={(event) => event.preventDefault()}
                                onClick={() => removeRecentAirportSelection("destination", suggestion.iata)}
                              >
                                <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                                  <path
                                    d="M7 7l10 10M17 7 7 17"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="1.8"
                                    strokeLinecap="round"
                                  />
                                </svg>
                              </button>
                            ) : null}
                          </div>
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
            <PopularDestinationsChips
              origin={destination}
              onSelectDestination={(iata) => selectAutocompleteSuggestion("origin", iata)}
              t={(key, params) => t(key as Parameters<typeof t>[0], params)}
            />
            <QuickSearchAdditionalAirports
              side="destination"
              entries={additionalDestinations}
              focusEntryId={additionalFocusEntryId}
              airportsByIata={airportsByIata}
              recentSuggestions={destinationRecentAirportSuggestions}
              addLabel={t("addAnotherDestination")}
              inputLabel={t("additionalDestinationInput")}
              removeLabel={t("removeAdditionalDestination")}
              pickerLabel={t("pickAirportDestinationAria")}
              invalidLabel={t("additionalAirportInvalid")}
              recentLabel={t("recentAutocompleteLabel")}
              maxEntries={5}
              fetchSuggestions={fetchAutocompleteSuggestions}
              onAdd={() => addAdditionalAirport("destination")}
              onChange={(id, value) => updateAdditionalAirport("destination", id, value)}
              onRemove={(id) => removeAdditionalAirport("destination", id)}
              onSelect={(id, iata) => {
                updateAdditionalAirport("destination", id, iata);
                rememberAirportSelection("destination", iata);
              }}
              onOpenPicker={(id, trigger) => openAdditionalPicker("destination", id, trigger)}
            />
          </div>
        </div>
        
        <QuickSearchNearbyBand
          includeNearbyOrigins={includeNearbyOrigins}
          includeNearbyDestinations={includeNearbyDestinations}
          radiusKm={radiusKm}
          t={t}
          setIncludeNearbyOrigins={setIncludeNearbyOrigins}
          setIncludeNearbyDestinations={setIncludeNearbyDestinations}
          setRadiusKm={updateRadiusKm}
        />
        <div className="qs-passengers">
          <div className="qs-passengers-copy">
            <span className="qs-passengers-title">{t("passengers")}</span>
            <small className="qs-search-hint">{t("passengersHint")}</small>
          </div>
          <div className="qs-stepper" aria-label={t("passengersStepperAria").replace("{count}", String(adults))}>
            <button
              type="button"
              aria-label={t("passengersStepperDecrease")}
              onClick={() => changeAdults(-1)}
              disabled={adults <= 1}
            >
              -
            </button>
            <span className="qs-stepper-value" aria-live="polite">
              <strong>{adults}</strong>
              <small>{passengersSummaryLabel}</small>
            </span>
            <button
              type="button"
              aria-label={t("passengersStepperIncrease")}
              onClick={() => changeAdults(1)}
              disabled={adults >= 9}
            >
              +
            </button>
          </div>
          <small className="qs-search-hint qs-passengers-note">{t("passengersBaseFareHint")}</small>
        </div>

        <div className={`qs-date-grid${isReturn ? " has-return" : ""}`}>
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
              min={minTravelDate}
              dayHintsByIso={calendarHintsActive?.dayHintsByIso || {}}
              hintsLoading={calendarHintsLoadingKey === calendarHintsRequestKey}
              showCountryEstimateBadge={canRequestCalendarHints && hasCountryScopeForCalendarHints}
              hintScopeMode={calendarHintsActive?.scopeMode || calendarHintsScopeMode}
              onVisibleMonthChange={setCalendarVisibleMonth}
              multiple={!isReturn}
              selectedValues={selectedTravelDates}
              maxSelections={15}
              onSelectedValuesChange={(values) => {
                const normalizedDates = Array.from(new Set(values)).sort().slice(0, 15);
                setSelectedTravelDates(normalizedDates);
                setDaysBefore(0);
                setDaysAfter(0);
                if (normalizedDates[0]) {
                  setTravelDate(normalizedDates[0]);
                  setCalendarVisibleMonth(monthFromDateIso(normalizedDates[0]));
                }
              }}
              invalid={(dateTouched && !travelDate) || Boolean(fieldErrors.travel_date)}
              onBlur={() => setDateTouched(true)}
              onChange={(value) => {
                setTravelDate(value);
                setSelectedTravelDates([]);
                setCalendarVisibleMonth(monthFromDateIso(value));
                if (isReturn && returnDate && value && returnDate < value) {
                  setReturnDate("");
                  setReturnDateTouched(true);
                  setCalendarVisibleMonthReturn(monthFromDateIso(value));
                  setFieldErrors((prev) => ({
                    ...prev,
                    travel_date: undefined,
                    return_date: t("returnResetAfterOutboundChange"),
                  }));
                  return;
                }
                setFieldErrors((prev) => ({
                  ...prev,
                  travel_date: undefined,
                  ...(prev.return_date ? { return_date: undefined } : {}),
                }));
              }}
            />
            {(dateTouched && !travelDate) || fieldErrors.travel_date ? (
              <small className="qs-error">{fieldErrors.travel_date || t("selectOutbound")}</small>
            ) : null}
          </label>

          <label className="qs-check qs-check-inline qs-roundtrip-toggle">
            <input
              type="checkbox"
              name="is_return"
              checked={isReturn}
              onChange={(e) => {
                const nextChecked = e.target.checked;
                setIsReturn(nextChecked);
                setReturnDateTouched(false);
                setSearchError((current) => (
                  current === t("selectReturn") || current === t("returnBefore") ? null : current
                ));
                if (!nextChecked) {
                  setReturnDate("");
                  setApplyFlexReturn(false);
                  setFieldErrors((prev) => ({ ...prev, return_date: undefined }));
                  return;
                }
                setFieldErrors((prev) => ({ ...prev, return_date: undefined }));
              }}
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
            <span className="qs-roundtrip-copy">
              <strong>{t("roundTrip")}</strong>
              <small className="qs-search-hint">{roundTripHelperCopy}</small>
            </span>
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
                dayHintsByIso={calendarHintsActiveReturn?.dayHintsByIso || {}}
                hintsLoading={calendarHintsLoadingKeyReturn === calendarHintsRequestKeyReturn}
                showCountryEstimateBadge={canRequestCalendarHints && hasCountryScopeForCalendarHints}
                hintScopeMode={calendarHintsActiveReturn?.scopeMode || calendarHintsScopeMode}
                onVisibleMonthChange={setCalendarVisibleMonthReturn}
                min={travelDate || undefined}
                invalid={(returnDateTouched && !returnDate) || Boolean(fieldErrors.return_date) || returnDateInvalid}
                onBlur={() => setReturnDateTouched(true)}
                onChange={(value) => {
                  setReturnDate(value);
                  setCalendarVisibleMonthReturn(monthFromDateIso(value));
                  setReturnDateTouched(true);
                  setFieldErrors((prev) => ({
                    ...prev,
                    return_date: value && travelDate && value < travelDate ? t("returnBefore") : undefined,
                  }));
                }}
              />
              {(returnDateTouched && !returnDate) || fieldErrors.return_date || returnDateInvalid ? (
                <small className="qs-error">
                  {fieldErrors.return_date || (returnDateInvalid ? t("returnBefore") : t("selectReturn"))}
                </small>
              ) : tripType === "round_trip_incomplete" ? (
                <small className="qs-search-hint qs-return-hint">{t("selectReturnHint")}</small>
              ) : null}
            </label>
          ) : null}
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

        

        <QuickSearchAdvancedDrawer
          isOpen={isAdvancedOpen}
          onClose={() => setIsAdvancedOpen(false)}
          closeRef={advancedCloseRef}
          departAfter={departAfter}
          departBefore={departBefore}
          strictFilters={strictFilters}
          includeStops={includeStops}
          maxStops={maxStops}
          bufferMin={bufferMin}
          excludeOrigins={excludeOrigins}
          excludeDestinations={excludeDestinations}
          excludeOriginInput={excludeOriginInput}
          excludeDestinationInput={excludeDestinationInput}
          fieldErrors={fieldErrors}
          t={t}
          setDepartAfter={setDepartAfter}
          setDepartBefore={setDepartBefore}
          setStrictFilters={setStrictFilters}
          setIncludeStops={setIncludeStops}
          setMaxStops={setMaxStops}
          setBufferMin={setBufferMin}
          setExcludeOriginInput={setExcludeOriginInput}
          setExcludeDestinationInput={setExcludeDestinationInput}
          addExcludeOrigin={commitExcludeOriginInput}
          addExcludeDestination={commitExcludeDestinationInput}
          removeExcludeOrigin={removeExcludeOriginChip}
          removeExcludeDestination={removeExcludeDestinationChip}
          onClearAll={() => {
            setDepartAfter("");
            setDepartBefore("");
            setStrictFilters(true);
            setExcludeOrigins([]);
            setExcludeDestinations([]);
          }}
          pendingSearchChanges={pendingActionVisibility.consoleAction}
          onApplyAndSearch={() => {
            setIsAdvancedOpen(false);
            runSearch();
          }}
        />

        <div className="qs-actions">
          <div className="qs-search-cta">
            <button className="btn-search" type="submit" disabled={!isReady || !routeInputsValid || isSubmitting || isLoading}>
              {isLoading ? t("loadingAria") : t("search")}
            </button>
            {searchCtaHint ? (
              <small className="qs-search-hint qs-search-cta-hint">{searchCtaHint}</small>
            ) : null}
          </div>
          {isIdleVisualState ? (
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
          ) : null}
        </div>
        <QuickSearchSummaryChips 
          title={t("quickSummaryTitle")}
          headline={summaryTrip}
          caption={summaryMeta}
          chips={compactSummaryChips} 
          missingBadges={summaryMissingBadges}
          onOpenAdvanced={() => setIsAdvancedOpen(true)}
          moreOptionsLabel={t("moreOptions")}
        />
        </QuickSearchSearchForm>
      </section>

      {showResultsWorkspace && !isDualMode ? (
      <QuickSearchResultsWorkspace>
      <div id="qs-workspace-hint" className="qs-workspace-hint">
        {pageWorkspaceHint}
      </div>
      <div className="qs-workspace">
        <div className="qs-workspace-grid">
        <section className="panel panel-soft qs-results-panel">
          {showResultsStagehead ? (
          <div className="qs-results-stagehead">
            <div className="qs-results-stagehead__status">
              <span className="qs-results-stagehead__eyebrow">{t("results")}</span>
              <h2>{resultsStageTitle}</h2>
              <p>{hasSearched ? `${t("orderedBy")} ${sortLabel[sortBy]}` : pageWorkspaceHint}</p>
            </div>
            {pendingSearchChanges ? (
              <span className="qs-results-stagehead__pending">{t("pendingChangesTitle")}</span>
            ) : null}
          </div>
          ) : null}
          {showResultsToolbar ? (
          <div className="qs-results-toolbar" ref={resultsToolbarRef} tabIndex={-1}>
            <div className="qs-results-summary">
              <strong>{totalResults}</strong> {t("results")}
              {hasSearched ? <span className="muted"> - {t("orderedBy")} {sortLabel[sortBy]}</span> : null}
              {searchMeta?.truncated ? <span className="chip chip-warn">{t("truncated")}</span> : null}
              {hasSearched ? (
                <span className="qs-freshness-global">
                  {!globalFreshness.isUnavailable ? (
                    <span>
                      {globalFreshness.label}
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
              <label className="field">
                {t("orderBy")}
                <select
                  name="sort_by"
                  autoComplete="off"
                  value={sortBy}
                  onChange={(e) => handleSortChange(e.target.value as QuickSearchSortBy)}
                  className="qs-input"
                >
                  <option value="ranking">{t("sortRanking")}</option>
                  <option value="price">{t("sortPrice")}</option>
                  <option value="duration">{t("sortDuration")}</option>
                  <option value="freshness">{t("sortFreshness")}</option>
                </select>
              </label>
              <button
                type="button"
                className="btn-ghost qs-export-json"
                onClick={() => {
                  void handleExportQuickSearch();
                }}
                disabled={!canExportQuickSearch}
                aria-label={t("quickExportJsonAria")}
              >
                <Download className="qs-inline-icon" aria-hidden="true" />
                {isExportingQuickSearch ? t("quickExportingJson") : t("quickExportJson")}
              </button>
              <details
                className="qs-explain-popover qs-how-order"
                ref={explainPopoverRef}
                onToggle={(event) => setIsExplainOpen(event.currentTarget.open)}
              >
                <summary className={`qs-explain-trigger qs-results-explain-chip qs-how-order__summary ${showDegradedState ? "qs-degraded-chip" : ""}`} role="button" aria-label={t("explainTitle")} ref={explainTriggerRef}>
                  <svg className="qs-inline-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.7" />
                    <path d="M12 8v.2M12 11v5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                  </svg>
                  {explainChipLabel}
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
                  </div>
                  <div className="qs-explain-note">
                    <span>{t("detailsNote")}</span>
                  </div>
                  {selectedResult ? (
                    <div className="qs-explain-selected">
                      <strong>{selectedResult.origin} {" â†’ "} {selectedResult.destination}</strong>
                      <span>{t("score")}: {selectedResult.ranking_score ? formatScore(selectedResult.ranking_score) : "--"}</span>
                      <span>{getFreshnessLabel(selectedResult)}</span>
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
          ) : null}

          <QuickSearchLoadingProgress
            show={isVisualLoading}
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
            loadingTotalText={loadingTotalText}
            loadingProgressText={loadingProgressText}
            loadingScopeText={loadingScopeText}
            providerStatuses={providerSearchStatuses}
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
                      {item.label}: {item.before} â†’ {item.after}
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

          {providerTotalWarnings.length > 0 && visibleResults.length === 0 ? (
            <div className="notice notice-error section-gap-sm" role="status" aria-live="polite">
              {providerTotalWarnings.map((group) => `${group.message}${group.count > 1 ? ` (${group.count})` : ""}`).join(" ")}
            </div>
          ) : null}
          {providerPartialInlineText && showResultsList ? (
            <div className="notice notice-info section-gap-sm" role="status" aria-live="polite">
              {providerPartialInlineText}
            </div>
          ) : null}

          {!isVisualLoading ? (
            <QuickSearchStatePanels
              searchState={panelSearchState}
              rateLimitSeconds={rateLimitSeconds}
              searchError={searchError}
              emptyStateMainTitle={emptyStateMainTitle}
              locale={locale}
              zeroResultCauses={zeroResultCauses}
              visibleZeroResultCauses={visibleZeroResultCauses}
              canExpandZeroResultCauses={canExpandZeroResultCauses}
              emptyCausesExpanded={emptyCausesExpanded}
              zeroResultActions={zeroResultActions}
              onToggleEmptyCauses={toggleEmptyCauses}
              onRelaxAction={onZeroResultRelaxAction}
              onRunSearch={runSearch}
              onEmptyCta={openRelaxPreview}
              t={t}
            />
          ) : null}
          {showResultsList ? (
            <>
              <QuickSearchResultsList
                visibleResults={visibleResults}
                compactView={compactView}
                expandedRows={expandedRows}
                openRowMenuId={openRowMenuId}
                deeplinkUrl={deeplinkUrl}
                origin={origin}
                destination={destination}
                radiusKm={radiusKm}
                departAfter={departAfter}
                departBefore={departBefore}
                localeTag={localeTag}
                travelers={adults}
                fareProfile={outboundFareProfile}
                onFareProfileChange={setOutboundFareProfile}
                weatherOrigin={weatherOrigin}
                weatherDestination={weatherDestination}
                getCopyPayload={getCopyPayload}
                rowMenuTriggerRefs={rowMenuTriggerRefs}
                t={t}
                formatMoney={formatMoney}
                formatScore={formatScore}
                formatMinutes={formatMinutes}
                resultKey={resultKey}
                canRefreshPrice={canRefreshPrice}
                isInWatchlist={isInWatchlist}
                getWatchlistHref={getResultWatchlistHref}
                refreshingResultId={refreshingResultId}
                refreshPrice={refreshQuickSearchResult}
                addToWatchlist={addToWatchlist}
                viewInWatchlist={viewResultInWatchlist}
                setExpandedRows={setExpandedRows}
                setSelectedResultId={setSelectedResultId}
                setOpenRowMenuId={setOpenRowMenuId}
                setCopyModalPayload={setCopyModalPayload}
                setCopyModalOpen={setCopyModalOpen}
                closeRowMenu={closeRowMenu}
                onTrackOpenRyanair={trackOpenRyanair}
                onTrackRowOverflow={trackRowOverflow}
                onTrackCopyParams={trackCopyParams}
              />
              {totalPages > 1 ? (
                <div
                  className={`qs-pagination animate-fade-in${isPageChanging ? " qs-pagination--loading" : ""}`}
                  role="navigation"
                  aria-label="Pagination"
                  aria-busy={isPageChanging}
                >
                  <div className="qs-pagination-stats">
                    {t("paginationShowing")
                      .replace("{start}", String(totalResults === 0 ? 0 : (activePage - 1) * pageSize + 1))
                      .replace("{end}", String(Math.min(activePage * pageSize, totalResults)))
                      .replace("{total}", String(totalResults))}
                    {isPageChanging ? <span className="qs-pagination-live">Preparando pagina</span> : null}
                  </div>
                  <div className="qs-pagination-nav">
                    <button
                      className="qs-pagination-btn qs-pagination-btn-arrow"
                      onClick={() => {
                        goToPage(activePage - 1);
                      }}
                      disabled={activePage === 1 || isPageChanging}
                      aria-label={t("paginationPrev")}
                    >
                      <span className="qs-pagination-arrow">â†</span>
                      <span className="qs-pagination-btn-text">{t("paginationPrev")}</span>
                    </button>

                    <div className="qs-pagination-pages">
                      {getPageNumbers(activePage, totalPages).map((num, idx) => {
                        if (num === "...") {
                          return (
                            <span key={`ellipsis-${idx}`} className="qs-pagination-ellipsis" aria-hidden="true">
                              ...
                            </span>
                          );
                        }
                        const isSelected = num === activePage;
                        return (
                          <button
                            key={`page-${num}`}
                            className={`qs-pagination-btn ${isSelected ? "active" : ""}`}
                            onClick={() => {
                              goToPage(Number(num));
                            }}
                            disabled={isPageChanging}
                            aria-current={isSelected ? "page" : undefined}
                            aria-label={`Ir a la pagina ${num}`}
                          >
                            {num}
                          </button>
                        );
                      })}
                    </div>

                    <button
                      className="qs-pagination-btn qs-pagination-btn-arrow"
                      onClick={() => {
                        goToPage(activePage + 1);
                      }}
                      disabled={activePage === totalPages || isPageChanging}
                      aria-label={t("paginationNext")}
                    >
                      <span className="qs-pagination-btn-text">{t("paginationNext")}</span>
                      <span className="qs-pagination-arrow">â†’</span>
                    </button>
                  </div>
                </div>
              ) : null}
            </>
          ) : null}

        </section>
        <aside className="qs-context-rail">
          {pendingActionVisibility.contextRailNotice ? (
            <div className="notice notice-warning qs-pending-changes" role="status" aria-live="polite">
              <strong>{t("pendingChangesTitle")}</strong>
              <span>{t("pendingChangesBody")}</span>
            </div>
          ) : null}
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
              <section className="qs-info-tier qs-info-tier-status" aria-live="polite">
                <span className="qs-info-tier-kicker">{t("searchSummaryTitle")}</span>
                <strong>{showDegradedState ? t("degradedBadge") : t("searchReadyTitle")}</strong>
                <p>
                  {showDegradedState ? t("degradedHint") : t("searchReadyHint")}
                  {formatFreshnessTime(globalFreshness.observedAt) ? (
                    <span> Â· {t("lastData")}: {formatFreshnessTime(globalFreshness.observedAt)}</span>
                  ) : null}
                </p>
              </section>
              {(warningSeverity.critical.length > 0 || warningSeverity.neutral.length > 0 || weatherMessage || providerPartialInlineText) ? (
                <section className="qs-info-tier qs-info-tier-impact" aria-live="polite">
                  <span className="qs-info-tier-kicker">{t("results")}</span>
                  {warningSeverity.critical.length > 0 ? (
                    <div className="qs-info-impact-row qs-info-impact-row-critical">
                      <strong>{warningProblemTitle}</strong>
                      <span>{groupedCriticalWarnings.map((group) => `${group.message}${group.count > 1 ? ` (${group.count})` : ""}`).join(" Â· ")}</span>
                    </div>
                  ) : null}
                  {providerPartialInlineText ? (
                    <div className="qs-info-impact-row qs-info-impact-row-neutral">
                      <strong>{warningGroupedTitle}</strong>
                      <span>{providerPartialInlineText}</span>
                    </div>
                  ) : null}
                  {warningSeverity.neutral.length > 0 && !providerPartialInlineText ? (
                    <div className="qs-info-impact-row qs-info-impact-row-neutral">
                      <strong>{warningGroupedTitle}</strong>
                      <span>{groupedNeutralWarnings.map((group) => `${group.message}${group.count > 1 ? ` (${group.count})` : ""}`).join(" Â· ")}</span>
                    </div>
                  ) : null}
                  {weatherMessage ? (
                    <div className="qs-info-impact-row qs-info-impact-row-neutral">
                      <strong>{warningGroupedTitle}</strong>
                      <span>{weatherMessage}</span>
                    </div>
                  ) : null}
                </section>
              ) : null}
              {relaxedLabels.length > 0 ? (
                <div className="notice notice-compact notice-success">
                  {t("filtersRelaxed")}: {relaxedLabels.join(", ")}.
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
                      {sourcesSummary.entries.map((entry) => (
                        <li key={`${entry.id}-${entry.label}-${entry.count}`}>
                          <QuickSearchProviderBadge source={entry.label} unknownLabel={t("sourceUnknown")} />
                          <strong>{entry.count}</strong>
                        </li>
                      ))}
                    </ul>
                  </div>
                </details>
              ) : null}
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
                  notify({ tone: "success", title: t("deepLinkCopied"), durationMs: 3200 });
                  setCopyModalOpen(false);
                }}
              >
                {t("deepLinkCopy")}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {deepLinkError ? <div className="notice notice-error section-gap-sm">{deepLinkError}</div> : null}
      {message ? (
        <div className={`notice section-gap ${messageType === "success" ? "notice-success" : "notice-error"}`}>
          {message}
        </div>
      ) : null}

      </QuickSearchResultsWorkspace>
      ) : !isDualMode ? (
        <section className="panel panel-soft section-gap-sm" aria-live="polite">
          <div className="panel-header">
            <h2>{t("searchReadyTitle")}</h2>
            <span className="muted">{t("searchReadyHint")}</span>
          </div>
        </section>
      ) : null}



      {/* ── Dual-mode workspace (Fase 6) ── */}
      {isDualMode && (outboundSide.searchState !== "idle" || returnSide.searchState !== "idle") ? (
        <QuickSearchDualWorkspace ariaLabel="Round-trip results" hoveredSide={dualHoverSide}>
          {/* ── Outbound panel ── */}
          <QuickSearchSidePanel
            side="outbound"
            origin={originCountryOnly != null ? (originCountryOnly as CountryAirports).name : origin}
            destination={destinationCountryOnly != null ? (destinationCountryOnly as CountryAirports).name : destination}
            dateLabel={formatShortDate(travelDate)}
            headerLabel={t("sideOutboundLabel")}
            resultCount={outboundSide.searchState === "success" ? outboundPanelState.visibleResults.length : 0}
            currentPage={outboundSide.searchState === "success" ? outboundSide.currentPage : undefined}
            totalPages={outboundSide.searchMeta?.pagination?.total_pages}
            pageSize={outboundSide.searchMeta?.pagination?.page_size}
            totalResults={outboundSide.searchMeta?.pagination?.total_results}
            isPageChanging={outboundSide.isPageChanging}
            onPageChange={outboundSide.searchState === "success" ? (page: number) => outboundSide.goToPage(page) : undefined}
            locale={locale}
            onHoverStart={() => setDualHoverSide("outbound")}
            onHoverEnd={() => setDualHoverSide(null)}
          >
            {outboundSide.searchState === "success" ? (
              <QuickSearchSideViewControls
                title={t("sideViewControlsOutboundTitle")}
                subtitle={t("sideViewControlsSubtitle")}
                state={outboundViewState}
                t={t}
                onChange={updateOutboundViewState}
                onReset={resetOutboundViewState}
              />
            ) : null}
            {outboundSide.searchState === "loading" || outboundSide.searchState === "error" || outboundSide.searchState === "empty" || outboundSide.searchState === "rate" || (outboundSide.searchState === "success" && outboundPanelState.visibleResults.length === 0) ? (
              <QuickSearchStatePanels
                searchState={outboundSide.searchState === "success" ? "empty" : outboundSide.searchState}
                rateLimitSeconds={outboundSide.rateLimitSeconds}
                searchError={outboundSide.searchError}
                emptyStateMainTitle={outboundPanelState.emptyStateMainTitle}
                locale={locale}
                zeroResultCauses={outboundPanelState.zeroResultCauses}
                visibleZeroResultCauses={outboundPanelState.visibleZeroResultCauses}
                canExpandZeroResultCauses={outboundPanelState.canExpandZeroResultCauses}
                emptyCausesExpanded={outboundEmptyCausesExpanded}
                zeroResultActions={outboundPanelState.zeroResultActions}
                onToggleEmptyCauses={() => setOutboundEmptyCausesExpanded((prev) => !prev)}
                onRelaxAction={(action) => { void handleDualRelaxAction(action, "outbound"); }}
                onRunSearch={() => outboundSide.goToPage(1)}
                onEmptyCta={() => outboundSide.goToPage(1)}
                t={t}
              />
            ) : outboundSide.searchState === "success" ? (
              <QuickSearchResultsList
                visibleResults={outboundPanelState.visibleResults}
                compactView={compactView}
                expandedRows={outboundSide.expandedRows}
                openRowMenuId={null}
                deeplinkUrl={outboundSide.deepLink?.url || outboundSide.deepLink?.fallback_url || localRyanairUrl}
                origin={origin}
                destination={destination}
                radiusKm={radiusKm}
                departAfter={departAfter}
                departBefore={departBefore}
                localeTag={localeTag}
                travelers={adults}
                fareProfile={outboundFareProfile}
                onFareProfileChange={setOutboundFareProfile}
                weatherOrigin={outboundSide.weatherOrigin}
                weatherDestination={outboundSide.weatherDestination}
                getCopyPayload={getCopyPayload}
                rowMenuTriggerRefs={rowMenuTriggerRefs}
                t={t}
                formatMoney={formatMoneyOutbound}
                formatScore={formatScore}
                formatMinutes={formatMinutes}
                resultKey={resultKey}
                canRefreshPrice={canRefreshPrice}
                refreshingResultId={refreshingResultId}
                isInWatchlist={isInWatchlist}
                getWatchlistHref={getResultWatchlistHref}
                refreshPrice={refreshQuickSearchResult}
                viewInWatchlist={viewResultInWatchlist}
                addToWatchlist={async (result: SearchResult, fareProfile: FareComparisonProfile) => {
                  setMessage("");
                  try {
                    const response = await apiFetch<SaveResult>("/search/save-result", {
                      method: "POST",
                      body: JSON.stringify(buildQuickSearchSaveResultPayload(result, {
                        jobId: outboundSide.jobId,
                        fareProfile,
                        fallbackDeepLinkUrl: outboundSide.deepLink?.url ?? outboundSide.deepLink?.fallback_url ?? localRyanairUrl ?? null,
                      })),
                    });
                    if (response) {
                      markAsSaved(result, response.watch_id);
                      const isExisting = "created_or_existing" in response && response.created_or_existing === "existing";
                      notify({
                        tone: "success",
                        title: t(isExisting ? "watchExists" : "watchAdded"),
                        actionLabel: t("viewWatchlist"),
                        onAction: () => navigateToWatchlistWithContext(result.origin, result.destination, result.travel_date, response.watch_id),
                        durationMs: 3200,
                      });
                    }
                  } catch {
                    setMessage(t("watchFailed"));
                    setMessageType("error");
                  }
                }}
                setExpandedRows={outboundSide.setExpandedRows}
                setSelectedResultId={outboundSide.setSelectedResultId}
                setOpenRowMenuId={() => {}}
                setCopyModalPayload={setCopyModalPayload}
                setCopyModalOpen={setCopyModalOpen}
                closeRowMenu={() => {}}
                onTrackOpenRyanair={trackOpenRyanair}
                onTrackRowOverflow={trackRowOverflow}
                onTrackCopyParams={trackCopyParams}
              />
            ) : null}
          </QuickSearchSidePanel>
          <div className="qs-dual-divider" />

          {/* ── Return panel ── */}
          <QuickSearchSidePanel
            side="return"
            origin={destinationCountryOnly != null ? (destinationCountryOnly as CountryAirports).name : destination}
            destination={originCountryOnly != null ? (originCountryOnly as CountryAirports).name : origin}
            dateLabel={formatShortDate(returnDate)}
            headerLabel={t("sideReturnLabel")}
            resultCount={returnSide.searchState === "success" ? returnPanelState.visibleResults.length : 0}
            currentPage={returnSide.searchState === "success" ? returnSide.currentPage : undefined}
            totalPages={returnSide.searchMeta?.pagination?.total_pages}
            pageSize={returnSide.searchMeta?.pagination?.page_size}
            totalResults={returnSide.searchMeta?.pagination?.total_results}
            isPageChanging={returnSide.isPageChanging}
            onPageChange={returnSide.searchState === "success" ? (page: number) => returnSide.goToPage(page) : undefined}
            locale={locale}
            onHoverStart={() => setDualHoverSide("return")}
            onHoverEnd={() => setDualHoverSide(null)}
          >
            {returnSide.searchState === "success" ? (
              <QuickSearchSideViewControls
                title={t("sideViewControlsReturnTitle")}
                subtitle={t("sideViewControlsSubtitle")}
                state={returnViewState}
                t={t}
                onChange={updateReturnViewState}
                onReset={resetReturnViewState}
              />
            ) : null}
            {returnSide.searchState === "loading" || returnSide.searchState === "error" || returnSide.searchState === "empty" || returnSide.searchState === "rate" || (returnSide.searchState === "success" && returnPanelState.visibleResults.length === 0) ? (
              <QuickSearchStatePanels
                searchState={returnSide.searchState === "success" ? "empty" : returnSide.searchState}
                rateLimitSeconds={returnSide.rateLimitSeconds}
                searchError={returnSide.searchError}
                emptyStateMainTitle={returnPanelState.emptyStateMainTitle}
                locale={locale}
                zeroResultCauses={returnPanelState.zeroResultCauses}
                visibleZeroResultCauses={returnPanelState.visibleZeroResultCauses}
                canExpandZeroResultCauses={returnPanelState.canExpandZeroResultCauses}
                emptyCausesExpanded={returnEmptyCausesExpanded}
                zeroResultActions={returnPanelState.zeroResultActions}
                onToggleEmptyCauses={() => setReturnEmptyCausesExpanded((prev) => !prev)}
                onRelaxAction={(action) => { void handleDualRelaxAction(action, "return"); }}
                onRunSearch={() => returnSide.goToPage(1)}
                onEmptyCta={() => returnSide.goToPage(1)}
                t={t}
              />
            ) : returnSide.searchState === "success" ? (
              <QuickSearchResultsList
                visibleResults={returnPanelState.visibleResults}
                compactView={compactView}
                expandedRows={returnSide.expandedRows}
                openRowMenuId={null}
                deeplinkUrl={returnSide.deepLink?.url || returnSide.deepLink?.fallback_url || buildReturnFallbackUrl()}
                origin={destination}
                destination={origin}
                radiusKm={radiusKm}
                departAfter={departAfter}
                departBefore={departBefore}
                localeTag={localeTag}
                travelers={adults}
                fareProfile={returnFareProfile}
                onFareProfileChange={setReturnFareProfile}
                weatherOrigin={null} /* Phase 14: weather not fetched in dual mode */
                weatherDestination={null} /* Phase 14: weather not fetched in dual mode */
                getCopyPayload={getCopyPayload}
                rowMenuTriggerRefs={rowMenuTriggerRefs}
                t={t}
                formatMoney={formatMoneyReturn}
                formatScore={formatScore}
                formatMinutes={formatMinutes}
                resultKey={resultKey}
                canRefreshPrice={canRefreshPrice}
                refreshingResultId={refreshingResultId}
                refreshPrice={refreshQuickSearchResult}
                isInWatchlist={isInWatchlist}
                getWatchlistHref={getResultWatchlistHref}
                viewInWatchlist={viewResultInWatchlist}
                setExpandedRows={setExpandedRows}
                addToWatchlist={async (result: SearchResult, fareProfile: FareComparisonProfile) => {
                  setMessage("");
                  try {
                    const response = await apiFetch<SaveResult>("/search/save-result", {
                      method: "POST",
                      body: JSON.stringify(buildQuickSearchSaveResultPayload(result, {
                        jobId: returnSide.jobId,
                        fareProfile,
                        fallbackDeepLinkUrl: returnSide.deepLink?.url ?? returnSide.deepLink?.fallback_url ?? localRyanairUrl ?? null,
                      })),
                    });
                    if (response) {
                      markAsSaved(result, response.watch_id);
                      const isExisting = "created_or_existing" in response && response.created_or_existing === "existing";
                      notify({
                        tone: "success",
                        title: t(isExisting ? "watchExists" : "watchAdded"),
                        actionLabel: t("viewWatchlist"),
                        onAction: () => navigateToWatchlistWithContext(result.origin, result.destination, result.travel_date, response.watch_id),
                        durationMs: 3200,
                      });
                    }
                  } catch {
                    setMessage(t("watchFailed"));
                    setMessageType("error");
                  }
                }}
                setSelectedResultId={returnSide.setSelectedResultId}
                setOpenRowMenuId={() => {}}
                setCopyModalPayload={setCopyModalPayload}
                setCopyModalOpen={setCopyModalOpen}
                closeRowMenu={() => {}}
                onTrackOpenRyanair={trackOpenRyanair}
                onTrackRowOverflow={trackRowOverflow}
                onTrackCopyParams={trackCopyParams}
              />
            ) : null}
          </QuickSearchSidePanel>

          {/* ── Combined banner ── */}
          <QuickSearchCombinedBanner
            combinedPrice={
              (() => {
                const ob = outboundSide.selectedResultId
                  ? outboundPanelState.visibleResults.find((r, i) => resultKey(r, i) === outboundSide.selectedResultId)
                  : outboundPanelState.visibleResults[0];
                const rb = returnSide.selectedResultId
                  ? returnPanelState.visibleResults.find((r, i) => resultKey(r, i) === returnSide.selectedResultId)
                  : returnPanelState.visibleResults[0];
                if (ob && rb) {
                  const obPrice = ob.price_total ?? ob.price;
                  const rbPrice = rb.price_total ?? rb.price;
                  if (obPrice == null || rbPrice == null) return null;
                  return obPrice + rbPrice;
                }
                return null;
              })()
            }
            currency={(() => {
              const ob = outboundPanelState.visibleResults[0];
              const rb = returnPanelState.visibleResults[0];
              return ob?.currency ?? rb?.currency ?? "EUR";
            })()}
            visible={dualCombinationVisible}
            onSave={() => {
              const ob = findCombinationResult(outboundPanelState.visibleResults, outboundSide.selectedResultId);
              const rb = findCombinationResult(returnPanelState.visibleResults, returnSide.selectedResultId);
              if (!ob || !rb) {
                notify({ tone: "info", title: t("combinationSelectBoth"), durationMs: 3000 });
                return;
              }
              pendingCombinationResultsRef.current = { outbound: ob, return: rb };
              void saveCombination.saveCombination({
                outbound: ob,
                return: rb,
                origin,
                destination,
                groupId: crypto.randomUUID(),
                outboundFareProfile,
                returnFareProfile,
              });
            }}
            saving={saveCombination.status === "saving"}
            locale={locale}
          />
        </QuickSearchDualWorkspace>
      ) : null}

      {airportPickerModal}

    </main>
  );
}
