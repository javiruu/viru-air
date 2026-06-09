"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import {
  createDoorToDoorSavedPlace,
  deleteDoorToDoorSavedPlace,
  fetchDoorToDoorProviderStatus,
  fetchDoorToDoorSavedPlaces,
} from "@/modules/door-to-door/api";
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
    fetchDoorToDoorSavedPlaces(selectedWatchId || undefined)
      .then((items) => {
        // If backend is empty, try migrating from localStorage one time
        if (items.length === 0 && typeof window !== "undefined") {
          try {
            const raw = window.localStorage.getItem("viru_d2d_saved_places_v1");
            if (raw) {
              const parsed = JSON.parse(raw) as DoorToDoorSavedPlace[];
              if (Array.isArray(parsed) && parsed.length > 0) {
                // Migrate each item to backend
                Promise.all(
                  parsed.map((item) =>
                    createDoorToDoorSavedPlace({
                      label: item.label,
                      note: item.note || "",
                      watch_id: item.watch_id || null,
                    }).catch(() => null),
                  ),
                ).then(async () => {
                  // Refetch first, then clear localStorage only on success
                  try {
                    const migrated = await fetchDoorToDoorSavedPlaces(selectedWatchId || undefined);
                    if (migrated && migrated.length > 0) {
                      window.localStorage.removeItem("viru_d2d_saved_places_v1");
                    }
                    setSavedPlaces((migrated || []).slice(0, 12));
                  } catch {
                    // Refetch failed — keep localStorage as safety net
                    setSavedPlaces(parsed.slice(0, 12));
                  }
                }).catch(() => {
                  // Migration failed — keep localStorage items visible
                  setSavedPlaces(parsed.slice(0, 12));
                });
                return;
              }
            }
          } catch {
            // Ignore migration errors
          }
        }
        setSavedPlaces(items.slice(0, 12));
      })
      .catch(() => setSavedPlaces([]));
    setMounted(true);
  }, [selectedWatchId]);

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

  const addSavedPlace = useCallback(async () => {
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
    try {
      const created = await createDoorToDoorSavedPlace({
        label,
        note,
        watch_id: selectedWatchId || null,
      });
      setSavedPlaces((current) => [created, ...current].slice(0, 12));
      setSavedPlaceLabel("");
      setSavedPlaceNote("");
      notify({ tone: "success", title: t("doorToDoor.mapHub.savedPlaces.savedToast") });
    } catch {
      notify({ tone: "error", title: t("doorToDoor.mapHub.savedPlaces.saveError") });
    }
  }, [savedPlaceLabel, savedPlaceNote, savedPlaces, selectedWatchId, notify, t]);

  const removeSavedPlace = useCallback(async (id: string) => {
    try {
      await deleteDoorToDoorSavedPlace(id);
      setSavedPlaces((current) => current.filter((item) => item.id !== id));
      notify({ tone: "success", title: t("doorToDoor.mapHub.savedPlaces.deletedToast") });
    } catch {
      notify({ tone: "error", title: t("doorToDoor.mapHub.savedPlaces.deleteError") });
    }
  }, [notify, t]);

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
