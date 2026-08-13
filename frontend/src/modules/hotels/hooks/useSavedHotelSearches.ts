"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createSavedHotelSearch,
  deleteSavedHotelSearch,
  listSavedHotelSearches,
  updateSavedHotelSearch,
} from "../api";
import type { HotelSavedSearchOut } from "../types";

export function useSavedHotelSearches() {
  const [savedSearches, setSavedSearches] = useState<HotelSavedSearchOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const refreshSavedSearches = useCallback(async () => {
    setLoading(true);
    try {
      setSavedSearches(await listSavedHotelSearches());
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "saved_search_load_failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshSavedSearches();
  }, [refreshSavedSearches]);

  const saveSearch = useCallback(async (query: Record<string, unknown>, label?: string) => {
    setSaving(true);
    try {
      const saved = await createSavedHotelSearch({ query, label: label?.trim() || null });
      setSavedSearches((current) => [saved, ...current.filter((item) => item.id !== saved.id)]);
      setMutationError(null);
      return saved;
    } catch (cause) {
      setMutationError(cause instanceof Error ? cause.message : "saved_search_save_failed");
      return null;
    } finally {
      setSaving(false);
    }
  }, []);

  const setStatus = useCallback(async (id: string, status: "active" | "paused") => {
    setBusyId(id);
    try {
      const updated = await updateSavedHotelSearch(id, { status });
      setSavedSearches((current) => current.map((item) => item.id === id ? updated : item));
      setMutationError(null);
    } catch (cause) {
      setMutationError(cause instanceof Error ? cause.message : "saved_search_update_failed");
    } finally {
      setBusyId(null);
    }
  }, []);

  const removeSearch = useCallback(async (id: string) => {
    setBusyId(id);
    try {
      await deleteSavedHotelSearch(id);
      setSavedSearches((current) => current.filter((item) => item.id !== id));
      setMutationError(null);
    } catch (cause) {
      setMutationError(cause instanceof Error ? cause.message : "saved_search_delete_failed");
    } finally {
      setBusyId(null);
    }
  }, []);

  return { savedSearches, loading, error: error || mutationError, busyId, saving, refreshSavedSearches, saveSearch, setStatus, removeSearch };
}
