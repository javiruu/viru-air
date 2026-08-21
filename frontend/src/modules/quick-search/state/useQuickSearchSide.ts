import { useCallback, useRef, useState } from "react";

import { apiFetchWithStatus, LONG_RUNNING_API_BASE } from "@/modules/shared/api";
import {
  buildQuickSearchCanonicalPayload,
  prepareQuickSearchRequest,
  type QuickSearchCanonicalPayload,
  type QuickSearchQueryParams,
} from "@/modules/quick-search/api/buildQuickSearchRequest";
import { collectQuickSearchWarningCodes, normalizeQuickSearchResponse } from "@/modules/quick-search/responseNormalizer";
import type {
  DeepLinkResponse,
  QuickSearchLoadingPhase,
  SearchFilters,
  SearchResponse,
  SearchResponseRaw,
  SearchResult,
  WeatherReport,
} from "@/modules/quick-search/types";

// ── Types ────────────────────────────────────────────────────────────

export type QuickSearchSideId = "outbound" | "return";

/** Parameters that describe one side of a search.  Passed to `runSearch()`. */
export type QuickSearchSideParams = {
  originIata: string | string[];
  destinationIata: string | string[];
  travelDate: string;
  travelDates?: string[];
  flexDaysBefore: number;
  flexDaysAfter: number;
  radiusKm: number;
  includeStops: boolean;
  includeNearbyOrigins: boolean;
  includeNearbyDestinations: boolean;
  departAfter?: string;
  departBefore?: string;
  maxStops: number;
  excludeOrigins: string[];
  excludeDestinations: string[];
  strictFilters: boolean;
  softFiltersWeight?: number;
  pageSize?: number;
};

type QuickSearchRunOptions = {
  presentation?: "search" | "page";
};

export type QuickSearchSideState = ReturnType<typeof useQuickSearchSide>;

// ── Hook ──────────────────────────────────────────────────────────────

const PAGE_SIZE = 10;

/**
 * Encapsulates the complete lifecycle of ONE search side (outbound or return).
 *
 * Manages: results, pagination, loading progress, error/empty/success states,
 * degradation flags, weather, and filter metadata — everything that would need
 * to be duplicated for a dual-panel (ida + vuelta) layout.
 */
