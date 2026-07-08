import { trackUxEvent } from "@/lib/uxTracking";
import { apiFetch } from "@/modules/shared/api";
import { summarizeRefreshBulkResult } from "@/modules/watchlist/summary";
import { filterWatchesBySelection, mapSnapshotsToHistoryRows } from "@/modules/watchlist/watchlistActions.helpers";
import type { HistoryRow, Snapshot, Watch } from "@/modules/watchlist/types";

type MessageType = "error" | "success";

type TranslateFn = (key: string, params?: Record<string, string | number>) => string;
export type SelectedRefreshResult = "updated" | "same" | "no_flights";

type UseWatchlistMutationsInput = {
  t: TranslateFn;
  load: () => Promise<void>;
  items: Watch[];
  selectedOrigin: string;
  selectedDestination: string;
  selectedDates: string[];
  setIsRefreshingSelectedWatch: (value: boolean) => void;
  setMessage: (value: string) => void;
  setMessageType: (value: MessageType) => void;
  setIsRefreshingFiltered: (value: boolean) => void;
};

export function useWatchlistMutations({
  t,
  load,
  items,
  selectedOrigin,
  selectedDestination,
  selectedDates,
  setIsRefreshingSelectedWatch,
  setMessage,
  setMessageType,
  setIsRefreshingFiltered,
}: UseWatchlistMutationsInput) {
  async function refreshFiltered(): Promise<void> {
    setMessage("");
    const targets = filterWatchesBySelection(items, selectedOrigin, selectedDestination, selectedDates);

    if (targets.length === 0) {
      setMessage(t("watchlist.messages.noFlightsForFilteredUpdate"));
      setMessageType("error");
      return;
    }

    setIsRefreshingFiltered(true);
    try {
      const response = await apiFetch<{
        status: string;
        requested: number;
        refreshed: string[];
        failed: Array<{ watch_id: string; code: string }>;
      }>("/watchlist/refresh-bulk", {
        method: "POST",
        body: JSON.stringify({ watch_ids: targets.map((item) => item.id) }),
      });
      const summary = summarizeRefreshBulkResult(response);
      void trackUxEvent("watchlist_refresh", { scope: "filtered", count: targets.length });
      await load();
      setMessage(
        t("watchlist.messages.bulkUpdateSummary", {
          updated: summary.updated,
          skippedCooldown: summary.skippedCooldown,
          skippedPaused: summary.skippedPaused,
          failed: summary.failed,
          degradedOrStale: summary.degradedOrStale,
        }),
      );
      setMessageType("success");
    } catch {
      setMessage(t("watchlist.messages.filteredUpdateError"));
      setMessageType("error");
    } finally {
      setIsRefreshingFiltered(false);
    }
  }

  async function loadWatchHistoryRows(watchId: string): Promise<HistoryRow[]> {
    const watch = items.find((item) => item.id === watchId);
    if (!watch) return [];
    const snapshots = await apiFetch<Array<Snapshot & { watch_id: string }>>("/prices/history/batch", {
      method: "POST",
      body: JSON.stringify({ watch_ids: [watchId] }),
    });
    return mapSnapshotsToHistoryRows([watch], snapshots)
      .sort((a, b) => new Date(b.capturedAt).getTime() - new Date(a.capturedAt).getTime());
  }

  async function refreshSelectedWatch(watchId: string): Promise<SelectedRefreshResult> {
    setMessage("");
    setIsRefreshingSelectedWatch(true);
    try {
      const beforeRows = await loadWatchHistoryRows(watchId);
      const beforeLatestPrice = beforeRows[0]?.price ?? null;
      const response = await apiFetch<{ status: string; watch_id: string; stale_data?: boolean; provider_status?: string }>(
        `/watchlist/${watchId}/refresh-now`,
        { method: "POST" },
      );
      await load();
      if (response.status === "no_flights") {
        setMessage(t("watchlist.messages.selectedRefreshNoFlights"));
        setMessageType("error");
        return "no_flights";
      }
      const afterRows = await loadWatchHistoryRows(watchId);
      const afterLatestPrice = afterRows[0]?.price ?? null;
      if (beforeLatestPrice != null && afterLatestPrice === beforeLatestPrice) {
        setMessage(t("watchlist.messages.selectedPriceSame"));
        setMessageType("success");
        return "same";
      }
      setMessage(t("watchlist.messages.selectedPriceUpdated"));
      setMessageType("success");
      return "updated";
    } catch (error) {
      setMessage(t("watchlist.messages.selectedRefreshError"));
      setMessageType("error");
      throw error;
    } finally {
      setIsRefreshingSelectedWatch(false);
    }
  }

  async function updateWatchStatus(id: string, status: "active" | "paused"): Promise<void> {
    try {
      await apiFetch<Watch>(`/watchlist/${id}`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      await load();
      setMessage(status === "paused" ? t("watchlist.messages.flightPaused") : t("watchlist.messages.flightResumed"));
      setMessageType("success");
    } catch {
      setMessage(t("watchlist.messages.statusUpdateError"));
      setMessageType("error");
    }
  }

  async function deleteWatch(id: string): Promise<void> {
    try {
      await apiFetch<{ status: string }>(`/watchlist/${id}`, { method: "DELETE" });
      await load();
      setMessage(t("watchlist.messages.flightDeleted"));
      setMessageType("success");
    } catch {
      setMessage(t("watchlist.messages.deleteError"));
      setMessageType("error");
    }
  }

  async function bulkUpdateStatus(ids: string[], status: "active" | "paused"): Promise<void> {
    if (ids.length === 0) return;
    try {
      const response = await apiFetch<{
        status: string;
        requested: number;
        updated_ids: string[];
        failed: Array<{ watch_id: string; code: string }>;
      }>("/watchlist/status-bulk", {
        method: "POST",
        body: JSON.stringify({ watch_ids: ids, status }),
      });
      const failedCount = response.failed.length;
      await load();
      if (failedCount > 0) {
        setMessage(t("watchlist.messages.bulkPartialError", { failed: failedCount, total: response.requested }));
        setMessageType(failedCount === response.requested ? "error" : "success");
      } else {
        setMessage(status === "paused" ? t("watchlist.messages.flightsPaused") : t("watchlist.messages.flightsResumed"));
        setMessageType("success");
      }
    } catch {
      setMessage(t("watchlist.messages.statusUpdateError"));
      setMessageType("error");
    }
  }

  async function bulkDelete(ids: string[]): Promise<void> {
    if (ids.length === 0) return;
    try {
      const response = await apiFetch<{
        status: string;
        requested: number;
        deleted_ids: string[];
        failed: Array<{ watch_id: string; code: string }>;
      }>("/watchlist/delete-bulk", {
        method: "POST",
        body: JSON.stringify({ watch_ids: ids }),
      });
      const failedCount = response.failed.length;
      await load();
      if (failedCount > 0) {
        setMessage(t("watchlist.messages.bulkPartialError", { failed: failedCount, total: response.requested }));
        setMessageType(failedCount === response.requested ? "error" : "success");
      } else {
        setMessage(t("watchlist.messages.flightsDeleted"));
        setMessageType("success");
      }
    } catch {
      setMessage(t("watchlist.messages.deleteError"));
      setMessageType("error");
    }
  }

  return {
    refreshFiltered,
    refreshSelectedWatch,
    updateWatchStatus,
    deleteWatch,
    bulkUpdateStatus,
    bulkDelete,
  };
}
