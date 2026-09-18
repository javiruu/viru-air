import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

test("registration persists the Supabase session returned by the API", () => {
  const source = readFileSync(join(process.cwd(), "src/app/(public)/register/page.tsx"), "utf8");

  // After the Supabase cutover the registration hands the returned tokens to the
  // Supabase SSR session instead of a legacy localStorage token store.
  assert.match(source, /supabase\.auth\.setSession\(\{ access_token: data\.access_token/);
  assert.match(source, /registerApiV1AuthRegisterPost/);
});
