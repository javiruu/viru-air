import type { AuthOut } from "@/modules/shared/auth";
import { createClient } from "@/lib/supabase/client";

type SupabaseAuthClient = ReturnType<typeof createClient>;

export type LoginSubmitResult =
  | { kind: "success"; data: AuthOut }
  | { kind: "invalid_credentials" }
  | { kind: "server_error" }
  | { kind: "network_error" };

export async function submitLogin(
  email: string,
  password: string,
  /** Injectable for tests; defaults to the Supabase browser client. */
  supabase: SupabaseAuthClient = createClient(),
): Promise<LoginSubmitResult> {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });

  if (data?.session) {
    return { kind: "success", data: { access_token: data.session.access_token, token_type: "bearer" } };
  }

  if (error?.message?.includes("Invalid login credentials") || error?.status === 400) {
    return { kind: "invalid_credentials" };
  }

  return { kind: "server_error" };
}
