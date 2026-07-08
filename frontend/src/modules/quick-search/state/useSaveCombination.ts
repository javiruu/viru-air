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
  messageKey: string | null;
  outboundWatchId: string;
  returnWatchId: string;
  groupId: string;
};

// ── Hook ──────────────────────────────────────────────────────────────

export function useSaveCombination() {
  const router = useRouter();
  const [state, setState] = useState<SaveCombinationState>({
    status: "idle",
    messageKey: null,
    outboundWatchId: "",
    returnWatchId: "",
    groupId: "",
  });

  const reset = useCallback(() => {
    setState({ status: "idle", messageKey: null, outboundWatchId: "", returnWatchId: "", groupId: "" });
  }, []);

  const saveCombination = useCallback(
    async (params: SaveCombinationParams) => {
      setState({ status: "saving", messageKey: null, outboundWatchId: "", returnWatchId: "", groupId: params.groupId });

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
      const outboundWatchId = outboundOk ? outboundResult.value.watch_id ?? "" : "";
      const returnWatchId = returnOk ? returnResult.value.watch_id ?? "" : "";

      if (outboundOk && returnOk) {
        setState({ status: "saved", messageKey: null, outboundWatchId, returnWatchId, groupId: params.groupId });
      } else if (outboundOk || returnOk) {
        setState({
          status: "partial",
          messageKey: "combinationPartial",
          outboundWatchId,
          returnWatchId,
          groupId: params.groupId,
        });
      } else {
        setState({
          status: "error",
          messageKey: "combinationError",
          outboundWatchId: "",
          returnWatchId: "",
          groupId: params.groupId,
        });
      }
    },
    [],
  );

  const navigateToWatchlistWithContext = useCallback((
    origin?: string,
    destination?: string,
    travelDate?: string,
    watchId?: string,
  ) => {
    const url = buildWatchlistUrl({
      origin: origin || "",
      destination: destination || "",
      travelDate: travelDate || "",
      watchId: watchId || "",
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
