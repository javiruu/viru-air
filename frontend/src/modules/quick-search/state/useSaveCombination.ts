"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/modules/shared/api";
import { buildQuickSearchSaveResultPayload } from "@/modules/quick-search/api/buildSaveResultPayload";
import { buildWatchlistUrl } from "@/modules/shared/useRouteState";
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
          body: JSON.stringify(buildQuickSearchSaveResultPayload(params.outbound, { groupId: params.groupId })),
        }),
        apiFetch<SaveResult>("/search/save-result", {
          method: "POST",
          body: JSON.stringify(buildQuickSearchSaveResultPayload(params.return, { groupId: params.groupId })),
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

  const navigateToWatchlistWithContext = useCallback((
    origin?: string,
    destination?: string,
    travelDate?: string,
  ) => {
    const url = buildWatchlistUrl({
      origin: origin || "",
      destination: destination || "",
      travelDate: travelDate || "",
    });
    router.push(url);
  }, [router]);

  return {
    ...state,
    saveCombination,
    reset,
    navigateToWatchlistWithContext,
  };
}
