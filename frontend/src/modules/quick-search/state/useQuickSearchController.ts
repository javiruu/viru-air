import { useRef, useState } from "react";

import {
  DeepLinkResponse,
  Pref,
  QuickSearchLoadingPhase,
  RegionPref,
  SearchFilters,
  SearchResponse,
  SearchResult,
  SummaryHighlightKey,
  WeatherReport,
} from "@/modules/quick-search/types";
import { useQuickSearchFormState } from "@/modules/quick-search/state/useQuickSearchFormState";

/**
 * Full monolithic state for quick-search.  Kept as a compatibility wrapper.
 *
 * Internally delegates form-only state to {@link useQuickSearchFormState} and
 * layers result / loading / UI state on top.  All existing destructuring in
 * QuickSearchView continues to work without any change.
 */
export function useQuickSearchMainState(initialOrigin: string, initialDestination: string) {
  // Form state (extracted)
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
    originCountryOnly,
    setOriginCountryOnly,
    destinationCountryOnly,
    setDestinationCountryOnly,
    originSelectedCountryCode,
    setOriginSelectedCountryCode,
    destinationSelectedCountryCode,
    setDestinationSelectedCountryCode,
    departAfter,
    setDepartAfter,
    departBefore,
    setDepartBefore,
    includeStops,
    setIncludeStops,
    maxStops,
    setMaxStops,
    bufferMin,
    setBufferMin,
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
    activePicker,
    setActivePicker,
    airportSearch,
    setAirportSearch,
    recentAirports,
    setRecentAirports,
    selectedCountry,
    setSelectedCountry,
    countrySelectionTouched,
    setCountrySelectionTouched,
    airportSelectionTouched,
    setAirportSelectionTouched,
    isEditing,
    setIsEditing,
    routePulse,
    setRoutePulse,
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
    blurTimer,
    autocompleteBlurTimer,
    formRef,
    filtersToggleRef,
    filtersCloseRef,
    explainPopoverRef,
    explainTriggerRef,
    relaxUndoRef,
    lastPickerTriggerRef,
    airportSearchInputRef,
  } = useQuickSearchFormState(initialOrigin, initialDestination);

  // Result state
  const [results, setResults] = useState<SearchResult[]>([]);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"error" | "success">("error");
  const [hasSearched, setHasSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [weatherOrigin, setWeatherOrigin] = useState<WeatherReport | null>(null);
  const [weatherDestination, setWeatherDestination] = useState<WeatherReport | null>(null);
  const [weatherMessage, setWeatherMessage] = useState("");
  const [filtersNotice, setFiltersNotice] = useState<string[]>([]);
  const [filtersWarningCodes, setFiltersWarningCodes] = useState<string[]>([]);
  const [filtersMeta, setFiltersMeta] = useState<SearchFilters | null>(null);
  const [searchMeta, setSearchMeta] = useState<SearchResponse["meta"] | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [searchState, setSearchState] = useState<"idle" | "loading" | "success" | "empty" | "error" | "rate">("idle");
  const [searchError, setSearchError] = useState<string | null>(null);
  const [rateLimitSeconds, setRateLimitSeconds] = useState(0);
  const [isDegraded, setIsDegraded] = useState(false);
  const [compactView, setCompactView] = useState(false);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);

  // Preferences & deep-link
  const [pref, setPref] = useState<Pref | null>(null);
  const [regionPref, setRegionPref] = useState<RegionPref | null>(null);
  const [prefBadge, setPrefBadge] = useState(false);
  const [deepLink, setDeepLink] = useState<DeepLinkResponse | null>(null);
  const [deepLinkError, setDeepLinkError] = useState("");

  // Copy modal
  const [copyModalOpen, setCopyModalOpen] = useState(false);
  const [copyModalPayload, setCopyModalPayload] = useState("");
  const [summaryHighlightKey, setSummaryHighlightKey] = useState<SummaryHighlightKey>(null);

  // UI toggles
  const [isExplainOpen, setIsExplainOpen] = useState(false);
  const [openRowMenuId, setOpenRowMenuId] = useState<string | null>(null);

  // Loading progress
  const [targetProgress, setTargetProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0);
  const [loadingPhase, setLoadingPhase] = useState<QuickSearchLoadingPhase>("idle");
  const [showBoarding, setShowBoarding] = useState(false);
  const [loadingVisualHold, setLoadingVisualHold] = useState(false);
  const [showLoader, setShowLoader] = useState(false);

  // Viewport & accessibility
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [isMobileViewport, setIsMobileViewport] = useState(false);

  // Expandable sections
  const [warningsExpanded, setWarningsExpanded] = useState(false);
  const [criticalWarningsExpanded, setCriticalWarningsExpanded] = useState(false);
  const [emptyCausesExpanded, setEmptyCausesExpanded] = useState(false);
  const [infoExpanded, setInfoExpanded] = useState(false);

  // Result-scoped refs
  const zeroResultsTracked = useRef(false);
  const idleStateTracked = useRef(false);
  const resultsToolbarRef = useRef<HTMLDivElement | null>(null);
  const rowMenuTriggerRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const tripTypeIncompleteTrackedRef = useRef(false);
  const sourcesShownKeyRef = useRef<string | null>(null);
  const freshnessShownKeyRef = useRef<string | null>(null);
  const headrowRemovedTrackedRef = useRef(false);
  const requestIdRef = useRef(0);
  const activeLoadingRequestRef = useRef<number | null>(null);
  const prevSearchStateRef = useRef(searchState);

  // Loading animation refs
  const progressRafRef = useRef<number | null>(null);
  const animFromRef = useRef(0);
  const animToRef = useRef(0);
  const animStartTsRef = useRef(0);
  const animDurationMsRef = useRef(220);
  const lastTargetRef = useRef(0);
  const isAnimatingRef = useRef(false);
  const displayProgressRef = useRef(0);
  const commitRafRef = useRef<number | null>(null);
  const boardingThresholdTimerRef = useRef<number | null>(null);
  const takeoffHoldTimerRef = useRef<number | null>(null);
  const loadingStartRef = useRef<number | null>(null);
  const hideTimeoutRef = useRef<number | null>(null);
  const debugEpochRef = useRef<number | null>(null);
  const debugLastTickLogTsRef = useRef(0);

  return {
    origin, setOrigin, destination, setDestination, travelDate, setTravelDate,
    returnDate, setReturnDate, isReturn, setIsReturn, adults, setAdults,
    originCountryOnly, setOriginCountryOnly, destinationCountryOnly, setDestinationCountryOnly,
    originSelectedCountryCode, setOriginSelectedCountryCode,
    destinationSelectedCountryCode, setDestinationSelectedCountryCode,
    departAfter, setDepartAfter, departBefore, setDepartBefore,
    includeStops, setIncludeStops, maxStops, setMaxStops, bufferMin, setBufferMin,
    radiusKm, setRadiusKm, includeNearbyOrigins, setIncludeNearbyOrigins,
    includeNearbyDestinations, setIncludeNearbyDestinations,
    excludeOrigins, setExcludeOrigins, excludeDestinations, setExcludeDestinations,
    excludeOriginInput, setExcludeOriginInput,
    excludeDestinationInput, setExcludeDestinationInput,
    strictFilters, setStrictFilters, daysBefore, setDaysBefore,
    daysAfter, setDaysAfter, applyFlexReturn, setApplyFlexReturn,
    priceMin, setPriceMin, priceMax, setPriceMax, durationMax, setDurationMax,
    sortBy, setSortBy,
    activePicker, setActivePicker, airportSearch, setAirportSearch,
    recentAirports, setRecentAirports, selectedCountry, setSelectedCountry,
    countrySelectionTouched, setCountrySelectionTouched,
    airportSelectionTouched, setAirportSelectionTouched,
    isEditing, setIsEditing, routePulse, setRoutePulse,
    originTouched, setOriginTouched, destinationTouched, setDestinationTouched,
    dateTouched, setDateTouched, fieldErrors, setFieldErrors,
    activeAutocompleteField, setActiveAutocompleteField,
    activeAutocompleteIndex, setActiveAutocompleteIndex,
    isFiltersOpen, setIsFiltersOpen,
    blurTimer, autocompleteBlurTimer, formRef, filtersToggleRef, filtersCloseRef,
    explainPopoverRef, explainTriggerRef, relaxUndoRef, lastPickerTriggerRef,
    airportSearchInputRef,
    results, setResults, message, setMessage, messageType, setMessageType,
    hasSearched, setHasSearched, isLoading, setIsLoading,
    weatherOrigin, setWeatherOrigin, weatherDestination, setWeatherDestination,
    weatherMessage, setWeatherMessage,
    filtersNotice, setFiltersNotice, filtersWarningCodes, setFiltersWarningCodes,
    filtersMeta, setFiltersMeta, searchMeta, setSearchMeta,
    jobId, setJobId, searchState, setSearchState, searchError, setSearchError,
    rateLimitSeconds, setRateLimitSeconds, isDegraded, setIsDegraded,
    compactView, setCompactView,
    expandedRows, setExpandedRows, selectedResultId, setSelectedResultId,
    pref, setPref, regionPref, setRegionPref, prefBadge, setPrefBadge,
    deepLink, setDeepLink, deepLinkError, setDeepLinkError,
    copyModalOpen, setCopyModalOpen, copyModalPayload, setCopyModalPayload,
    summaryHighlightKey, setSummaryHighlightKey,
    isExplainOpen, setIsExplainOpen, openRowMenuId, setOpenRowMenuId,
    targetProgress, setTargetProgress, displayProgress, setDisplayProgress,
    loadingPhase, setLoadingPhase, showBoarding, setShowBoarding,
    loadingVisualHold, setLoadingVisualHold, showLoader, setShowLoader,
    prefersReducedMotion, setPrefersReducedMotion,
    isMobileViewport, setIsMobileViewport,
    warningsExpanded, setWarningsExpanded,
    criticalWarningsExpanded, setCriticalWarningsExpanded,
    emptyCausesExpanded, setEmptyCausesExpanded, infoExpanded, setInfoExpanded,
    zeroResultsTracked, idleStateTracked, resultsToolbarRef,
    rowMenuTriggerRefs, tripTypeIncompleteTrackedRef,
    sourcesShownKeyRef, freshnessShownKeyRef, headrowRemovedTrackedRef,
    requestIdRef, activeLoadingRequestRef, prevSearchStateRef,
    progressRafRef, animFromRef, animToRef, animStartTsRef, animDurationMsRef,
    lastTargetRef, isAnimatingRef, displayProgressRef, commitRafRef,
    boardingThresholdTimerRef, takeoffHoldTimerRef, loadingStartRef,
    hideTimeoutRef, debugEpochRef, debugLastTickLogTsRef,
  };
}