export function useQuickSearchSide(sideId: QuickSearchSideId) {
  // ── Result state ──────────────────────────────────────────────────
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searchState, setSearchState] = useState<
    "idle" | "loading" | "success" | "empty" | "error" | "rate"
  >("idle");
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchMeta, setSearchMeta] = useState<SearchResponse["meta"] | null>(null);
  const [filtersMeta, setFiltersMeta] = useState<SearchFilters | null>(null);
  const [filtersNotice, setFiltersNotice] = useState<string[]>([]);
  const [filtersWarningCodes, setFiltersWarningCodes] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [isDegraded, setIsDegraded] = useState(false);
  const [rateLimitSeconds, setRateLimitSeconds] = useState(0);

  // ── Pagination ────────────────────────────────────────────────────
  const [currentPage, setCurrentPage] = useState(1);
  const [isPageChanging, setIsPageChanging] = useState(false);

  // ── Deep link ─────────────────────────────────────────────────────
  const [deepLink, setDeepLink] = useState<DeepLinkResponse | null>(null);
  const [deepLinkError, setDeepLinkError] = useState("");

  // ── Weather ───────────────────────────────────────────────────────
  const [weatherOrigin, setWeatherOrigin] = useState<WeatherReport | null>(null);
  const [weatherDestination, setWeatherDestination] = useState<WeatherReport | null>(null);
  const [weatherMessage, setWeatherMessage] = useState("");

  // ── Row interaction ───────────────────────────────────────────────
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);

  // ── Loading progress ──────────────────────────────────────────────
  const [targetProgress, setTargetProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0);
  const [loadingPhase, setLoadingPhase] = useState<QuickSearchLoadingPhase>("idle");
  const [showBoarding, setShowBoarding] = useState(false);
  const [loadingVisualHold, setLoadingVisualHold] = useState(false);
  const [showLoader, setShowLoader] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  // ── Loading animation refs ────────────────────────────────────────
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

  // Keep a ref to the last params so `goToPage` can re-use them
  const lastParamsRef = useRef<QuickSearchSideParams | null>(null);

  // Abort controller for in-flight deep link request
  const deepLinkAbortRef = useRef<AbortController | null>(null);

  // ── runSearch ─────────────────────────────────────────────────────

  const runSearch = useCallback(
    async (params: QuickSearchSideParams, page = 1, options?: QuickSearchRunOptions) => {
      const isPageChange = options?.presentation === "page";
      requestIdRef.current += 1;
      const requestId = requestIdRef.current;
      activeLoadingRequestRef.current = requestId;
      const isCurrentRequest = () => requestId === requestIdRef.current;

      lastParamsRef.current = params;
      setIsPageChanging(isPageChange);

      setSearchError(null);
      if (!isPageChange) {
        setFiltersNotice([]);
        setFiltersWarningCodes([]);
        setFiltersMeta(null);
        setSearchMeta(null);
        setJobId(null);
        setIsDegraded(false);
        setSearchState("loading");
        setShowLoader(true);
        setLoadingVisualHold(false);
        setDisplayProgress(0);
        setTargetProgress(30);
        setLoadingPhase("requesting");
      }

      const queryParams: QuickSearchQueryParams = {
        origin_iata: params.originIata,
        destination_iata: params.destinationIata,
        travel_date: params.travelDate,
        date: params.travelDate,
        travel_dates: params.travelDates,
        flex_days_before: params.flexDaysBefore,
        flex_days_after: params.flexDaysAfter,
        radius_km: params.radiusKm,
        include_stops: params.includeStops,
        include_nearby_origins: params.includeNearbyOrigins,
        include_nearby_destinations: params.includeNearbyDestinations,
        depart_after: params.departAfter,
        depart_before: params.departBefore,
        max_stops: params.includeStops ? params.maxStops : 0,
        exclude_origins: params.excludeOrigins,
        exclude_destinations: params.excludeDestinations,
        strict_filters: params.strictFilters,
        soft_filters_weight: params.softFiltersWeight ?? 0.6,
        page,
        page_size: params.pageSize ?? PAGE_SIZE,
      };

      const prepared = prepareQuickSearchRequest(queryParams);
      if (prepared.issues.length > 0) {
        if (!isCurrentRequest()) return;
        setSearchError("Invalid search parameters");
        setSearchState("idle");
        setIsPageChanging(false);
        return;
      }

      const canonicalPayload: QuickSearchCanonicalPayload =
        buildQuickSearchCanonicalPayload(prepared.params);

      try {
        if (!isCurrentRequest()) return;

        const result = await apiFetchWithStatus<SearchResponseRaw>("/search/quick", {
          method: "POST",
          body: JSON.stringify(canonicalPayload),
        }, { apiBase: LONG_RUNNING_API_BASE });

        if (!isCurrentRequest()) return;

        if (!isPageChange) {
          setTargetProgress(80);
          setLoadingPhase("response_parsed");
        }

        if (result.ok) {
          const data: SearchResponse = normalizeQuickSearchResponse(result.data);

          setResults(data.results);
          setFiltersMeta(data.filters || null);
          setSearchMeta(data.meta || null);
          setCurrentPage(data.meta?.pagination?.page ?? page);
          setJobId(data.job_id || null);

          const providerOverallStatus =
            data.meta?.provider_status?.overall_status ??
            data.meta?.provider_status?.overall;
          setIsDegraded(
            Boolean(
              data.meta?.stale_data ||
                data.results.find((item) => item.stale_data) ||
                providerOverallStatus === "partial_degraded" ||
                providerOverallStatus === "total_outage" ||
                data.meta?.provider_status?.partial_results_served ||
                data.meta?.provider_status?.total_outage,
            ),
          );

          const warningCodes = collectQuickSearchWarningCodes(data);
          setFiltersWarningCodes(warningCodes);
          setFiltersNotice(warningCodes);

          if (!isPageChange) {
            setTargetProgress(95);
            setLoadingPhase("client_done");
          }
          setHasSearched(true);

          const isEmptyResult =
            (data.meta?.pagination?.total_results ?? data.results.length) === 0;
          setSearchState(isEmptyResult ? "empty" : "success");
        } else {
          const { status, error } = result;

          if (!isPageChange) {
            setTargetProgress(95);
          }

          if (status === 429) {
            setRateLimitSeconds(error.retry_after_sec ?? 30);
            setSearchState("rate");
            setSearchError("Rate limited");
          } else {
            setSearchState("error");
            setSearchError(error.message ?? "Search failed");
          }
          setHasSearched(true);
        }
      } catch (err) {
        if (!isCurrentRequest()) return;
        if (!isPageChange) {
          setTargetProgress(95);
        }
        setSearchState("error");
        setSearchError("Search failed");
        setHasSearched(true);
      } finally {
        if (isCurrentRequest()) {
          setIsPageChanging(false);
        }
      }
    },
    [], // intentionally empty — uses refs for cancellation
  );

  // ── goToPage ──────────────────────────────────────────────────────

  const goToPage = useCallback(
    (page: number) => {
      const params = lastParamsRef.current;
      if (!params) return;
      void runSearch(params, page, { presentation: "page" });
    },
    [runSearch],
  );

  // ── fetchDeepLink ─────────────────────────────────────────────────

  const fetchDeepLink = useCallback(
    (params: {
      originIata: string;
      destinationIata: string;
      dateOut: string;
      dateIn?: string;
      adults: number;
      locale: "es" | "en";
    }) => {
      // Cancel any in-flight deep link request
      deepLinkAbortRef.current?.abort();
      const controller = new AbortController();
      deepLinkAbortRef.current = controller;

      const query = new URLSearchParams();
      query.set("origin_iata", params.originIata);
      query.set("destination_iata", params.destinationIata);
      query.set("date_out", params.dateOut);
      if (params.dateIn) {
        query.set("date_in", params.dateIn);
      }
      query.set("adults", String(params.adults));
      query.set("teens", "0");
      query.set("children", "0");
      query.set("infants", "0");
      query.set("locale", params.locale === "en" ? "en-us" : "es-es");

      void apiFetchWithStatus<DeepLinkResponse>(
        `/search/deeplink?${query.toString()}`,
        { method: "GET", signal: controller.signal },
      ).then((result) => {
        if (controller.signal.aborted) return;
        if (result.ok) {
          setDeepLink(result.data);
          setDeepLinkError("");
        } else {
          setDeepLink(null);
          setDeepLinkError("deeplink_failed");
        }
      }).catch(() => {
        if (controller.signal.aborted) return;
        setDeepLink(null);
        setDeepLinkError("deeplink_failed");
      });
    },
    [],
  );

  // ── reset ─────────────────────────────────────────────────────────

  const reset = useCallback(() => {
    lastParamsRef.current = null;
    deepLinkAbortRef.current?.abort();
    deepLinkAbortRef.current = null;
    setResults([]);
    setSearchState("idle");
    setSearchError(null);
    setSearchMeta(null);
    setFiltersMeta(null);
    setFiltersNotice([]);
    setFiltersWarningCodes([]);
    setJobId(null);
    setIsDegraded(false);
    setRateLimitSeconds(0);
    setCurrentPage(1);
    setIsPageChanging(false);
    setDeepLink(null);
    setDeepLinkError("");
    setWeatherOrigin(null);
    setWeatherDestination(null);
    setWeatherMessage("");
    setExpandedRows({});
    setSelectedResultId(null);
    setTargetProgress(0);
    setDisplayProgress(0);
    setLoadingPhase("idle");
    setShowBoarding(false);
    setLoadingVisualHold(false);
    setShowLoader(false);
    setHasSearched(false);
  }, []);

  // ── Return ────────────────────────────────────────────────────────

  return {
    sideId,

    // Result state
    results,
    setResults,
    searchState,
    setSearchState,
    searchError,
    setSearchError,
    searchMeta,
    setSearchMeta,
    filtersMeta,
    setFiltersMeta,
    filtersNotice,
    setFiltersNotice,
    filtersWarningCodes,
    setFiltersWarningCodes,
    jobId,
    setJobId,
    isDegraded,
    setIsDegraded,
    rateLimitSeconds,
    setRateLimitSeconds,
    hasSearched,
    setHasSearched,

    // Pagination
    currentPage,
    setCurrentPage,
    isPageChanging,

    // Deep link
    deepLink,
    setDeepLink,
    deepLinkError,
    setDeepLinkError,

    // Weather
    weatherOrigin,
    setWeatherOrigin,
    weatherDestination,
    setWeatherDestination,
    weatherMessage,
    setWeatherMessage,

    // Row interaction
    expandedRows,
    setExpandedRows,
    selectedResultId,
    setSelectedResultId,

    // Loading progress
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

    // Loading refs
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

    // Actions
    runSearch,
    goToPage,
    fetchDeepLink,
    reset,
  };
}
