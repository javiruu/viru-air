import assert from "node:assert/strict";
import test from "node:test";

import { resolveFtueUserKey } from "@/lib/ftue";
import type { createClient as createSupabaseClient } from "@/lib/supabase/client";

type SupabaseAuthClient = ReturnType<typeof createSupabaseClient>;

function stubClient(
  getUser: () => Promise<{
    data: { user: { id: string } | null };
    error: { message: string; status?: number } | null;
  }>,
): SupabaseAuthClient {
  return { auth: { getUser } } as unknown as SupabaseAuthClient;
}

test("ftue user key comes from the Supabase session, falling back to anon", async () => {
  const signedIn = await resolveFtueUserKey(
    stubClient(async () => ({
      data: { user: { id: "user-42" } },
      error: null,
    })),
  );
  assert.equal(signedIn, "user-42");

  const signedOut = await resolveFtueUserKey(
    stubClient(async () => ({ data: { user: null }, error: null })),
  );
  assert.equal(signedOut, "anon");

  const failing = await resolveFtueUserKey(
    stubClient(async () => {
      throw new Error("offline");
    }),
  );
  assert.equal(failing, "anon");
});
