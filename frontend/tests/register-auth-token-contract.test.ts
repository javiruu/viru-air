import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

test("registration persists the Supabase session", () => {
  const source = readFileSync(join(process.cwd(), "src/app/(public)/register/page.tsx"), "utf8");

  // After the Supabase cutover the registration delegates to supabase.auth.signUp
  // (via submitRegister) and hands the returned tokens to the Supabase SSR
  // session instead of a legacy localStorage token store or the decommissioned
  // /auth/register backend endpoint.
  assert.match(source, /supabase\.auth\.setSession\(\{ access_token: data\.access_token/);
  assert.match(source, /submitRegister/);
  assert.doesNotMatch(source, /registerApiV1AuthRegisterPost/);
});
