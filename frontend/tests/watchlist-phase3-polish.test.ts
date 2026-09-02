import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { readStylesheetTree } from "./helpers/read-stylesheet-tree";

const DETAIL_PANEL = path.join(
  process.cwd(),
  "src",
  "modules",
  "watchlist",
  "components",
  "WatchDetailPanel.tsx",
);
const SCREENS = path.join(process.cwd(), "src", "styles", "screens.css");

test("Phase 3.1: additional fare controls use accessible progressive disclosure", () => {
  const detail = fs.readFileSync(DETAIL_PANEL, "utf8");

  assert.match(detail, /<details className="watch-detail-secondary">/);
  assert.match(detail, /<summary className="watch-detail-secondary-summary">/);
  assert.match(detail, /<FareComparisonPanel/);
  assert.match(detail, /watch-detail-secondary-content/);
});

test("Phase 3.4: selected detail transition respects reduced motion", () => {
  const detail = fs.readFileSync(DETAIL_PANEL, "utf8");
  const screens = readStylesheetTree(SCREENS);

  assert.match(detail, /watch-detail-selection-transition/);
  assert.match(screens, /@media \(prefers-reduced-motion: reduce\)[\s\S]*\.watch-detail-selection-transition/);
});
