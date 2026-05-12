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
