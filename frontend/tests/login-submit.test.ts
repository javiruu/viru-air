import assert from "node:assert/strict";
import test from "node:test";

import { submitLogin } from "@/modules/shared/login-submit";
import type { createClient as createSupabaseClient } from "@/lib/supabase/client";

type SupabaseAuthClient = ReturnType<typeof createSupabaseClient>;

/**
 * Since the Supabase Auth cutover, submitLogin delegates to
 * supabase.auth.signInWithPassword. These tests inject a Supabase client stub
 * to exercise the result mapping without touching the network.
 */
const INVALID_CREDENTIALS_ERROR = { message: "Invalid login credentials", status: 400 };
const SERVER_ERROR = { message: "Service unavailable", status: 503 };

function stubClient(
  signInWithPassword: (
    creds: { email: string; password: string },
  ) => Promise<{ data: Record<string, unknown>; error: { message: string; status?: number } | null }>,
): SupabaseAuthClient {
  return { auth: { signInWithPassword } } as unknown as SupabaseAuthClient;
}

test("submitLogin maps Supabase invalid credentials to invalid_credentials", async () => {
  const result = await submitLogin(
    "qa@viru.dev",
    "badpass123",
    stubClient(async () => ({ data: {}, error: INVALID_CREDENTIALS_ERROR })),
  );
  assert.deepEqual(result, { kind: "invalid_credentials" });
});

test("submitLogin maps Supabase server failures to server_error", async () => {
  const result = await submitLogin(
    "qa@viru.dev",
    "goodpass123",
    stubClient(async () => ({ data: {}, error: SERVER_ERROR })),
  );
  assert.deepEqual(result, { kind: "server_error" });
});

test("submitLogin maps an unreachable auth server to network_error", async () => {
  const result = await submitLogin("qa@viru.dev", "goodpass123", stubClient(async () => {
    throw new TypeError("Failed to fetch");
  }));
  assert.deepEqual(result, { kind: "network_error" });
});
;

test("submitLogin returns the access token on a successful session", async () => {
  const result = await submitLogin(
    "qa@viru.dev",
    "goodpass123",
    stubClient(async () => ({
      data: { session: { access_token: "token-abc", refresh_token: "refresh-abc" } },
      error: null,
    })),
  );
  assert.deepEqual(result, {
    kind: "success",
    data: {
      access_token: "token-abc",
      refresh_token: "refresh-abc",
      token_type: "bearer",
    },
  });
});
