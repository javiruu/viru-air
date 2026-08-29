import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_SRC = path.resolve(TEST_DIR, "../src");

const fallbackFiles = [
  "app/loading.tsx",
  "app/(private)/loading.tsx",
  "app/(public)/loading.tsx",
  "app/(public)/page.tsx",
  "app/(public)/login/page.tsx",
  "app/(public)/register/page.tsx",
  "app/(public)/forgot-password/page.tsx",
  "modules/shared/HelpBase.tsx",
  "modules/shared/RequireAuth.tsx",
  "modules/shared/NavigationPendingOverlay.tsx",
  "app/(private)/admin/page.tsx",
  "app/(private)/preferencias/apariencia/page.tsx",
  "app/(private)/preferencias/region/page.tsx",
];

test("key loading fallbacks use Boneyard", () => {
  for (const relativePath of fallbackFiles) {
    const absolutePath = path.join(FRONTEND_SRC, relativePath);
    const content = fs.readFileSync(absolutePath, "utf8");

    assert.doesNotMatch(
      content,
      /import\s+AirLoader\s+from/,
      `expected no AirLoader import in ${relativePath}`,
    );
    assert.match(
      content,
      /Boneyard/,
      `expected Boneyard usage in ${relativePath}`,
    );
  }
});

test("root layout does not mount the global navigation loading overlay", () => {
  const layoutPath = path.join(FRONTEND_SRC, "app/layout.tsx");
  const content = fs.readFileSync(layoutPath, "utf8");

  assert.doesNotMatch(
    content,
    /NavigationPendingOverlay/,
    "expected root layout to avoid global navigation overlay mounting",
  );
});
