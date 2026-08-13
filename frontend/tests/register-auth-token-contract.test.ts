import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

test("registration persists the refresh token returned by the API", () => {
  const source = readFileSync(
    join(process.cwd(), "src/app/(public)/register/page.tsx"),
    "utf8",
  );

  assert.match(source, /saveAuthTokens\(data\)/);
  assert.doesNotMatch(source, /saveToken\(data\.access_token\)/);
});
