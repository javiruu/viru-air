"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchDoorToDoorHistory } from "@/modules/door-to-door/api";
import type { DoorToDoorHistoryItem } from "@/modules/door-to-door/types";

export function useDoorToDoorHistory(selectedWatchId: string, triggerVersion: number) {
  const [history, setHistory] = useState<DoorToDoorHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const requestIdRef = useRef(0);

  const refreshHistory = useCallback(async () => {
    if (!selectedWatchId) {
      setHistory([]);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    try {
      const items = await fetchDoorToDoorHistory(selectedWatchId);
      if (requestId !== requestIdRef.current) return;
      setHistory(items);
    } catch {
      if (requestId !== requestIdRef.current) return;
      setHistory([]);
    }
  }, [selectedWatchId]);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory, triggerVersion]);

  useEffect(() => {
    setShowHistory(false);
  }, [selectedWatchId]);

  return { history, showHistory, setShowHistory, refreshHistory };
}
