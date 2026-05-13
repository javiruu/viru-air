import { useCallback, useState } from "react";

import { useI18n } from "@/i18n";
import { shiftMonth } from "@/modules/watchlist/dateUtils";
import type { ListSort, RangeWindow, ViewMode } from "@/modules/watchlist/types";

export function useWatchlistViewState() {
  const { t } = useI18n();
  const [selectedOrigin, setSelectedOrigin] = useState("");
  const [selectedDestination, setSelectedDestination] = useState("");
  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [selectedPoint, setSelectedPoint] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("chart");
  const [calendarCursor, setCalendarCursor] = useState("");
  const [rangeWindow, setRangeWindow] = useState<RangeWindow>("30");
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareNotice, setCompareNotice] = useState("");
  const [selectedWatchId, setSelectedWatchId] = useState("");
  const [watchSearch, setWatchSearch] = useState("");
  const [watchSort, setWatchSort] = useState<ListSort>("freshness");

  const onOriginChange = useCallback((value: string) => {
    setSelectedOrigin(value);
    setSelectedDestination("");
    setSelectedDates([]);
    setSelectedPoint("");
  }, []);

  const onDestinationChange = useCallback((value: string) => {
    setSelectedDestination(value);
    setSelectedDates([]);
    setSelectedPoint("");
  }, []);

  const onDatesChange = useCallback((values: string[]) => {
    setSelectedDates(values);
    setSelectedPoint("");
  }, []);

  const toggleViewMode = useCallback(() => {
    setViewMode((current) => (current === "chart" ? "calendar" : "chart"));
  }, []);

  const toggleRangeWindow = useCallback(() => {
    setRangeWindow((current) => (current === "all" ? "30" : "all"));
  }, []);

  const resetZoom = useCallback(() => {
    setRangeWindow("30");
  }, []);

  const prevMonth = useCallback(() => {
    setCalendarCursor((month) => shiftMonth(month, -1));
  }, []);

  const nextMonth = useCallback(() => {
    setCalendarCursor((month) => shiftMonth(month, 1));
  }, []);

  const toggleCompare = useCallback((id: string) => {
    setCompareNotice("");
    setCompareIds((prev) => {
      if (prev.includes(id)) return prev.filter((item) => item !== id);
      if (prev.length >= 4) {
        setCompareNotice(t("watchlist.compare.maxSelectionMessage"));
        return prev;
      }
      return [...prev, id];
    });
  }, [t]);

  return {
    selectedOrigin,
    selectedDestination,
    selectedDates,
    selectedPoint,
    viewMode,
    calendarCursor,
    rangeWindow,
    compareIds,
    compareNotice,
    selectedWatchId,
    watchSearch,
    watchSort,
    setSelectedOrigin,
    setSelectedDestination,
    setSelectedDates,
    setSelectedPoint,
    setCalendarCursor,
    setRangeWindow,
    setSelectedWatchId,
    setWatchSearch,
    setWatchSort,
    setCompareIds,
    onOriginChange,
    onDestinationChange,
    onDatesChange,
    toggleViewMode,
    toggleRangeWindow,
    resetZoom,
    prevMonth,
    nextMonth,
    toggleCompare,
  };
}
