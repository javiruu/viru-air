"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { fetchSavedDoorToDoorLocation, searchDoorToDoor } from "@/modules/door-to-door/api";
import { DEFAULT_PREFERENCES } from "@/modules/door-to-door/constants";
import type {
  DoorToDoorLocation,
  DoorToDoorPreferences,
  DoorToDoorResponse,
} from "@/modules/door-to-door/types";
import { apiFetch } from "@/modules/shared/api";
import type { Watch } from "@/modules/watchlist/types";

function normalizeLabel(value: string) {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

export function useDoorToDoorSearch() {
  const searchParams = useSearchParams();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const watchIdParam = searchParams?.get("watchId") || "";

  const defaultOrigin = useMemo<DoorToDoorLocation>(
    () => ({ type: "city", label: t("doorToDoor.defaults.origin"), lat: 36.834, lng: -2.463 }),
    [t],
  );
  const defaultDestination = useMemo<DoorToDoorLocation>(
    () => ({ type: "city", label: t("doorToDoor.defaults.destination") }),
    [t],
  );

  const [watches, setWatches] = useState<Watch[]>([]);
  const [selectedWatchId, setSelectedWatchId] = useState(watchIdParam);
  const [origin, setOrigin] = useState<DoorToDoorLocation>(defaultOrigin);
  const [finalDestination, setFinalDestination] = useState<DoorToDoorLocation>(defaultDestination);
  const [preferences, setPreferences] = useState<DoorToDoorPreferences>(DEFAULT_PREFERENCES);
  const [saveOrigin, setSaveOrigin] = useState(false);
  const [status, setStatus] = useState<"empty" | "loading" | "success" | "partial" | "error" | "no_coverage">("empty");
  const [response, setResponse] = useState<DoorToDoorResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const requestIdRef = useRef(0);

  const selectedWatch = useMemo(
    () => watches.find((w) => w.id === selectedWatchId) || null,
    [watches, selectedWatchId],
  );
  const isSubmitBlocked = status === "loading" || !selectedWatch;

  useEffect(() => {
    setSelectedWatchId(watchIdParam);
  }, [watchIdParam]);

  useEffect(() => {
    apiFetch<Watch[]>("/watchlist")
      .then((items) => {
        setWatches(items);
        setSelectedWatchId((c) => c || watchIdParam || items[0]?.id || "");
      })
      .catch(() => setWatches([]));
    fetchSavedDoorToDoorLocation()
      .then((saved) => {
        if (saved) setOrigin({ type: saved.type, label: saved.label, lat: saved.lat, lng: saved.lng });
      })
      .catch(() => undefined);
  }, [watchIdParam]);

  useEffect(() => {
    setOrigin((current) => (current.label ? current : defaultOrigin));
    setFinalDestination((current) => (current.label ? current : defaultDestination));
  }, [defaultDestination, defaultOrigin]);

  useEffect(() => {
    if (!selectedWatch) return;
    setFinalDestination((current) => {
      if (current.type !== "airport_only") return current;
      const nextLabel = t("doorToDoor.defaults.airportOnly", { iata: selectedWatch.destination_iata || "TSF" });
      if (current.label === nextLabel) return current;
      return { ...current, label: nextLabel };
    });
  }, [selectedWatch, t]);

  useEffect(() => {
    setResponse(null);
    setErrorMessage("");
    setStatus("empty");
  }, [selectedWatchId]);

  const calculate = useCallback(async () => {
    if (!selectedWatch) {
      setStatus("empty");
      setErrorMessage(t("doorToDoor.chooseWatchedRoute"));
      return;
    }
    const normalizedOrigin = normalizeLabel(origin.label);
    const normalizedDestination = normalizeLabel(finalDestination.label);
    if (normalizedOrigin.length < 2 || normalizedDestination.length < 2) {
      setStatus("empty");
      setErrorMessage(t("doorToDoor.states.emptyBodyWithWatch"));
      notify({ tone: "error", title: t("doorToDoor.states.emptyTitleWithWatch") });
      return;
    }
    if (finalDestination.type !== "airport_only" && normalizedOrigin === normalizedDestination) {
      setStatus("empty");
      setErrorMessage(t("doorToDoor.states.emptyBodyWithWatch"));
      notify({ tone: "error", title: t("doorToDoor.states.emptyTitleWithWatch") });
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setStatus("loading");
    setErrorMessage("");
    try {
      const data = await searchDoorToDoor({
        flight_watch_id: selectedWatch.id,
        origin,
        final_destination: finalDestination,
        preferences,
        save_origin_as_default: saveOrigin,
      });
      if (requestId !== requestIdRef.current) return;
      setResponse(data);
      const noCoverageWarning = data.warnings.some((w) => w.code === "NO_COVERAGE");
      if (data.options.length === 0 || noCoverageWarning) {
        setStatus("no_coverage");
      } else if (data.warnings.length > 0) {
        setStatus("partial");
      } else {
        setStatus("success");
      }
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      setErrorMessage(error instanceof Error ? error.message : "Error inesperado");
      setStatus("error");
    }
  }, [finalDestination, notify, origin, preferences, saveOrigin, selectedWatch, t]);

  return {
    watches,
    selectedWatchId,
    setSelectedWatchId,
    selectedWatch,
    origin,
    setOrigin,
    defaultOrigin,
    finalDestination,
    setFinalDestination,
    defaultDestination,
    preferences,
    setPreferences,
    saveOrigin,
    setSaveOrigin,
    status,
    response,
    errorMessage,
    calculate,
    isSubmitBlocked,
  };
}
