import type { AuthOut } from "@/modules/shared/auth";
import { createClient } from "@/lib/supabase/client";

type SupabaseAuthClient = ReturnType<typeof createClient>;

export type RegisterSubmitResult =
  | { kind: "success"; data: AuthOut }
  | { kind: "email_in_use" }
  | { kind: "invalid_email" }
  | { kind: "weak_password" }
  | { client_error: string; kind: "client_error" }
  | { kind: "server_error" }
  | { kind: "network_error" };

/** Maps a Supabase Auth API error to a stable user-facing result kind. */
function mapSupabaseRegisterError(error: { message?: string; status?: number } | null): RegisterSubmitResult {
  const message = error?.message ?? "";
  if (/already registered|already exists|already in use|been taken/i.test(message)) {
    return { kind: "email_in_use" };
  }
  if (/password.*least|weak password|easily determined/i.test(message)) {
    return { kind: "weak_password" };
  }
  if (error?.status === 422 || (/invalid/i.test(message) && /email/i.test(message))) {
    return { kind: "invalid_email" };
  }
  if (error?.status && error.status >= 500) {
    return { kind: "server_error" };
  }
  if (error?.status === 400 || error?.status === 422) {
    return { client_error: message, kind: "client_error" };
  }
  return { kind: "server_error" };
}

export async function submitRegister(
  email: string,
  password: string,
  /** Injectable for tests; defaults to the Supabase browser client. */
  supabase: SupabaseAuthClient = createClient(),
): Promise<RegisterSubmitResult> {
  let response: Awaited<ReturnType<SupabaseAuthClient["auth"]["signUp"]>>;
  try {
    response = await supabase.auth.signUp({ email, password });
  } catch {
    // signUp rejects (instead of returning `error`) when the auth server itself
    // is unreachable: DNS failure, offline, misconfigured URL.
    return { kind: "network_error" };
  }

  const { data, error } = response;
  const session = data?.session;
  if (session?.access_token) {
    return {
      kind: "success",
      data: {
        access_token: session.access_token,
        refresh_token: session.refresh_token,
        token_type: "bearer",
      },
    };
  }

  // Some Supabase configurations require email confirmation: signUp succeeds
  // without an immediate session. Surface that as a success path the page can
  // message clearly instead of a raw 404-style failure.
  if (!error && data?.user) {
    return {
      kind: "success",
      data: {
        access_token: "",
        refresh_token: "",
        token_type: "bearer",
      },
    };
  }

  return mapSupabaseRegisterError(error);
}
