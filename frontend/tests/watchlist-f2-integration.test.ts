import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const ACTIONS_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "useWatchlistActions.ts");
const DETAIL_PANEL_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");

test("watchlist selected route loads detail and prices summary endpoints", () => {
  const source = fs.readFileSync(ACTIONS_FILE, "utf8");
  assert.match(source, /apiFetch<WatchDetail>\(`\/watchlist\/\$\{selectedWatchId\}`\)/);
  assert.match(source, /apiFetch<PriceSummary>\(`\/prices\/summary\?watch_id=\$\{selectedWatchId\}`\)/);
});

test("watchlist bulk refresh uses refresh-bulk endpoint", () => {
  const source = fs.readFileSync(ACTIONS_FILE, "utf8");
  assert.match(source, /"\/watchlist\/refresh-bulk"/);
  assert.doesNotMatch(source, /Promise\.allSettled\(\s*targets\.map\(\(item\) => apiFetch<\{ status: string \}>\(`\/watchlist\/\$\{item\.id\}\/refresh-now`/);
});

test("watch detail panel contains required empty state keys", () => {
  const source = fs.readFileSync(DETAIL_PANEL_FILE, "utf8");
  assert.match(source, /watchlist\.detail\.empty/);
  assert.match(source, /watchlist\.summary\.empty/);
});
