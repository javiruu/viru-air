import { useEffect, useState } from "react";

import { useI18n } from "@/i18n";
import { COUNTRY_AIRPORTS, CountryAirports, findCountryByIata } from "@/modules/shared/airports";
import { useWatchlistCompatibility } from "@/modules/watchlist/useWatchlistCompatibility";
import { useWatchlistDataLoader } from "@/modules/watchlist/useWatchlistDataLoader";
import { useWatchlistDetail } from "@/modules/watchlist/useWatchlistDetail";
import { useWatchlistForm } from "@/modules/watchlist/useWatchlistForm";
import { useWatchlistMutations } from "@/modules/watchlist/useWatchlistMutations";
import type { HistoryRow, PriceSummary, Watch, WatchDetail } from "@/modules/watchlist/types";

type MessageType = "error" | "success";
type PickerField = "origin" | "destination";
type UseWatchlistActionsInput = {
  selectedOrigin: string;
  selectedDestination: string;
  selectedDates: string[];
  selectedWatchId: string;
  calendarCursor: string;
  setSelectedOrigin: (value: string) => void;
  setSelectedDestination: (value: string) => void;
  setSelectedDates: (value: string[]) => void;
  setSelectedWatchId: (value: string) => void;
  setCalendarCursor: (value: string | ((prev: string) => string)) => void;
};

export function useWatchlistActions({
  selectedOrigin,
  selectedDestination,
  selectedDates,
  selectedWatchId,
  calendarCursor,
  setSelectedOrigin,
  setSelectedDestination,
  setSelectedDates,
  setSelectedWatchId,
  setCalendarCursor,
}: UseWatchlistActionsInput) {
  const { t } = useI18n();
  const [items, setItems] = useState<Watch[]>([]);
  const [historyRows, setHistoryRows] = useState<HistoryRow[]>([]);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [travelDate, setTravelDate] = useState("");
  const [targetPrice, setTargetPrice] = useState("");
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<MessageType>("error");
  const [showAdd, setShowAdd] = useState(false);
  const [activePicker, setActivePicker] = useState<PickerField | null>(null);
  const [refreshingWatchId, setRefreshingWatchId] = useState<string | null>(null);
  const [isRefreshingFiltered, setIsRefreshingFiltered] = useState(false);
  const [isRefreshingBulk, setIsRefreshingBulk] = useState(false);
  const [isLoadingWatchlist, setIsLoadingWatchlist] = useState(true);
  const [isLoadingHistoryInitial, setIsLoadingHistoryInitial] = useState(true);
  const [selectedWatchDetail, setSelectedWatchDetail] = useState<WatchDetail | null>(null);
  const [selectedWatchSummary, setSelectedWatchSummary] = useState<PriceSummary | null>(null);
  const [isLoadingSelectedWatchDetail, setIsLoadingSelectedWatchDetail] = useState(false);
  const [listErrorMessage, setListErrorMessage] = useState("");
  const [selectedCountry, setSelectedCountry] = useState<CountryAirports | null>(
    findCountryByIata("MAD") || COUNTRY_AIRPORTS[0] || null,
  );
  const [compatibleOrigins, setCompatibleOrigins] = useState<string[]>([]);
  const [compatibleDestinations, setCompatibleDestinations] = useState<string[]>([]);
  const { load } = useWatchlistDataLoader({
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
    inlineLoadErrorMessage: t("watchlist.smartList.inlineLoadError"),
  });

  useEffect(() => {
    load()
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!showAdd) return;

    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowAdd(false);
        setActivePicker(null);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [showAdd]);

  useWatchlistCompatibility({
    origin,
    destination,
    travelDate,
    setOrigin,
    setDestination,
    setCompatibleOrigins,
    setCompatibleDestinations,
  });

  useWatchlistDetail({
    selectedWatchId,
    setSelectedWatchDetail,
    setSelectedWatchSummary,
    setIsLoadingSelectedWatchDetail,
  });

  const { refresh, refreshFiltered, updateWatchStatus, deleteWatch, bulkUpdateStatus, bulkDelete, bulkRefresh } =
    useWatchlistMutations({
      t,
      load,
      items,
      selectedOrigin,
      selectedDestination,
      selectedDates,
      setMessage,
      setMessageType,
      setRefreshingWatchId,
      setIsRefreshingFiltered,
      setIsRefreshingBulk,
    });

  const { onSubmit, openPicker, clearSelection, selectAirport } = useWatchlistForm({
    t,
    origin,
    destination,
    travelDate,
    targetPrice,
    activePicker,
    compatibleOrigins,
    compatibleDestinations,
    setOrigin,
    setDestination,
    setTravelDate,
    setTargetPrice,
    setMessage,
    setMessageType,
    setShowAdd,
    setActivePicker,
    setSelectedCountry,
    load,
  });

  return {
    items,
    historyRows,
    origin,
    destination,
    travelDate,
    targetPrice,
    message,
    messageType,
    showAdd,
    activePicker,
    refreshingWatchId,
    isRefreshingFiltered,
    isRefreshingBulk,
    isLoadingWatchlist,
    isLoadingHistoryInitial,
    selectedWatchDetail,
    selectedWatchSummary,
    isLoadingSelectedWatchDetail,
    listErrorMessage,
    selectedCountry,
    compatibleOrigins,
    compatibleDestinations,
    setOrigin,
    setDestination,
    setTravelDate,
    setTargetPrice,
    setShowAdd,
    setActivePicker,
    setSelectedCountry,
    load,
    onSubmit,
    refresh,
    refreshFiltered,
    updateWatchStatus,
    deleteWatch,
    bulkUpdateStatus,
    bulkDelete,
    bulkRefresh,
    openPicker,
    clearSelection,
    selectAirport,
  };
}

