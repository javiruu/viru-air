"use client";

import { useEffect, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type SupabaseAuthClient = ReturnType<typeof createClient>;

/**
 * Resolves the signed-in Supabase user id through the single session authority
 * (`supabase.auth.getUser()`), never by decoding tokens from localStorage —
 * `@supabase/ssr` stores the session in cookies, so the old `sb_access_token`
 * localStorage read always fell back to "anon".
 */
async function resolveUserKey(): Promise<string> {
  try {
    const supabase = createClient();
    const { data } = await supabase.auth.getUser();
    return data.user?.id ?? "anon";
  } catch {
    return "anon";
  }
}

/** Test seam: resolve the FTUE user key with an injected Supabase client. */
export async function resolveFtueUserKey(
  supabase: SupabaseAuthClient = createClient(),
): Promise<string> {
  try {
    const { data } = await supabase.auth.getUser();
    return data.user?.id ?? "anon";
  } catch {
    return "anon";
  }
}

export function useFtueHint(scope: "dashboard" | "quick_search" | "watchlist") {
  const [userKey, setUserKey] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void resolveUserKey().then((key) => {
      if (active) setUserKey(key);
    });
    return () => {
      active = false;
    };
  }, []);

  const storageKey = useMemo(() => {
    // Wait for the resolved user key so hints are per-user, not per-device.
    return userKey ? `viru_ftue_seen_${scope}_${userKey}` : null;
  }, [scope, userKey]);

  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    // Only reveal (or keep hidden) once the key is resolved; anonymous visitors
    // keep hints available until they sign in.
    if (!storageKey) return;
    const seen = window.localStorage.getItem(storageKey) === "1";
    setVisible(!seen);
  }, [storageKey]);

  function dismiss(): void {
    if (typeof window !== "undefined" && storageKey) {
      window.localStorage.setItem(storageKey, "1");
    }
    setVisible(false);
  }

  return { visible, dismiss };
}
