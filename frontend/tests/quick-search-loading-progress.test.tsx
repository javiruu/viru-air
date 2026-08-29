import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const COMPONENT_PATH = path.resolve(TEST_DIR, "../src/modules/quick-search/components/QuickSearchLoadingProgress.tsx");

test("QuickSearchLoadingProgress retains its progress flow and delegates capture cards to Boneyard", () => {
  const source = fs.readFileSync(COMPONENT_PATH, "utf8");

  assert.match(source, /if \(!props\.show && !props\.loadingVisualHold\) return null;/);
  assert.match(source, /props\.progressPercent/);
  assert.match(source, /props\.loadingSubchecks/);
  assert.match(source, /BoneyardLoad name="quick-search-progress-load"/);
  assert.match(source, /qs-loading-card/);
});
