"use client";

import { useEffect, useMemo, useState } from "react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { fetchDoorToDoorProviderStatus } from "@/modules/door-to-door/api";
import { buildMapCapabilities, filterSavedPlacesForWatch } from "@/modules/door-to-door/mapHub";
import type {
  DoorToDoorProviderStatus,
  DoorToDoorResponse,
  DoorToDoorSavedPlace,
} from "@/modules/door-to-door/types";

function normalizeLabel(value: string) {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

export function useDoorToDoorMapHub(response: DoorToDoorResponse | null, selectedWatchId: string) {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [providerStatus, setProviderStatus] = useState<DoorToDoorProviderStatus[]>([]);
  const [savedPlaces, setSavedPlaces] = useState<DoorToDoorSavedPlace[]>([]);
  const [savedPlaceLabel, setSavedPlaceLabel] = useState("");
  const [savedPlaceNote, setSavedPlaceNote] = useState("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    fetchDoorToDoorProviderStatus()
      .then((items) => setProviderStatus(items))
      .catch(() => setProviderStatus([]));
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem("viru_d2d_saved_places_v1");
      if (!raw) return;
      const parsed = JSON.parse(raw) as DoorToDoorSavedPlace[];
      if (Array.isArray(parsed)) setSavedPlaces(parsed.slice(0, 12));
    } catch {
      setSavedPlaces([]);
    }
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    window.localStorage.setItem("viru_d2d_saved_places_v1", JSON.stringify(savedPlaces.slice(0, 12)));
  }, [savedPlaces, mounted]);

  const providerStatusSummary = useMemo(() => {
    const enabled = providerStatus.filter((p) => p.enabled);
    const realEnabled = enabled.filter((p) => p.source_type !== "mock" && p.source_type !== "estimate");
    const estimateEnabled = enabled.filter((p) => p.source_type === "mock" || p.source_type === "estimate");
    return { enabled: enabled.length, realEnabled: realEnabled.length, estimateEnabled: estimateEnabled.length };
  }, [providerStatus]);

  const mapCapabilities = useMemo(
    () => buildMapCapabilities(response, providerStatus),
    [response, providerStatus],
  );

  const visibleSavedPlaces = useMemo(
    () => filterSavedPlacesForWatch(savedPlaces, selectedWatchId),
    [savedPlaces, selectedWatchId],
  );

  function addSavedPlace() {
    const label = savedPlaceLabel.trim();
    const note = savedPlaceNote.trim();
    if (!label) return;
    const duplicate = savedPlaces.some((item) => {
      const sameScope = (item.watch_id || "") === (selectedWatchId || "");
      return sameScope && normalizeLabel(item.label) === normalizeLabel(label);
    });
    if (duplicate) {
      notify({ tone: "warning", title: t("doorToDoor.mapHub.savedPlaces.savedToast") });
      return;
    }
    const item: DoorToDoorSavedPlace = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      label,
      note,
      created_at: new Date().toISOString(),
      watch_id: selectedWatchId || null,
    };
    setSavedPlaces((current) => [item, ...current].slice(0, 12));
    setSavedPlaceLabel("");
    setSavedPlaceNote("");
    notify({ tone: "success", title: t("doorToDoor.mapHub.savedPlaces.savedToast") });
  }

  function removeSavedPlace(id: string) {
    setSavedPlaces((current) => current.filter((item) => item.id !== id));
    notify({ tone: "success", title: t("doorToDoor.mapHub.savedPlaces.deletedToast") });
  }

  return {
    providerStatus,
    providerStatusSummary,
    mapCapabilities,
    savedPlaces,
    savedPlaceLabel,
    setSavedPlaceLabel,
    savedPlaceNote,
    setSavedPlaceNote,
    visibleSavedPlaces,
    addSavedPlace,
    removeSavedPlace,
  };
}
