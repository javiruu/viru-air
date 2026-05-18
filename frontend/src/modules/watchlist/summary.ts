import { formatRelativeTime } from "@/modules/shared/format";

type RefreshBulkResponse = {
  status: string;
  requested: number;
  refreshed: string[];
  failed: Array<{ watch_id: string; code: string }>;
};

export type RefreshBulkSummary = {
  updated: number;
  skippedCooldown: number;
  skippedPaused: number;
  failed: number;
  degradedOrStale: number;
};

export function summarizeRefreshBulkResult(result: RefreshBulkResponse): RefreshBulkSummary {
  const skippedCooldown = result.failed.filter((item) => item.code === "refresh_cooldown_active").length;
  const skippedPaused = result.failed.filter((item) => item.code === "watch_paused").length;
  const degradedOrStale = result.failed.filter((item) => item.code.includes("degraded") || item.code.includes("stale")).length;
  return {
    updated: result.refreshed.length,
    skippedCooldown,
    skippedPaused,
    failed: Math.max(0, result.failed.length - skippedCooldown - skippedPaused),
    degradedOrStale,
  };
}

export function hasPriceSummaryData(summary: { count: number }): boolean {
  return summary.count > 0;
}

export type HistoryConfidenceLevel = "none" | "initial" | "limited" | "sufficient";

export type HistoryConfidence = {
  level: HistoryConfidenceLevel;
  titleKey: string | null;
  messageKey: string | null;
};

export function getHistoryConfidence(snapshotCount: number): HistoryConfidence {
  if (snapshotCount <= 0) {
    return { level: "none", titleKey: null, messageKey: null };
  }
  if (snapshotCount <= 1) {
    return {
      level: "initial",
      titleKey: "watchlist.summary.historyConfidence.initialTitle",
      messageKey: "watchlist.summary.historyConfidence.initialMessage",
    };
  }
  if (snapshotCount <= 3) {
    return {
      level: "limited",
      titleKey: "watchlist.summary.historyConfidence.limitedTitle",
      messageKey: "watchlist.summary.historyConfidence.limitedMessage",
    };
  }
  return {
    level: "sufficient",
    titleKey: "watchlist.summary.historyConfidence.sufficientTitle",
    messageKey: "watchlist.summary.historyConfidence.sufficientMessage",
  };
}

type Translator = (key: string, params?: Record<string, string | number>) => string;

export type FreshnessPresentation = {
  label: string;
  detail: string;
  fullText: string;
};

export function getFreshnessPresentation(args: {
  t: Translator;
  locale: string;
  lastUpdatedAt?: string | null;
  freshnessState?: string | null;
  now?: Date;
}): FreshnessPresentation {
  const { t, locale, lastUpdatedAt, freshnessState, now } = args;
  if (!lastUpdatedAt) {
    const label = t("watchlist.freshness.noDataLabel");
    const detail = t("watchlist.freshness.noDataDetail");
    return { label, detail, fullText: `${label} · ${detail}` };
  }

  const date = new Date(lastUpdatedAt);
  if (Number.isNaN(date.getTime())) {
    const label = t("watchlist.freshness.noDataLabel");
    const detail = t("watchlist.freshness.noDataDetail");
    return { label, detail, fullText: `${label} · ${detail}` };
  }

  const nowMs = now?.getTime() ?? Date.now();
  const diffHours = Math.max(0, (nowMs - date.getTime()) / (1000 * 60 * 60));
  const relativeTime = formatRelativeTime(date, locale);

  if (diffHours > 24) {
    const label = t("watchlist.freshness.needsReviewLabel");
    const detail = t("watchlist.freshness.lastUpdatedAgo", { time: relativeTime });
    return { label, detail, fullText: `${label} · ${detail}` };
  }

  const label = freshnessState ? t("watchlist.freshness.observingLabel") : t("watchlist.freshness.observedLabel");
  const detail = t("watchlist.freshness.updatedAgo", { time: relativeTime });
  return { label, detail, fullText: `${label} · ${detail}` };
}
