"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { initPostHog } from "@/lib/posthog";
import { type ReactNode, useEffect, useState } from "react";

/**
 * Global QueryClient provider for Viru Tracker.
 * Defaults configured per viru-modernization-codex/06_TANSTACK_QUERY.md:
 * - staleTime: 30s by default to prevent refetch storms
 * - gcTime: 5 minutes
 * - refetchOnWindowFocus: false to avoid accidental request storms on tab switch
 * - retry: 1 in general
 */
export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            gcTime: 5 * 60_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  useEffect(() => {
    initPostHog();
  }, []);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

export default QueryProvider;
