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
  // component tests run without real Supabase credentials. Warn loudly: this
  // project cannot authenticate against `mock.supabase.co` (it does not
  // resolve), so any login attempt will fail with a network error.
  console.warn(
    "[supabase] NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY are not set. " +
      "Falling back to a mock project that cannot authenticate — login will fail. " +
      "Create frontend/.env.local (see .env.example) or run a local Supabase stack " +
      "and point NEXT_PUBLIC_SUPABASE_URL at http://127.0.0.1:54321.",
  );
  return { url: "https://mock.supabase.co", key: "mock-anon-key" };
}

export function createClient() {
  const { url, key } = resolveSupabaseConfig();
  return createBrowserClient(url, key);
}
