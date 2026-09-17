import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";

import { useI18n } from "@/i18n";
import {
  markWatchPurchasedApiV1WatchlistWatchIdMarkPurchasedPost,
  upsertCommunityPriceApiV1WatchlistWatchIdCommunityPricePut,
  deleteCommunityPriceApiV1WatchlistWatchIdCommunityPriceDelete
} from "@/api/generated/watchlist/watchlist";
import type { CommunityPriceMutationResponse, Watch } from "@/modules/watchlist/types";

type CommunityPricingStage = "overview" | "flight" | "price" | "thanks";

type UseCommunityPricingInput = {
  readonly load: () => Promise<void>;
};

export function useCommunityPricing({ load }: UseCommunityPricingInput) {
  const { t } = useI18n();
  const [activeWatch, setActiveWatch] = useState<Watch | null>(null);
  const [stage, setStage] = useState<CommunityPricingStage>("overview");
  const [price, setPrice] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const returnFocusRef = useRef<HTMLElement | null>(null);

  function prepareWatch(watch: Watch): void {
    setActiveWatch(watch);
    setError("");
    setStage("overview");
    if (
      watch.community_pricing.response?.flew &&
      watch.community_pricing.response.price_per_traveler !== null
    ) {
      setPrice(String(watch.community_pricing.response.price_per_traveler));
      return;
    }
    setPrice("");
  }

  function open(watch: Watch, returnFocusTarget: HTMLElement): void {
    returnFocusRef.current = returnFocusTarget;
    prepareWatch(watch);
  }

  async function markPurchased(): Promise<void> {
    if (!activeWatch || activeWatch.community_pricing.eligible) return;
    setIsSaving(true);
    setError("");
    try {
      const response = await markWatchPurchasedApiV1WatchlistWatchIdMarkPurchasedPost(activeWatch.id);
      const data = response as unknown as CommunityPriceMutationResponse;
      setActiveWatch({
        ...activeWatch,
        status: data.status,
        community_pricing: data.community_pricing,
      });
      setStage("flight");
      await load().catch(() => undefined);
    } catch (caught) {
      if (!(caught instanceof Error)) throw caught;
      setError(t("watchlist.communityPricing.errors.markPurchased"));
    } finally {
      setIsSaving(false);
    }
  }

  function close(): void {
    const returnFocusTarget = returnFocusRef.current;
    flushSync(() => {
      setActiveWatch(null);
      setStage("overview");
      setPrice("");
      setError("");
    });
    returnFocusTarget?.focus();
    returnFocusRef.current = null;
  }

  function beginContribution(): void {
    setStage("flight");
    setError("");
  }

  function backToOverview(): void {
    setStage("overview");
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

  async function saveReport(flew: boolean, pricePerTraveler?: number): Promise<void> {
    if (!activeWatch) return;
    setIsSaving(true);
    setError("");
    try {
      const response = await upsertCommunityPriceApiV1WatchlistWatchIdCommunityPricePut(activeWatch.id, {
        flew,
        price_per_traveler: flew ? pricePerTraveler : null,
      });
      const data = response as unknown as CommunityPriceMutationResponse;
      setActiveWatch({
        ...activeWatch,
        status: data.status,
        community_pricing: data.community_pricing,
      });
      await load().catch(() => undefined);
      // After a successful price contribution, show a warm thank-you
      if (flew && pricePerTraveler !== undefined) {
        setStage("thanks");
      } else {
        setStage("overview");
      }
    } catch (caught) {
      if (!(caught instanceof Error)) throw caught;
      setError(t("watchlist.communityPricing.errors.save"));
    } finally {
      setIsSaving(false);
    }
  }

  // Auto-transition from "thanks" back to "overview" after a warm pause,
  // then refresh community data so the overview shows updated values.
  useEffect(() => {
    if (stage !== "thanks") return;
    const timer = setTimeout(() => {
      setStage("overview");
      void load().catch(() => undefined);
    }, 2500);
    return () => clearTimeout(timer);
  }, [load, stage]);

  async function dismissThanks(): Promise<void> {
    setStage("overview");
    await load().catch(() => undefined);
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
      await deleteCommunityPriceApiV1WatchlistWatchIdCommunityPriceDelete(activeWatch.id);
      await load().catch(() => undefined);
      close();
    } catch (caught) {
      if (!(caught instanceof Error)) throw caught;
      setError(t("watchlist.communityPricing.errors.delete"));
    } finally {
      setIsSaving(false);
    }
  }

  return {
    activeWatch,
    stage,
    price,
    isSaving,
    error,
    setPrice: updatePrice,
    open,
    close,
    markPurchased,
    beginContribution,
    backToOverview,
    chooseFlew,
    saveNoFlight,
    savePrice,
    deleteResponse,
    dismissThanks,
  };
}
