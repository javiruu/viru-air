import { createBrowserClient } from "@supabase/ssr";

/**
 * Resolves the Supabase browser client configuration, failing closed in
 * production instead of silently pointing at a mock project. Silent mock
 * fallbacks hide missing configuration until runtime; the Zod env schema
 * (`@/lib/env`) validates build-time env vars, this guard covers the browser
 * client at call time.
 */
export function resolveSupabaseConfig(): { url: string; key: string } {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (url && key) {
    return { url, key };
  }

  if (process.env.NODE_ENV === "production") {
    throw new Error(
      "Supabase client is not configured: NEXT_PUBLIC_SUPABASE_URL and " +
        "NEXT_PUBLIC_SUPABASE_ANON_KEY are required in production.",
    );
  }

  // Local development / tests: keep a mock project so the Orval mutator and
  // component tests run without real Supabase credentials.
  return { url: "https://mock.supabase.co", key: "mock-anon-key" };
}

export function createClient() {
  const { url, key } = resolveSupabaseConfig();
  return createBrowserClient(url, key);
}
