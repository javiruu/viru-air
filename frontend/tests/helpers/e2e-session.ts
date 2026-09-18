import type { BrowserContext } from "playwright";

/**
 * Shared E2E session seeding helper.
 *
 * Since the Supabase Auth cutover the browser session lives in the
 * `sb-{projectRef}-auth-token` localStorage bootstrap entry (synced to cookies
 * by @supabase/ssr), not in the retired `viru_token` key. This helper writes a
 * structurally valid session so the app boots authenticated in E2E runs
 * against a local stack.
 */
export function supabaseStorageKey(): string {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://mock.supabase.co";
  const projectRef = new URL(supabaseUrl).hostname.split(".")[0];
  return `sb-${projectRef}-auth-token`;
}

export function buildE2eSession(accessToken: string, userId: string, email: string): object {
  const issuedAt = Math.floor(Date.now() / 1000);
  return {
    access_token: accessToken,
    refresh_token: `refresh-${userId}`,
    token_type: "bearer",
    expires_in: 3600,
    expires_at: issuedAt + 3600,
    user: {
      id: userId,
      email,
      aud: "authenticated",
      role: "authenticated",
      app_metadata: {},
      user_metadata: {},
      created_at: new Date(issuedAt * 1000).toISOString(),
    },
  };
}

export async function seedSupabaseSession(
  context: BrowserContext,
  accessToken: string,
): Promise<void> {
  const userId = `e2e-${Math.random().toString(36).slice(2, 12)}`;
  const email = `${userId}@example.com`;
  const storageKey = supabaseStorageKey();
  const session = buildE2eSession(accessToken, userId, email);

  await context.addInitScript(
    ({ key, value }) => {
      window.localStorage.setItem(key, JSON.stringify({ currentSession: value, ...value }));
    },
    { key: storageKey, value: session },
  );
}
