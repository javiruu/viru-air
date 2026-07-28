import { useEffect, useMemo, useRef, useState } from "react";

import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import type {
  CommunityPriceMutationResponse,
  Watch,
} from "@/modules/watchlist/types";

type CommunityPricingStage = "flight" | "price";

type UseCommunityPricingInput = {
  readonly items: readonly Watch[];
  readonly load: () => Promise<void>;
};

export function useCommunityPricing({
  items,
  load,
}: UseCommunityPricingInput) {
  const { t } = useI18n();
  const [activeWatchId, setActiveWatchId] = useState<string | null>(null);
  const [stage, setStage] = useState<CommunityPricingStage>("flight");
  const [price, setPrice] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const hasOfferedExpiredWatch = useRef(false);

  const pendingWatches = useMemo(
    () =>
      items.filter(
        (watch) =>
          watch.community_pricing.eligible &&
          watch.community_pricing.response === null,
      ),
    [items],
  );
  const activeWatch =
    items.find((watch) => watch.id === activeWatchId) ?? null;

  useEffect(() => {
    if (
      hasOfferedExpiredWatch.current ||
      activeWatchId !== null ||
      pendingWatches.length === 0
    ) {
      return;
    }
    const firstExpired = pendingWatches.find(
      (watch) => watch.community_pricing.trigger_reason === "expired",
    );
    if (!firstExpired) return;
    hasOfferedExpiredWatch.current = true;
    setActiveWatchId(firstExpired.id);
  }, [activeWatchId, pendingWatches]);

  function prepareWatch(watch: Watch): void {
    setActiveWatchId(watch.id);
    setError("");
    if (
      watch.community_pricing.response?.flew &&
      watch.community_pricing.response.price_per_traveler !== null
    ) {
      setStage("price");
      setPrice(String(watch.community_pricing.response.price_per_traveler));
      return;
    }
    setStage("flight");
    setPrice("");
  }

  async function open(watch: Watch): Promise<void> {
    if (watch.community_pricing.eligible) {
      prepareWatch(watch);
      return;
    }

    setIsSaving(true);
    setError("");
    try {
      const response = await apiFetch<CommunityPriceMutationResponse>(
        `/watchlist/${watch.id}/mark-purchased`,
        { method: "POST" },
      );
      prepareWatch({
        ...watch,
        status: response.status,
        community_pricing: response.community_pricing,
      });
      await load();
    } catch (caught) {
      if (!(caught instanceof Error)) throw caught;
      setError(t("watchlist.communityPricing.errors.markPurchased"));
    } finally {
      setIsSaving(false);
    }
  }

  function close(): void {
    setActiveWatchId(null);
    setStage("flight");
    setPrice("");
    setError("");
  }

  function chooseFlew(): void {
    setStage("price");
    setError("");
  }

  function updatePrice(value: string): void {
    setPrice(value);
    setError("");
  }

  async function saveReport(
    flew: boolean,
    pricePerTraveler?: number,
  ): Promise<void> {
    if (!activeWatch) return;
    setIsSaving(true);
    setError("");
    try {
      await apiFetch<CommunityPriceMutationResponse>(
        `/watchlist/${activeWatch.id}/community-price`,
        {
          method: "PUT",
          body: JSON.stringify({
            flew,
            price_per_traveler: flew ? pricePerTraveler : null,
          }),
        },
      );
      await load();
      const nextPending = pendingWatches.find(
        (watch) => watch.id !== activeWatch.id,
      );
      if (nextPending) {
        prepareWatch(nextPending);
      } else {
        close();
      }
    } catch (caught) {
      if (!(caught instanceof Error)) throw caught;
      setError(t("watchlist.communityPricing.errors.save"));
    } finally {
      setIsSaving(false);
    }
  }

  async function saveNoFlight(): Promise<void> {
    await saveReport(false);
  }

  async function savePrice(): Promise<void> {
    const normalized = price.trim().replace(",", ".");
    const parsed = Number(normalized);
    if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 100000) {
      setError(t("watchlist.communityPricing.errors.invalidPrice"));
      return;
    }
    await saveReport(true, Math.round(parsed * 100) / 100);
  }

  async function deleteResponse(): Promise<void> {
    if (!activeWatch?.community_pricing.response) return;
    setIsSaving(true);
    setError("");
    try {
      await apiFetch<{ readonly status: string }>(
        `/watchlist/${activeWatch.id}/community-price`,
        { method: "DELETE" },
      );
      await load();
      setStage("flight");
      setPrice("");
    } catch (caught) {
      if (!(caught instanceof Error)) throw caught;
      setError(t("watchlist.communityPricing.errors.delete"));
    } finally {
      setIsSaving(false);
    }
  }

  return {
    activeWatch,
    pendingCount: pendingWatches.length,
    stage,
    price,
    isSaving,
    error,
    setPrice: updatePrice,
    open,
    close,
    chooseFlew,
    saveNoFlight,
    savePrice,
    deleteResponse,
  };
}
