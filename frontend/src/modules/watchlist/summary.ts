type RefreshBulkResponse = {
  status: string;
  requested: number;
  refreshed: string[];
  failed: Array<{ watch_id: string; code: string }>;
};

export type RefreshBulkSummary = {
  updated: number;
  skippedCooldown: number;
  failed: number;
  degradedOrStale: number;
};

export function summarizeRefreshBulkResult(result: RefreshBulkResponse): RefreshBulkSummary {
  const skippedCooldown = result.failed.filter((item) => item.code === "refresh_cooldown_active").length;
  const degradedOrStale = result.failed.filter((item) => item.code.includes("degraded") || item.code.includes("stale")).length;
  return {
    updated: result.refreshed.length,
    skippedCooldown,
    failed: Math.max(0, result.failed.length - skippedCooldown),
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
