import { FormEvent, useEffect, useState } from "react";

import { useI18n } from "@/i18n";
import { trackUxEvent } from "@/lib/uxTracking";
import { apiFetch } from "@/modules/shared/api";
import { COUNTRY_AIRPORTS, CountryAirports, findCountryByIata } from "@/modules/shared/airports";
import { summarizeRefreshBulkResult } from "@/modules/watchlist/summary";
import { toIsoMonth } from "@/modules/watchlist/dateUtils";
import type { CompatibleResponse, HistoryRow, PriceSummary, Snapshot, Watch, WatchDetail } from "@/modules/watchlist/types";

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

  async function load(): Promise<void> {
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

      if (!selectedWatchId && rows.length > 0) {
        setSelectedWatchId(rows[0].id);
      }

      const snapshots = rows.length
        ? await apiFetch<Array<Snapshot & { watch_id: string }>>("/prices/history/batch", {
            method: "POST",
            body: JSON.stringify({ watch_ids: rows.map((watch) => watch.id) }),
          })
        : [];

      const watchMap = new Map(rows.map((watch) => [watch.id, watch]));
      const merged = snapshots
        .map<HistoryRow | null>((snapshot) => {
          const watch = watchMap.get(snapshot.watch_id);
          if (!watch) return null;
          return {
            watchId: watch.id,
            origin: watch.origin_iata,
            destination: watch.destination_iata,
            travelDate: watch.travel_date_local,
            capturedAt: snapshot.captured_at_utc,
            price: snapshot.raw_price,
            currency: snapshot.raw_currency,
            departureTime: snapshot.departure_time_local,
          };
        })
        .filter((row): row is HistoryRow => Boolean(row));
      setHistoryRows(merged);

      if (rows.length > 0 && !rows.some((row) => row.id === selectedWatchId)) {
        setSelectedWatchId(rows[0].id);
      }

      if (!calendarCursor) {
        const seed = merged[0]?.travelDate || rows[0]?.travel_date_local || "";
        setCalendarCursor(toIsoMonth(seed));
      }
    } catch (error) {
      setListErrorMessage(t("watchlist.smartList.inlineLoadError"));
      throw error;
    } finally {
      setIsLoadingHistoryInitial(false);
      setIsLoadingWatchlist(false);
    }
  }

  useEffect(() => {
    load()
      .catch(() => {
        setMessage(t("watchlist.messages.loadError"));
        setMessageType("error");
      })
      .finally(() => setIsLoadingWatchlist(false));
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

  useEffect(() => {
    if (!travelDate) {
      setCompatibleOrigins([]);
      setCompatibleDestinations([]);
      setOrigin("");
      setDestination("");
      return;
    }

    if (!origin) {
      setCompatibleDestinations([]);
      return;
    }

    apiFetch<CompatibleResponse>(`/airports/compatible?origin_iata=${origin}&travel_date=${travelDate}`)
      .then((data) => {
        setCompatibleDestinations(data.compatible_iata);
        if (destination && data.compatible_iata.length > 0 && !data.compatible_iata.includes(destination)) {
          setDestination("");
        }
      })
      .catch(() => setCompatibleDestinations([]));
  }, [origin, travelDate, destination]);

  useEffect(() => {
    if (!travelDate) {
      setCompatibleOrigins([]);
      return;
    }

    if (!destination) {
      setCompatibleOrigins([]);
      return;
    }

    apiFetch<CompatibleResponse>(`/airports/compatible?destination_iata=${destination}&travel_date=${travelDate}`)
      .then((data) => {
        setCompatibleOrigins(data.compatible_iata);
        if (origin && data.compatible_iata.length > 0 && !data.compatible_iata.includes(origin)) {
          setOrigin("");
        }
      })
      .catch(() => setCompatibleOrigins([]));
  }, [destination, travelDate, origin]);

  useEffect(() => {
    if (!selectedWatchId) {
      setSelectedWatchDetail(null);
      setSelectedWatchSummary(null);
      return;
    }
    let isMounted = true;
    setIsLoadingSelectedWatchDetail(true);
    Promise.all([
      apiFetch<WatchDetail>(`/watchlist/${selectedWatchId}`),
      apiFetch<PriceSummary>(`/prices/summary?watch_id=${selectedWatchId}`),
    ])
      .then(([detail, summary]) => {
        if (!isMounted) return;
        setSelectedWatchDetail(detail);
        setSelectedWatchSummary(summary);
      })
      .catch(() => {
        if (!isMounted) return;
        setSelectedWatchDetail(null);
        setSelectedWatchSummary(null);
      })
      .finally(() => {
        if (isMounted) setIsLoadingSelectedWatchDetail(false);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedWatchId]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setMessageType("error");

    if (!travelDate) {
      setMessage(t("watchlist.messages.selectDateBeforeSave"));
      return;
    }
    if (!origin || !destination) {
      setMessage(t("watchlist.messages.completeRoute"));
      return;
    }
    if (compatibleDestinations.length > 0 && !compatibleDestinations.includes(destination)) {
      setMessage(t("watchlist.messages.destinationNotCompatible"));
      return;
    }
    if (compatibleOrigins.length > 0 && !compatibleOrigins.includes(origin)) {
      setMessage(t("watchlist.messages.originNotCompatible"));
      return;
    }

    try {
      await apiFetch<Watch>("/watchlist", {
        method: "POST",
        body: JSON.stringify({
          origin_iata: origin,
          destination_iata: destination,
          travel_date_local: travelDate,
          target_price: targetPrice ? Number(targetPrice) : null,
        }),
      });
      await load();
      setMessage(t("watchlist.messages.flightCreated"));
      setMessageType("success");
      setShowAdd(false);
      setOrigin("");
      setDestination("");
      setTravelDate("");
      setTargetPrice("");
    } catch {
      setMessage(t("watchlist.messages.createError"));
      setMessageType("error");
    }
  }

  async function refresh(id: string): Promise<void> {
    setRefreshingWatchId(id);
    try {
      await apiFetch<{ status: string }>(`/watchlist/${id}/refresh-now`, { method: "POST" });
      void trackUxEvent("watchlist_refresh", { scope: "single" });
      await load();
      setMessage(t("watchlist.messages.refreshLaunched"));
      setMessageType("success");
    } catch {
      setMessage(t("watchlist.messages.refreshError"));
      setMessageType("error");
    } finally {
      setRefreshingWatchId((current) => (current === id ? null : current));
    }
  }

  async function refreshFiltered(): Promise<void> {
    setMessage("");

    const targets = items.filter(
      (item) =>
        item.origin_iata === selectedOrigin &&
        item.destination_iata === selectedDestination &&
        (selectedDates.length === 0 || selectedDates.includes(item.travel_date_local)),
    );

    if (targets.length === 0) {
      setMessage(t("watchlist.messages.noFlightsForFilteredRefresh"));
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
        t("watchlist.messages.bulkRefreshSummary", { updated: summary.updated, skippedCooldown: summary.skippedCooldown, failed: summary.failed, degradedOrStale: summary.degradedOrStale }),
      );
      setMessageType("success");
    } catch {
      setMessage(t("watchlist.messages.filteredRefreshError"));
      setMessageType("error");
    } finally {
      setIsRefreshingFiltered(false);
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
    await Promise.allSettled(
      ids.map((id) =>
        apiFetch<Watch>(`/watchlist/${id}`, {
          method: "PUT",
          body: JSON.stringify({ status }),
        }),
      ),
    );
    await load();
    setMessage(status === "paused" ? t("watchlist.messages.flightsPaused") : t("watchlist.messages.flightsResumed"));
    setMessageType("success");
  }

  async function bulkDelete(ids: string[]): Promise<void> {
    if (ids.length === 0) return;
    await Promise.allSettled(ids.map((id) => apiFetch<{ status: string }>(`/watchlist/${id}`, { method: "DELETE" })));
    await load();
    setMessage(t("watchlist.messages.flightsDeleted"));
    setMessageType("success");
  }

  async function bulkRefresh(ids: string[]): Promise<void> {
    if (ids.length === 0) return;
    setIsRefreshingBulk(true);
    try {
      const response = await apiFetch<{
        status: string;
        requested: number;
        refreshed: string[];
        failed: Array<{ watch_id: string; code: string }>;
      }>("/watchlist/refresh-bulk", {
        method: "POST",
        body: JSON.stringify({ watch_ids: ids }),
      });
      const summary = summarizeRefreshBulkResult(response);
      await load();
      setMessage(
        t("watchlist.messages.bulkRefreshSummary", { updated: summary.updated, skippedCooldown: summary.skippedCooldown, failed: summary.failed, degradedOrStale: summary.degradedOrStale }),
      );
      setMessageType("success");
    } catch {
      setMessage(t("watchlist.messages.selectionRefreshError"));
      setMessageType("error");
    } finally {
      setIsRefreshingBulk(false);
    }
  }

  function openPicker(which: PickerField): void {
    if (!travelDate) {
      setMessage(t("watchlist.messages.selectDateBeforeAirports"));
      setMessageType("error");
      return;
    }
    const current = which === "origin" ? origin : destination;
    const country = findCountryByIata(current) || COUNTRY_AIRPORTS[0] || null;
    setSelectedCountry(country);
    setActivePicker(which);
  }

  function clearSelection(): void {
    if (activePicker === "origin") setOrigin("");
    if (activePicker === "destination") setDestination("");
  }

  function selectAirport(iata: string): void {
    if (activePicker === "origin") {
      setOrigin(iata);
    } else if (activePicker === "destination") {
      setDestination(iata);
    }
    setActivePicker(null);
  }

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
