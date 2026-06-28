import { useMemo } from "react";

import { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";
import { SearchFilters, SearchResponse, SearchResult, ZeroResultRelaxAction } from "@/modules/quick-search/types";
import { deriveQuickSearchVisibleResults } from "@/modules/quick-search/state/quickSearchVisibleResults";
import { parseNumericInput } from "@/modules/quick-search/searchCriteria";
import { resolveQuickSearchProviderPresentation } from "@/modules/quick-search/providerPresentation";

type QuickSearchScreenStateArgs = {
  results: SearchResult[];
  priceMin: string;
  priceMax: string;
  durationMax: string;
  sortBy: "ranking" | "price" | "duration" | "freshness";
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
  const visibleResults = useMemo(() => {
    return deriveQuickSearchVisibleResults({
      results,
      priceMin,
      priceMax,
      durationMax,
      sortBy,
    });
  }, [results, priceMin, priceMax, durationMax, sortBy]);

  const warningSeverity = useMemo(() => {
    const neutralCodes = new Set([
      "ryanair_unavailable_partial",
      "ryanair_availability_failed_partial",
      "ryanair_fares_failed_partial",
      "provider_timeout_partial",
      "provider_error_partial",
      "provider_partial_results_served",
    ]);
    const criticalCodes = new Set([
      "provider_total_outage",
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
    const grouped = new Map<string, { id: string; label: string; count: number }>();
    visibleResults.forEach((item) => {
      const provider = resolveQuickSearchProviderPresentation(item.source, t("sourceUnknown"));
      const current = grouped.get(provider.label);
      if (current) {
        current.count += 1;
        return;
      }
      grouped.set(provider.label, {
        id: provider.id,
        label: provider.label,
        count: 1,
      });
    });
    const entries = Array.from(grouped.values()).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
    const preview = entries.slice(0, 2).map((entry) => `${entry.label} (${entry.count})`).join(", ");
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

  const providerStatus = searchMeta?.provider_status;
  const providerOverallStatus = providerStatus?.overall_status ?? providerStatus?.overall;
  const providerTotalOutage = filtersWarningCodes.includes("provider_total_outage")
    || filtersWarningCodes.includes("ryanair_provider_unavailable_total")
    || providerOverallStatus === "total_outage"
    || Boolean(providerStatus?.total_outage);
  const providerPartialOutage = filtersWarningCodes.includes("provider_partial_results_served")
    || filtersWarningCodes.includes("provider_error_partial")
    || filtersWarningCodes.includes("provider_timeout_partial")
    || filtersWarningCodes.includes("ryanair_availability_failed_partial")
    || filtersWarningCodes.includes("ryanair_fares_failed_partial")
    || filtersWarningCodes.includes("ryanair_unavailable_partial")
    || providerOverallStatus === "partial_degraded"
    || Boolean(providerStatus?.partial_results_served);
  const providerPartialInlineNotice = useMemo(() => {
    if (!providerStatus) return null;
    if ((providerStatus.overall_status ?? providerStatus.overall) !== "partial_degraded") return null;
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
