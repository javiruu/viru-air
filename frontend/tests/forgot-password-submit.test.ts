import assert from "node:assert/strict";
import test from "node:test";

import { submitForgotPassword } from "@/modules/shared/forgot-password";
import type { createClient as createSupabaseClient } from "@/lib/supabase/client";

type SupabaseAuthClient = ReturnType<typeof createSupabaseClient>;

function stubClient(
  resetPasswordForEmail: (
    email: string,
  ) => Promise<{ data: Record<string, unknown>; error: { message: string; status?: number } | null }>,
): SupabaseAuthClient {
  return { auth: { resetPasswordForEmail } } as unknown as SupabaseAuthClient;
}

test("forgot-password submit resolves success on generic backend response", async () => {
  const result = await submitForgotPassword(
    "qa@viru.dev",
    stubClient(async () => ({ data: {}, error: null })),
  );
  assert.equal(result, "success");
});

test("forgot-password submit resolves generic error on backend failure", async () => {
  const result = await submitForgotPassword(
    "qa@viru.dev",
    stubClient(async () => ({ data: {}, error: { message: "request_failed", status: 500 } })),
  );
  assert.equal(result, "error");
});
