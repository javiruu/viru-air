import { useCallback, useEffect } from "react";

import type { Watch } from "@/modules/watchlist/types";
import { useChartHover } from "@/modules/watchlist/useChartHover";
import { useWatchlistActions } from "@/modules/watchlist/useWatchlistActions";
import { useWatchlistDerived } from "@/modules/watchlist/useWatchlistDerived";
import { useWatchlistViewState } from "@/modules/watchlist/useWatchlistViewState";

type UseWatchlistControllerInput = {
  chartWidth: number;
  chartBaseHeight: number;
  chartPad: { left: number; right: number; top: number; bottom: number };
  lineColors: string[];
};

export function useWatchlistController({
  chartWidth,
  chartBaseHeight,
  chartPad,
  lineColors,
}: UseWatchlistControllerInput) {
  const view = useWatchlistViewState();

  const actions = useWatchlistActions({
    selectedOrigin: view.selectedOrigin,
    selectedDestination: view.selectedDestination,
    selectedDates: view.selectedDates,
    selectedWatchId: view.selectedWatchId,
    calendarCursor: view.calendarCursor,
    setSelectedOrigin: view.setSelectedOrigin,
    setSelectedDestination: view.setSelectedDestination,
    setSelectedDates: view.setSelectedDates,
    setSelectedWatchId: view.setSelectedWatchId,
    setCalendarCursor: view.setCalendarCursor,
  });

  const { compareIds, setCompareIds } = view;
  const { items } = actions;

  useEffect(() => {
    if (compareIds.length === 0) return;
    setCompareIds((prev) => prev.filter((id) => items.some((item) => item.id === id)));
  }, [compareIds, items, setCompareIds]);

  const { setSelectedWatchId, setSelectedOrigin, setSelectedDestination, setSelectedDates, setSelectedPoint } = view;
  const selectWatch = useCallback(
    (watch: Watch) => {
      setSelectedWatchId(watch.id);
      setSelectedOrigin(watch.origin_iata);
      setSelectedDestination(watch.destination_iata);
      setSelectedDates([watch.travel_date_local]);
      setSelectedPoint("");
    },
    [setSelectedDestination, setSelectedDates, setSelectedOrigin, setSelectedPoint, setSelectedWatchId],
  );

  const derived = useWatchlistDerived({
    items: actions.items,
    historyRows: actions.historyRows,
    selectedOrigin: view.selectedOrigin,
    selectedDestination: view.selectedDestination,
    selectedDates: view.selectedDates,
    selectedPoint: view.selectedPoint,
    rangeWindow: view.rangeWindow,
    watchSearch: view.watchSearch,
    watchSort: view.watchSort,
    selectedWatchId: view.selectedWatchId,
    compareIds: view.compareIds,
    calendarCursor: view.calendarCursor,
    chartBaseHeight,
    chartWidth,
    chartPad,
    lineColors,
  });

  const hover = useChartHover({
    points: derived.flatChartPoints,
    chartWidth,
    chartHeight: derived.chartHeight,
  });

  return {
    view,
    actions,
    derived,
    hover,
    selectWatch,
  };
}
