import type { AuthOut } from "@/modules/shared/auth";
import { createClient } from "@/lib/supabase/client";

type SupabaseAuthClient = ReturnType<typeof createClient>;

export type LoginSubmitResult =
  | { kind: "success"; data: AuthOut }
  | { kind: "invalid_credentials" }
  | { kind: "server_error" }
  | { kind: "network_error" };

/** Maps a Supabase Auth API error to a stable user-facing result kind. */
function mapSupabaseError(error: { message?: string; status?: number } | null): LoginSubmitResult {
  if (error?.status === 400 || error?.status === 422 || error?.message?.includes("Invalid login credentials")) {
    return { kind: "invalid_credentials" };
  }
  return { kind: "server_error" };
}

export async function submitLogin(
  email: string,
  password: string,
  /** Injectable for tests; defaults to the Supabase browser client. */
  supabase: SupabaseAuthClient = createClient(),
): Promise<LoginSubmitResult> {
  let response: Awaited<ReturnType<SupabaseAuthClient["auth"]["signInWithPassword"]>>;
  try {
    response = await supabase.auth.signInWithPassword({ email, password });
  } catch {
    // signInWithPassword rejects (instead of returning `error`) when the auth
    // server itself is unreachable: DNS failure, offline, misconfigured URL.
    return { kind: "network_error" };
  }

  const { data, error } = response;
  if (data?.session) {
    return {
      kind: "success",
      data: {
        access_token: data.session.access_token,
        // The refresh token is required by `supabase.auth.setSession` on the
        // login page; dropping it silently broke session persistence.
        refresh_token: data.session.refresh_token,
        token_type: "bearer",
      },
    };
  }

  return mapSupabaseError(error);
}
