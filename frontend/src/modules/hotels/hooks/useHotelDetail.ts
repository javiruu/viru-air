"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { getHotelDetail, getHotelParity, getHotelRates } from "../api";
import type { HotelDetailOut, HotelParityOut, HotelRateOut } from "../types";
import { resolveHotelMessage } from "./useHotelSearch";

export function useHotelDetail(selectedHotelId: string | null, intentId?: string | null) {
  const { t } = useI18n();
  const [rates, setRates] = useState<HotelRateOut[]>([]);
  const [hotelDetail, setHotelDetail] = useState<HotelDetailOut | null>(null);
  const [loadingRates, setLoadingRates] = useState(false);
  const [paritySignals, setParitySignals] = useState<HotelParityOut[]>([]);
  const [parityLoading, setParityLoading] = useState(false);
  const [parityError, setParityError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedHotelId) {
      setHotelDetail(null);
      setRates([]);
      setParitySignals([]);
      setParityError(null);
      setLoadingRates(false);
      setParityLoading(false);
      return;
    }
    let cancelled = false;
    const controller = new AbortController();
    setLoadingRates(true);
    setParityLoading(true);
    setParityError(null);
    Promise.allSettled([
      getHotelDetail(selectedHotelId, controller.signal, intentId ?? undefined),
      getHotelRates(selectedHotelId, undefined, controller.signal, intentId ?? undefined),
      getHotelParity(selectedHotelId, controller.signal, intentId ?? undefined),
    ])
      .then(([detailResult, ratesResult, parityResult]) => {
        if (cancelled) return;
        setHotelDetail(detailResult.status === "fulfilled" ? detailResult.value : null);
        setRates(ratesResult.status === "fulfilled" ? ratesResult.value : []);
        if (parityResult.status === "fulfilled") {
          setParitySignals(parityResult.value);
          setParityError(null);
        } else {
          setParitySignals([]);
          setParityError(resolveHotelMessage(parityResult.reason, t));
        }
      })
      .finally(() => {
        if (cancelled) return;
        setLoadingRates(false);
        setParityLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [selectedHotelId, intentId, t]);

  return {
    rates,
    hotelDetail,
    loadingRates,
    paritySignals,
    parityLoading,
    parityError,
  };
}
