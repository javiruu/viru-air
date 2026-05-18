import { useCallback, useRef } from "react";

import { apiFetch } from "@/modules/shared/api";
import { toIsoMonth } from "@/modules/watchlist/dateUtils";
import { mapSnapshotsToHistoryRows } from "@/modules/watchlist/watchlistActions.helpers";
import type { HistoryRow, Snapshot, Watch } from "@/modules/watchlist/types";

type UseWatchlistDataLoaderInput = {
  selectedOrigin: string;
  selectedWatchId: string;
  calendarCursor: string;
  setSelectedOrigin: (value: string) => void;
  setSelectedDestination: (value: string) => void;
  setSelectedDates: (value: string[]) => void;
  setSelectedWatchId: (value: string) => void;
  setCalendarCursor: (value: string | ((prev: string) => string)) => void;
  setItems: (value: Watch[]) => void;
  setHistoryRows: (value: HistoryRow[]) => void;
  setListErrorMessage: (value: string) => void;
  setIsLoadingHistoryInitial: (value: boolean) => void;
  setIsLoadingWatchlist: (value: boolean) => void;
  inlineLoadErrorMessage: string;
};

export function resolveSelectedWatchId(rows: Pick<Watch, "id">[], currentSelectedWatchId: string): string {
  if (rows.length === 0) return "";
  if (currentSelectedWatchId && rows.some((row) => row.id === currentSelectedWatchId)) {
    return currentSelectedWatchId;
  }
  return rows[0].id;
}

export function useWatchlistDataLoader({
  selectedOrigin,
  selectedWatchId,
  calendarCursor,
  setSelectedOrigin,
  setSelectedDestination,
  setSelectedDates,
  setSelectedWatchId,
  setCalendarCursor,
  setItems,
  setHistoryRows,
  setListErrorMessage,
  setIsLoadingHistoryInitial,
  setIsLoadingWatchlist,
  inlineLoadErrorMessage,
}: UseWatchlistDataLoaderInput) {
  const selectedWatchIdRef = useRef(selectedWatchId);
  selectedWatchIdRef.current = selectedWatchId;

  const load = useCallback(async (): Promise<void> => {
    setIsLoadingWatchlist(true);
    setIsLoadingHistoryInitial(true);
    try {
      const rows = await apiFetch<Watch[]>("/watchlist");
      setListErrorMessage("");
      setItems(rows);

      if (!selectedOrigin && rows.length > 0) {
        setSelectedOrigin(rows[0].origin_iata);
        setSelectedDestination(rows[0].destination_iata);
        setSelectedDates([rows[0].travel_date_local]);
      }

      const snapshots = rows.length
        ? await apiFetch<Array<Snapshot & { watch_id: string }>>("/prices/history/batch", {
            method: "POST",
            body: JSON.stringify({ watch_ids: rows.map((watch) => watch.id) }),
          })
        : [];

      const merged = mapSnapshotsToHistoryRows(rows, snapshots);
      setHistoryRows(merged);

      const nextSelectedWatchId = resolveSelectedWatchId(rows, selectedWatchIdRef.current);
      if (nextSelectedWatchId !== selectedWatchIdRef.current) {
        setSelectedWatchId(nextSelectedWatchId);
      }

      if (!calendarCursor) {
        const seed = merged[0]?.travelDate || rows[0]?.travel_date_local || "";
        setCalendarCursor(toIsoMonth(seed));
      }
    } catch (error) {
      setListErrorMessage(inlineLoadErrorMessage);
      throw error;
    } finally {
      setIsLoadingHistoryInitial(false);
      setIsLoadingWatchlist(false);
    }
  }, [
    calendarCursor,
    inlineLoadErrorMessage,
    selectedOrigin,
    setCalendarCursor,
    setHistoryRows,
    setIsLoadingHistoryInitial,
    setIsLoadingWatchlist,
    setItems,
    setListErrorMessage,
    setSelectedDates,
    setSelectedDestination,
    setSelectedOrigin,
    setSelectedWatchId,
  ]);

  return { load };
}
