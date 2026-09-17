"use client";

import { useEffect, useMemo, useState } from "react";

function userKeyFromToken(): string {
  if (typeof window === "undefined") return "anon";
  const token = window.localStorage.getItem("sb_access_token");
  if (!token) return "anon";
  const parts = token.split(".");
  if (parts.length < 2) return "anon";
  try {
    const payload = JSON.parse(atob(parts[1]));
    return typeof payload?.sub === "string" ? payload.sub : "anon";
  } catch {
    return "anon";
  }
}

export function useFtueHint(scope: "dashboard" | "quick_search" | "watchlist") {
  const storageKey = useMemo(() => {
    const userKey = userKeyFromToken();
    return `viru_ftue_seen_${scope}_${userKey}`;
  }, [scope]);

  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const seen = window.localStorage.getItem(storageKey) === "1";
    setVisible(!seen);
  }, [storageKey]);

  function dismiss(): void {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(storageKey, "1");
    }
    setVisible(false);
  }

  return { visible, dismiss };
}
