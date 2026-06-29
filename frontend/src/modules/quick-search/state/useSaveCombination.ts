"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/modules/shared/api";
import type { SearchResult } from "@/modules/quick-search/types";

// ── Types ────────────────────────────────────────────────────────────

type SaveCombinationParams = {
  outbound: SearchResult;
  return: SearchResult;
  /** IATA origin code (outbound direction). */
  origin: string;
  /** IATA destination code (outbound direction). */
  destination: string;
  /** Shared group identifier (generated once per combination). */
  groupId: string;
};

type SaveResult = {
  watch_id?: string;
  created_or_existing?: string;
};

type SaveCombinationState = {
  status: "idle" | "saving" | "saved" | "error" | "partial";
  /** i18n key suffix for the parent to translate (e.g. "combinationError", "combinationPartial"). */
  messageKey: string | null;
};

// ── Helper ────────────────────────────────────────────────────────────

function buildWatchlistPayload(result: SearchResult, groupId: string) {
  return {
    origin_iata: result.origin,
    destination_iata: result.destination,
    travel_date: result.travel_date,
    price_total: result.price_total ?? result.price,
    currency: result.currency,
    freshness_status: result.freshness?.status ?? null,
    requires_revalidation: result.freshness?.requires_revalidation ?? result.stale_data ?? null,
    validation_status: result.freshness?.validation_status ?? null,
    group_id: groupId,
  };
}

// ── Hook ──────────────────────────────────────────────────────────────

export function useSaveCombination() {
  const router = useRouter();
  const [state, setState] = useState<SaveCombinationState>({
    status: "idle",
    messageKey: null,
  });

  const reset = useCallback(() => {
    setState({ status: "idle", messageKey: null });
  }, []);

  const saveCombination = useCallback(
    async (params: SaveCombinationParams) => {
      setState({ status: "saving", messageKey: null });

      const [outboundResult, returnResult] = await Promise.allSettled([
        apiFetch<SaveResult>("/search/save-result", {
          method: "POST",
          body: JSON.stringify(buildWatchlistPayload(params.outbound, params.groupId)),
        }),
        apiFetch<SaveResult>("/search/save-result", {
          method: "POST",
          body: JSON.stringify(buildWatchlistPayload(params.return, params.groupId)),
        }),
      ]);

      const outboundOk =
        outboundResult.status === "fulfilled" && outboundResult.value;
      const returnOk =
        returnResult.status === "fulfilled" && returnResult.value;

      if (outboundOk && returnOk) {
        setState({ status: "saved", messageKey: null });
      } else if (outboundOk || returnOk) {
        setState({
          status: "partial",
          messageKey: "combinationPartial",
        });
      } else {
        setState({
          status: "error",
          messageKey: "combinationError",
        });
      }
    },
    [],
  );

  const navigateToWatchlist = useCallback(() => {
    router.push("/watchlist");
  }, [router]);

  return {
    ...state,
    saveCombination,
    reset,
    navigateToWatchlist,
  };
}
