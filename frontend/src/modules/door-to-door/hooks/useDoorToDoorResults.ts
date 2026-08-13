"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { chooseDoorToDoorOption } from "@/modules/door-to-door/api";
import { getAlternativeDeltas, getDecisionBadges, getDecisionReasons } from "@/modules/door-to-door/decision";
import type { DoorToDoorOption, DoorToDoorResponse } from "@/modules/door-to-door/types";

type TrustTone = "success" | "warning";

function deriveTrustTone(option: DoorToDoorOption | null): TrustTone {
  if (!option) return "warning";
  const confirmed = option.sources.filter(
    (s) =>
      (s.source_type === "api" || s.source_type === "open_data" || s.source_type === "maps") &&
      (s.confidence === "live" || s.confidence === "cached"),
  ).length;
  const uncertain = option.sources.filter(
    (s) =>
      s.source_type === "deeplink" ||
      s.source_type === "estimate" ||
      s.source_type === "mock" ||
      s.confidence === "estimated" ||
      s.confidence === "deeplink" ||
      s.confidence === "unavailable",
  ).length;
  if (confirmed > 0 && confirmed >= uncertain) return "success";
  return "warning";
}

function resolveActiveOption(response: DoorToDoorResponse | null, chosenOptionId: string): DoorToDoorOption | null {
  if (!response || response.options.length === 0) return null;
  const chosenFromServer = response.summary?.chosen_option_id || null;
  const recommendedFromServer = response.summary?.recommended_option_id || null;
  return (
    response.options.find((o) => o.id === chosenFromServer) ||
    response.options.find((o) => o.id === chosenOptionId) ||
    response.options.find((o) => o.id === recommendedFromServer) ||
    response.options[0] ||
    null
  );
}

export function useDoorToDoorResults(
  response: DoorToDoorResponse | null,
  onHistoryRefresh: () => Promise<void>,
) {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [chosenOptionId, setChosenOptionId] = useState<string>("");

  // Sync chosenOptionId when response changes (new search)
  useEffect(() => {
    setChosenOptionId(response?.summary.chosen_option_id || "");
  }, [response?.summary.chosen_option_id]);

  const realResults = useMemo(
    () => response?.options.filter((o) => o.status === "real_result") ?? [],
    [response],
  );
  const realDeeplinks = useMemo(
    () => response?.options.filter((o) => o.status === "real_deeplink") ?? [],
    [response],
  );
  const estimateOptions = useMemo(
    () => response?.options.filter((o) => o.status === "estimate_only") ?? [],
    [response],
  );

  const selectedPlan = useMemo(
    () => resolveActiveOption(response, chosenOptionId),
    [response, chosenOptionId],
  );

  const quickBadgesByOption = useMemo(() => {
    if (!response) return {};
    return getDecisionBadges(response.options);
  }, [response]);

  const recommendedOption = useMemo(() => {
    if (!response) return null;
    return response.options.find((o) => o.id === response.summary.recommended_option_id) || response.options[0] || null;
  }, [response]);

  const recommendedReasons = useMemo(() => {
    if (!response || !recommendedOption) return [];
    return getDecisionReasons(recommendedOption, response.options);
  }, [response, recommendedOption]);

  const alternativeDeltas = useMemo(() => {
    if (!response || !recommendedOption) return [];
    return getAlternativeDeltas(recommendedOption, response.options);
  }, [response, recommendedOption]);

  const trustTone = useMemo(() => deriveTrustTone(selectedPlan), [selectedPlan]);

  const warningCodes = useMemo(
    () => new Set((response?.warnings ?? []).map((w) => w.code)),
    [response?.warnings],
  );
  const hasNoRealCoverage = warningCodes.has("NO_REAL_PROVIDER_COVERAGE");
  const hasPartialCoverage = warningCodes.has("PROVIDER_PARTIAL_COVERAGE");
  const hasNoCoverage = warningCodes.has("NO_COVERAGE");

  // GTFS granular warnings
  const hasGtfsFeedUnavailable = warningCodes.has("GTFS_FEED_UNAVAILABLE");
  const hasGtfsNoNearbyStops = warningCodes.has("GTFS_NO_NEARBY_STOPS");
  const hasGtfsNoServiceForDate = warningCodes.has("GTFS_NO_SERVICE_FOR_DATE");
  const hasGtfsNoMatchingService = warningCodes.has("GTFS_NO_MATCHING_SERVICE");
  const hasGtfsPartialCoverage = warningCodes.has("GTFS_PARTIAL_COVERAGE");
  const hasGtfsPriceUnavailable = warningCodes.has("GTFS_PRICE_UNAVAILABLE");

  const hasAnyGtfsWarning = hasGtfsFeedUnavailable || hasGtfsNoNearbyStops || hasGtfsNoServiceForDate || hasGtfsNoMatchingService || hasGtfsPartialCoverage || hasGtfsPriceUnavailable;

  const gtfsWarningCodes: string[] = useMemo(() => {
    const codes: string[] = [];
    if (hasGtfsFeedUnavailable) codes.push("GTFS_FEED_UNAVAILABLE");
    if (hasGtfsNoNearbyStops) codes.push("GTFS_NO_NEARBY_STOPS");
    if (hasGtfsNoServiceForDate) codes.push("GTFS_NO_SERVICE_FOR_DATE");
    if (hasGtfsNoMatchingService) codes.push("GTFS_NO_MATCHING_SERVICE");
    if (hasGtfsPartialCoverage) codes.push("GTFS_PARTIAL_COVERAGE");
    if (hasGtfsPriceUnavailable) codes.push("GTFS_PRICE_UNAVAILABLE");
    return codes;
  }, [hasGtfsFeedUnavailable, hasGtfsNoNearbyStops, hasGtfsNoServiceForDate, hasGtfsNoMatchingService, hasGtfsPartialCoverage, hasGtfsPriceUnavailable]);

  const hasChosenPlan = Boolean(response?.summary.chosen_option_id);

  const markChosen = useCallback(async (option: DoorToDoorOption) => {
    if (!response?.summary.history_id) return;
    try {
      await chooseDoorToDoorOption({
        historyId: response.summary.history_id,
        optionId: option.id,
        optionLabel: option.label,
        optionSummary: {
          total_price_min: option.total_price_min,
          total_price_max: option.total_price_max,
          total_duration_minutes: option.total_duration_minutes,
        },
      });
      setChosenOptionId(option.id);
      await onHistoryRefresh();
      notify({ tone: "success", title: t("doorToDoor.option.chosenSaved") });
    } catch {
      notify({ tone: "error", title: t("doorToDoor.option.chosenError") });
    }
  }, [response, onHistoryRefresh, t, notify]);

  return {
    chosenOptionId,
    realResults,
    realDeeplinks,
    estimateOptions,
    selectedPlan,
    quickBadgesByOption,
    recommendedOption,
    recommendedReasons,
    alternativeDeltas,
    trustTone,
    warningCodes,
    hasNoRealCoverage,
    hasPartialCoverage,
    hasNoCoverage,
    hasGtfsFeedUnavailable,
    hasGtfsNoNearbyStops,
    hasGtfsNoServiceForDate,
    hasGtfsNoMatchingService,
    hasGtfsPartialCoverage,
    hasGtfsPriceUnavailable,
    hasAnyGtfsWarning,
    gtfsWarningCodes,
    hasChosenPlan,
    markChosen,
  };
}
