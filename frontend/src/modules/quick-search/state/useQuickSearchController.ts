import { useRef, useState } from "react";

import {
  CountryAirports,
  DeepLinkResponse,
  Pref,
  QuickSearchAutocompleteField,
  QuickSearchFieldErrors,
  QuickSearchLoadingPhase,
  RegionPref,
  RelaxUndoPayload,
  SearchFilters,
  SearchResponse,
  SearchResult,
  SummaryHighlightKey,
  WeatherReport,
} from "@/modules/quick-search/types";

export function useQuickSearchMainState(initialOrigin: string, initialDestination: string) {
  const [origin, setOrigin] = useState(initialOrigin);
  const [destination, setDestination] = useState(initialDestination);
  const [travelDate, setTravelDate] = useState("");
  const [returnDate, setReturnDate] = useState("");
  const [isReturn, setIsReturn] = useState(false);
  const [adults, setAdults] = useState(1);
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
  const [activePicker, setActivePicker] = useState<"origin" | "destination" | null>(null);
  const [airportSearch, setAirportSearch] = useState("");
  const [recentAirports, setRecentAirports] = useState<string[]>([]);
  const [originCountryOnly, setOriginCountryOnly] = useState<CountryAirports | null>(null);
  const [destinationCountryOnly, setDestinationCountryOnly] = useState<CountryAirports | null>(null);
  const [originSelectedCountryCode, setOriginSelectedCountryCode] = useState<string | null>(null);
  const [destinationSelectedCountryCode, setDestinationSelectedCountryCode] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [routePulse, setRoutePulse] = useState(false);
  const [departAfter, setDepartAfter] = useState("07:00");
  const [departBefore, setDepartBefore] = useState("22:00");
  const [bufferMin, setBufferMin] = useState("");
  const [includeStops, setIncludeStops] = useState(false);
  const [maxStops, setMaxStops] = useState(1);
  const [radiusKm, setRadiusKm] = useState(150);
  const [includeNearbyOrigins, setIncludeNearbyOrigins] = useState(false);
  const [includeNearbyDestinations, setIncludeNearbyDestinations] = useState(false);
  const [excludeOrigins, setExcludeOrigins] = useState<string[]>([]);
  const [excludeDestinations, setExcludeDestinations] = useState<string[]>([]);
  const [excludeOriginInput, setExcludeOriginInput] = useState("");
  const [excludeDestinationInput, setExcludeDestinationInput] = useState("");
  const [strictFilters, setStrictFilters] = useState(true);
  const [daysBefore, setDaysBefore] = useState(0);
  const [daysAfter, setDaysAfter] = useState(0);
  const [applyFlexReturn, setApplyFlexReturn] = useState(false);
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [durationMax, setDurationMax] = useState("");
  const [riskFilter, setRiskFilter] = useState<"all" | "low" | "medium" | "high">("all");
  const [sortBy, setSortBy] = useState<"ranking" | "price" | "duration" | "risk" | "freshness">("ranking");
  const [isDegraded, setIsDegraded] = useState(false);
  const [compactView, setCompactView] = useState(false);
  const [showHighRisk, setShowHighRisk] = useState(false);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [pref, setPref] = useState<Pref | null>(null);
  const [regionPref, setRegionPref] = useState<RegionPref | null>(null);
  const [prefBadge, setPrefBadge] = useState(false);
  const [deepLink, setDeepLink] = useState<DeepLinkResponse | null>(null);
  const [deepLinkError, setDeepLinkError] = useState("");
  const [copyModalOpen, setCopyModalOpen] = useState(false);
  const [copyModalPayload, setCopyModalPayload] = useState("");
  const [summaryHighlightKey, setSummaryHighlightKey] = useState<SummaryHighlightKey>(null);
  const [originTouched, setOriginTouched] = useState(false);
  const [destinationTouched, setDestinationTouched] = useState(false);
  const [dateTouched, setDateTouched] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<QuickSearchFieldErrors>({});
  const [activeAutocompleteField, setActiveAutocompleteField] = useState<QuickSearchAutocompleteField | null>(null);
  const [activeAutocompleteIndex, setActiveAutocompleteIndex] = useState(-1);
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const [isExplainOpen, setIsExplainOpen] = useState(false);
  const [openRowMenuId, setOpenRowMenuId] = useState<string | null>(null);
  const [targetProgress, setTargetProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0);
  const [loadingPhase, setLoadingPhase] = useState<QuickSearchLoadingPhase>("idle");
  const [showBoarding, setShowBoarding] = useState(false);
  const [loadingVisualHold, setLoadingVisualHold] = useState(false);
  const [showLoader, setShowLoader] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [isMobileViewport, setIsMobileViewport] = useState(false);
  const [warningsExpanded, setWarningsExpanded] = useState(false);
  const [criticalWarningsExpanded, setCriticalWarningsExpanded] = useState(false);
  const [emptyCausesExpanded, setEmptyCausesExpanded] = useState(false);
  const [infoExpanded, setInfoExpanded] = useState(false);
  const [selectedCountry, setSelectedCountry] = useState<CountryAirports | null>(null);
  const [countrySelectionTouched, setCountrySelectionTouched] = useState(false);
  const [airportSelectionTouched, setAirportSelectionTouched] = useState(false);
  const blurTimer = useRef<number | null>(null);
  const autocompleteBlurTimer = useRef<number | null>(null);
  const zeroResultsTracked = useRef(false);
  const idleStateTracked = useRef(false);
  const resultsToolbarRef = useRef<HTMLDivElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const filtersToggleRef = useRef<HTMLButtonElement | null>(null);
  const filtersCloseRef = useRef<HTMLButtonElement | null>(null);
  const explainPopoverRef = useRef<HTMLDetailsElement | null>(null);
  const explainTriggerRef = useRef<HTMLElement | null>(null);
  const relaxUndoRef = useRef<RelaxUndoPayload | null>(null);
  const lastPickerTriggerRef = useRef<HTMLButtonElement | null>(null);
  const airportSearchInputRef = useRef<HTMLInputElement | null>(null);
  const rowMenuTriggerRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const tripTypeIncompleteTrackedRef = useRef(false);
  const sourcesShownKeyRef = useRef<string | null>(null);
  const freshnessShownKeyRef = useRef<string | null>(null);
  const headrowRemovedTrackedRef = useRef(false);
  const requestIdRef = useRef(0);
  const activeLoadingRequestRef = useRef<number | null>(null);
  const prevSearchStateRef = useRef(searchState);
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
  };
}
