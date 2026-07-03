import {
  INITIAL_PROVIDER_SEARCH_STATUSES,
  resolveProviderPresentation,
} from "@/modules/shared/providerPresentation";
import type { HistoryRow } from "@/modules/watchlist/types";

export type WatchProviderCoverageItem = {
  id: string;
  label: string;
  status: "observed" | "ready";
  observedCount: number;
  latestCapturedAt: string | null;
};

export function buildWatchProviderCoverage(rows: Pick<HistoryRow, "provider" | "capturedAt">[]): WatchProviderCoverageItem[] {
  const observed = new Map<string, { label: string; count: number; latestCapturedAt: string | null }>();
  rows.forEach((row) => {
    const provider = resolveProviderPresentation(row.provider);
    if (provider.id === "unknown" || !provider.rawSource) return;
    const current = observed.get(provider.id);
    const currentLatest = current?.latestCapturedAt ? new Date(current.latestCapturedAt).getTime() : 0;
    const nextLatest = new Date(row.capturedAt).getTime();
    observed.set(provider.id, {
      label: provider.label,
      count: (current?.count ?? 0) + 1,
      latestCapturedAt:
        Number.isFinite(nextLatest) && nextLatest >= currentLatest
          ? row.capturedAt
          : current?.latestCapturedAt ?? row.capturedAt,
    });
  });

  return INITIAL_PROVIDER_SEARCH_STATUSES.map((provider) => {
    const current = observed.get(provider.id);
    return {
      id: provider.id,
      label: provider.label,
      status: current ? "observed" : "ready",
      observedCount: current?.count ?? 0,
      latestCapturedAt: current?.latestCapturedAt ?? null,
    };
  });
}
