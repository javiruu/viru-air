import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

test("admin users and account sessions consume paginated backend contracts", () => {
  const adminSource = readFileSync(join(process.cwd(), "src/app/(private)/admin/page.tsx"), "utf8");
  const profileSource = readFileSync(
    join(process.cwd(), "src/app/(private)/cuenta/perfil/page.tsx"),
    "utf8",
  );

  // Pagination now travels through the generated Orval clients' typed params.
  assert.match(adminSource, /listUsersApiV1AdminUsersGet\(\{\s*limit: ADMIN_USERS_PAGE_SIZE,\s*offset,/);
  assert.match(profileSource, /getSessionsApiV1AccountSessionsGet\(\{\s*limit: ACCOUNT_SESSIONS_PAGE_SIZE,\s*offset,/);
});
