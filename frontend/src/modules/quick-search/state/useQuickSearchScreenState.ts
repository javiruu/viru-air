import { useMemo } from "react";

import { normalizeQuickSearchResults } from "@/modules/quick-search/api/normalizeQuickSearchResponse";
import { parseNumericInput } from "@/modules/quick-search/searchCriteria";
import { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";
import { SearchFilters, SearchResponse, SearchResult, ZeroResultRelaxAction } from "@/modules/quick-search/types";

type QuickSearchScreenStateArgs = {
  results: SearchResult[];
  priceMin: string;
  priceMax: string;
  durationMax: string;
  riskFilter: "all" | "low" | "medium" | "high";
  sortBy: "ranking" | "price" | "duration" | "risk" | "freshness";
  showHighRisk: boolean;
  filtersNotice: string[];
  filtersWarningCodes: string[];
  filtersMeta: SearchFilters | null;
  isDegraded: boolean;
  searchMeta: SearchResponse["meta"] | null;
  weatherMessage: string;
  strictFilters: boolean;
  includeStops: boolean;
  radiusActive: boolean;
  radiusKm: number;
  excludeOriginsCount: number;
  excludeDestinationsCount: number;
  departAfter: string;
  departBefore: string;
  daysBefore: number;
  daysAfter: number;
  emptyCausesExpanded: boolean;
  t: (key: QuickSearchCopyKey) => string;
  tWarn: (key: string) => string;
};

export function useQuickSearchScreenState({
  results,
  priceMin,
  priceMax,
  durationMax,
  riskFilter,
  sortBy,
  showHighRisk,
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
  excludeOriginsCount,
  excludeDestinationsCount,
  departAfter,
  departBefore,
  daysBefore,
  daysAfter,
  emptyCausesExpanded,
  t,
  tWarn,
}: QuickSearchScreenStateArgs) {
  const normalizedResults = useMemo(() => normalizeQuickSearchResults(results), [results]);
  const { visibleResults, hiddenHighRiskResults } = useMemo(() => {
    const min = parseNumericInput(priceMin, { min: 0 });
    const max = parseNumericInput(priceMax, { min: 0 });
    const durMax = parseNumericInput(durationMax, { min: 1 });
    let list = normalizedResults.filter((item) => {
      if (riskFilter !== "all" && item.risk_label !== riskFilter) {
        if (riskFilter !== "high" && item.risk_label === "high") return true;
        return false;
      }
      if (min !== null && item.price_total !== undefined && item.price_total < min) return false;
      if (max !== null && item.price_total !== undefined && item.price_total > max) return false;
      if (durMax !== null && item.duration_total_min != null && item.duration_total_min > durMax) return false;
      return true;
    });
    const hiddenHighRisk = list.filter((item) => item.risk_label === "high" && riskFilter !== "high");
    if (!showHighRisk && riskFilter !== "high") {
      list = list.filter((item) => item.risk_label !== "high");
    }
    const riskScore = (label?: string | null) => {
      if (label === "low") return 1;
      if (label === "medium") return 2;
      if (label === "high") return 3;
      return 9;
    };
    list = list.slice().sort((a, b) => {
      if (sortBy === "price") return (a.price_total ?? 0) - (b.price_total ?? 0);
      if (sortBy === "duration") return (a.duration_total ?? 99999) - (b.duration_total ?? 99999);
      if (sortBy === "risk") return riskScore(a.risk_label) - riskScore(b.risk_label);
      if (sortBy === "freshness") {
        const aTs = a.freshness_ts ? new Date(a.freshness_ts).getTime() : 0;
        const bTs = b.freshness_ts ? new Date(b.freshness_ts).getTime() : 0;
        return bTs - aTs;
      }
      return (b.ranking_score ?? 0) - (a.ranking_score ?? 0);
    });
    return { visibleResults: list, hiddenHighRiskResults: hiddenHighRisk };
  }, [normalizedResults, priceMin, priceMax, durationMax, riskFilter, sortBy, showHighRisk]);

  const warningSeverity = useMemo(() => {
    const neutralCodes = new Set([
      "ryanair_unavailable_partial",
      "ryanair_availability_failed_partial",
      "ryanair_fares_failed_partial",
      "provider_timeout_partial",
      "provider_error_partial",
    ]);
    const criticalCodes = new Set([
      "ryanair_provider_unavailable_total",
      "ryanair_availability_failed",
      "ryanair_fares_failed",
    ]);
    const sourceCodesOrNotices = filtersWarningCodes.length > 0 ? filtersWarningCodes : filtersNotice;
    const neutral: string[] = [];
    const critical: string[] = [];
    sourceCodesOrNotices.forEach((codeOrNotice) => {
      if (!filtersWarningCodes.length) {
        if (/(error|fall|failed|bloque|blocked|rate|limit)/i.test(codeOrNotice)) {
          critical.push(codeOrNotice);
          return;
        }
        neutral.push(codeOrNotice);
        return;
      }
      const code = codeOrNotice;
      if (criticalCodes.has(code)) {
        critical.push(tWarn(code));
        return;
      }
      if (neutralCodes.has(code)) {
        neutral.push(tWarn(code));
        return;
      }
      neutral.push(tWarn(code));
    });
    return { neutral, critical };
  }, [filtersWarningCodes, filtersNotice, tWarn]);

  const groupedNeutralWarnings = useMemo(() => {
    const grouped = new Map<string, number>();
    for (const notice of warningSeverity.neutral) {
      grouped.set(notice, (grouped.get(notice) || 0) + 1);
    }
    return Array.from(grouped.entries()).map(([message, count]) => ({ message, count }));
  }, [warningSeverity.neutral]);

  const groupedCriticalWarnings = useMemo(() => {
    const grouped = new Map<string, number>();
    for (const notice of warningSeverity.critical) {
      grouped.set(notice, (grouped.get(notice) || 0) + 1);
    }
    return Array.from(grouped.entries()).map(([message, count]) => ({ message, count }));
  }, [warningSeverity.critical]);

  const sourcesSummary = useMemo(() => {
    const grouped = new Map<string, number>();
    visibleResults.forEach((item) => {
      const source =
        typeof item.source === "string" && item.source.trim()
          ? item.source.trim()
          : t("sourceUnknown");
      grouped.set(source, (grouped.get(source) || 0) + 1);
    });
    const entries = Array.from(grouped.entries()).sort((a, b) => b[1] - a[1]);
    const preview = entries.slice(0, 2).map(([source, count]) => `${source} (${count})`).join(", ");
    return {
      entries,
      preview,
    };
  }, [visibleResults, t]);

  const durationMaxNumber = useMemo(() => parseNumericInput(durationMax, { min: 1 }), [durationMax]);

  const timeWindowMinutes = useMemo(() => {
    const parseMinutes = (value: string) => {
      const [h, m] = value.split(":").map(Number);
      if (!Number.isFinite(h) || !Number.isFinite(m)) return null;
      return h * 60 + m;
    };
    const from = parseMinutes(departAfter);
    const to = parseMinutes(departBefore);
    if (from === null || to === null) return null;
    if (to >= from) return to - from;
    return 24 * 60 - from + to;
  }, [departAfter, departBefore]);

  const providerTotalOutage = filtersWarningCodes.includes("ryanair_provider_unavailable_total");
  const providerPartialOutage = filtersWarningCodes.includes("ryanair_availability_failed_partial")
    || filtersWarningCodes.includes("ryanair_fares_failed_partial")
    || filtersWarningCodes.includes("ryanair_unavailable_partial");
  const providerStatus = searchMeta?.provider_status;
  const providerPartialInlineNotice = useMemo(() => {
    if (!providerStatus) return null;
    if (providerStatus.overall !== "partial_degraded") return null;
    if (!providerStatus.partial_results_served) return null;
    const availabilityFailed = providerStatus.availability?.status === "failed";
    const faresFailed = providerStatus.fares?.status === "failed";
    if (availabilityFailed && !faresFailed) return t("providerPartialAvailabilityNotice");
    if (faresFailed && !availabilityFailed) return t("providerPartialFaresNotice");
    return t("providerPartialMixedNotice");
  }, [providerStatus, t]);
  const hasGroupedWarnings = warningSeverity.critical.length > 0 || warningSeverity.neutral.length > 0;
  const showDegradedState =
    isDegraded
    || Boolean(searchMeta?.stale_data)
    || providerPartialOutage
    || providerTotalOutage;
  const infoItemsCount =
    (filtersMeta?.relaxed && filtersMeta.relaxed.length > 0 ? 1 : 0)
    + (warningSeverity.critical.length > 0 ? 1 : 0)
    + (warningSeverity.neutral.length > 0 ? 1 : 0)
    + (showDegradedState && !hasGroupedWarnings ? 1 : 0)
    + (weatherMessage ? 1 : 0)
    + 1;

  const zeroResultCauses = useMemo(() => {
    if (providerTotalOutage) {
      return [t("emptyCauseProvider")];
    }
    const causes: string[] = [];
    if (providerPartialOutage) causes.push(t("emptyCauseProvider"));
    if (strictFilters) causes.push(t("emptyCauseStrict"));
    if (!includeStops) causes.push(t("emptyCauseStops"));
    if (durationMaxNumber !== null) causes.push(t("emptyCauseDuration"));
    if (timeWindowMinutes !== null && timeWindowMinutes <= 360) causes.push(t("emptyCauseTimeWindow"));
    if (!radiusActive || radiusKm < 150) causes.push(t("emptyCauseRadius"));
    if (excludeOriginsCount > 0 || excludeDestinationsCount > 0) causes.push(t("emptyCauseExclusions"));
    return causes;
  }, [
    strictFilters,
    includeStops,
    durationMaxNumber,
    timeWindowMinutes,
    radiusActive,
    radiusKm,
    excludeOriginsCount,
    excludeDestinationsCount,
    providerPartialOutage,
    providerTotalOutage,
    t,
  ]);

  const visibleZeroResultCauses = emptyCausesExpanded ? zeroResultCauses : zeroResultCauses.slice(0, 3);
  const canExpandZeroResultCauses = zeroResultCauses.length > 3;
  const emptyStateMainTitle = providerTotalOutage
    ? t("emptyStateProviderTitle")
    : providerPartialOutage && visibleResults.length === 0
      ? t("emptyStateProviderPartialTitle")
      : t("emptyStateMainTitle");

  const zeroResultActions = useMemo(() => {
    if (providerTotalOutage) return [];
    const actions: Array<{ id: ZeroResultRelaxAction; label: string }> = [];
    if (strictFilters) actions.push({ id: "disable_strict", label: t("emptyActionDisableStrict") });
    if (durationMaxNumber !== null) actions.push({ id: "increase_duration", label: t("emptyActionIncreaseDuration") });
    if (!radiusActive || radiusKm < 150) actions.push({ id: "open_radius_150", label: t("emptyActionOpenRadius") });
    if (daysBefore < 2 || daysAfter < 2) actions.push({ id: "open_date_flex", label: t("emptyActionDateFlex") });
    if (excludeOriginsCount > 0 || excludeDestinationsCount > 0) {
      actions.push({ id: "clear_exclusions", label: t("emptyActionClearExclusions") });
    }
    return actions;
  }, [
    strictFilters,
    durationMaxNumber,
    radiusActive,
    radiusKm,
    daysBefore,
    daysAfter,
    excludeOriginsCount,
    excludeDestinationsCount,
    providerTotalOutage,
    t,
  ]);

  return {
    durationMaxNumber,
    visibleResults,
    hiddenHighRiskResults,
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
  };
}
