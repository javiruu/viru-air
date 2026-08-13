import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

test("admin users and account sessions consume paginated backend contracts", () => {
  const adminSource = readFileSync(
    join(process.cwd(), "src/app/(private)/admin/page.tsx"),
    "utf8",
  );
  const profileSource = readFileSync(
    join(process.cwd(), "src/app/(private)/cuenta/perfil/page.tsx"),
    "utf8",
  );

  assert.match(adminSource, /\/admin\/users\?limit=\$\{ADMIN_USERS_PAGE_SIZE\}&offset=\$\{offset\}/);
  assert.match(profileSource, /\/account\/sessions\?limit=\$\{ACCOUNT_SESSIONS_PAGE_SIZE\}&offset=\$\{offset\}/);
});
