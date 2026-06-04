"use client";

import { useCallback, useEffect, useState } from "react";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import {
  addHotelCompSetMember,
  createHotelCompSet,
  deleteHotelCompSetMember,
  getHotelCompSetDetail,
  getHotelDetail,
  getHotelNearbySuggestions,
  HotelsRequestError,
  listHotelCompSets,
} from "../api";
import type {
  HotelCompSetDetailOut,
  HotelCompSetOut,
  HotelDetailOut,
  HotelNearbySuggestionOut,
} from "../types";
import { resolveHotelMessage } from "./useHotelSearch";

export function useHotelCompSets() {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [compSets, setCompSets] = useState<HotelCompSetOut[]>([]);
  const [selectedCompSet, setSelectedCompSet] = useState<HotelCompSetDetailOut | null>(null);
  const [compSetAnchorDetail, setCompSetAnchorDetail] = useState<HotelDetailOut | null>(null);
  const [anchorLoading, setAnchorLoading] = useState(false);
  const [anchorError, setAnchorError] = useState<string | null>(null);
  const [anchorCache, setAnchorCache] = useState<Record<string, HotelDetailOut>>({});
  const [nearbySuggestions, setNearbySuggestions] = useState<HotelNearbySuggestionOut[]>([]);
  const [nearbyLoading, setNearbyLoading] = useState(false);
  const [nearbyMessage, setNearbyMessage] = useState<string | null>(null);

  const refreshCompSets = useCallback(async () => {
    const next = await listHotelCompSets();
    setCompSets(next);
  }, []);

  const handleCreateCompSet = useCallback(
    async (name: string, anchorHotelId: string) => {
      try {
        const created = await createHotelCompSet({ name, anchor_hotel_id: anchorHotelId });
        await refreshCompSets();
        const detail = await getHotelCompSetDetail(created.id);
        setSelectedCompSet(detail);
        notify({ tone: "success", title: t("hotels.messages.compSetCreated") });
      } catch (error) {
        const message = error instanceof Error ? error.message : t("shared.errors.generic");
        notify({ tone: "error", title: message });
      }
    },
    [refreshCompSets, notify, t],
  );

  const handleSelectCompSet = useCallback(async (compSetId: string) => {
    const detail = await getHotelCompSetDetail(compSetId);
    setSelectedCompSet(detail);
  }, []);

  const handleAddMember = useCallback(
    async (compSetId: string, hotelId: string) => {
      try {
        await addHotelCompSetMember(compSetId, { hotel_id: hotelId });
        const detail = await getHotelCompSetDetail(compSetId);
        setSelectedCompSet(detail);
        notify({ tone: "success", title: t("hotels.messages.memberAdded") });
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        notify({ tone: "error", title: message });
      }
    },
    [notify, t],
  );

  const handleDeleteMember = useCallback(
    async (compSetId: string, memberId: string) => {
      try {
        await deleteHotelCompSetMember(compSetId, memberId);
        const detail = await getHotelCompSetDetail(compSetId);
        setSelectedCompSet(detail);
        notify({ tone: "success", title: t("hotels.messages.memberRemoved") });
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        notify({ tone: "error", title: message });
      }
    },
    [notify, t],
  );

  // Hydrate anchor detail when selectedCompSet changes
  useEffect(() => {
    const anchorHotelId = selectedCompSet?.anchor_hotel_id;
    if (!anchorHotelId) {
      setCompSetAnchorDetail(null);
      setAnchorError(null);
      setAnchorLoading(false);
      return;
    }

    const cached = anchorCache[anchorHotelId];
    if (cached) {
      setCompSetAnchorDetail(cached);
      setAnchorError(null);
      setAnchorLoading(false);
      return;
    }

    let cancelled = false;
    setCompSetAnchorDetail(null);
    setAnchorLoading(true);
    setAnchorError(null);
    getHotelDetail(anchorHotelId)
      .then((detail) => {
        if (cancelled) return;
        setAnchorCache((current) => ({ ...current, [anchorHotelId]: detail }));
        setCompSetAnchorDetail(detail);
      })
      .catch(() => {
        if (cancelled) return;
        setCompSetAnchorDetail(null);
        setAnchorError(t("hotels.compSet.anchorLoadError"));
      })
      .finally(() => {
        if (cancelled) return;
        setAnchorLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [anchorCache, selectedCompSet, t]);

  // Load nearby suggestions when selectedCompSet changes
  useEffect(() => {
    if (!selectedCompSet) {
      setNearbySuggestions([]);
      setNearbyMessage(null);
      setNearbyLoading(false);
      return;
    }

    setNearbyLoading(true);
    setNearbyMessage(null);
    getHotelNearbySuggestions(selectedCompSet.id)
      .then((items) => {
        setNearbySuggestions(items);
      })
      .catch((error) => {
        setNearbySuggestions([]);
        if (error instanceof HotelsRequestError && error.status === 422) {
          setNearbyMessage(t("hotels.compSet.nearbyMissingCoords"));
          return;
        }
        setNearbyMessage(t("hotels.compSet.nearbyGenericError"));
      })
      .finally(() => setNearbyLoading(false));
  }, [selectedCompSet, t]);

  return {
    compSets,
    selectedCompSet,
    compSetAnchorDetail,
    anchorLoading,
    anchorError,
    nearbySuggestions,
    nearbyLoading,
    nearbyMessage,
    refreshCompSets,
    handleCreateCompSet,
    handleSelectCompSet,
    handleAddMember,
    handleDeleteMember,
  };
}
