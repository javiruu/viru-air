import assert from "node:assert/strict";
import test from "node:test";

import { submitRegister } from "@/modules/shared/register-submit";
import type { createClient as createSupabaseClient } from "@/lib/supabase/client";

type SupabaseAuthClient = ReturnType<typeof createSupabaseClient>;

/**
 * Since the Supabase Auth cutover, submitRegister delegates to
 * supabase.auth.signUp. These tests inject a Supabase client stub to exercise
 * the result mapping without touching the network.
 */
const EMAIL_IN_USE = { message: "User already registered", status: 422 };
const WEAK_PASSWORD = { message: "Password should be at least 6 characters", status: 400 };
const INVALID_EMAIL = { message: "Unable to validate email address: invalid format", status: 422 };
const SERVER_ERROR = { message: "Service unavailable", status: 503 };

function stubClient(
  signUp: (
    creds: { email: string; password: string },
  ) => Promise<{ data: Record<string, unknown>; error: { message: string; status?: number } | null }>,
): SupabaseAuthClient {
  return { auth: { signUp } } as unknown as SupabaseAuthClient;
}

test("submitRegister maps Supabase duplicate email to email_in_use", async () => {
  const result = await submitRegister(
    "qa@viru.dev",
    "goodpass123",
    stubClient(async () => ({ data: {}, error: EMAIL_IN_USE })),
  );
  assert.deepEqual(result, { kind: "email_in_use" });
});

test("submitRegister maps Supabase weak password to weak_password", async () => {
  const result = await submitRegister(
    "qa@viru.dev",
    "123",
    stubClient(async () => ({ data: {}, error: WEAK_PASSWORD })),
  );
  assert.deepEqual(result, { kind: "weak_password" });
});

test("submitRegister maps Supabase invalid email to invalid_email", async () => {
  const result = await submitRegister(
    "not-an-email",
    "goodpass123",
    stubClient(async () => ({ data: {}, error: INVALID_EMAIL })),
  );
  assert.deepEqual(result, { kind: "invalid_email" });
});

test("submitRegister maps Supabase server failures to server_error", async () => {
  const result = await submitRegister(
    "qa@viru.dev",
    "goodpass123",
    stubClient(async () => ({ data: {}, error: SERVER_ERROR })),
  );
  assert.deepEqual(result, { kind: "server_error" });
});

test("submitRegister maps an unreachable auth server to network_error", async () => {
  const result = await submitRegister("qa@viru.dev", "goodpass123", stubClient(async () => {
    throw new TypeError("Failed to fetch");
  }));
  assert.deepEqual(result, { kind: "network_error" });
});

test("submitRegister returns the access token on a successful session", async () => {
  const result = await submitRegister(
    "qa@viru.dev",
    "goodpass123",
    stubClient(async () => ({
      data: { session: { access_token: "token-abc", refresh_token: "refresh-abc" }, user: { id: "u1" } },
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

test("submitRegister succeeds without session when email confirmation is required", async () => {
  const result = await submitRegister(
    "qa@viru.dev",
    "goodpass123",
    stubClient(async () => ({
      data: { session: null, user: { id: "u1" } },
      error: null,
    })),
  );
  assert.equal(result.kind, "success");
  if (result.kind === "success") {
    assert.equal(result.data.access_token, "");
  }
});
