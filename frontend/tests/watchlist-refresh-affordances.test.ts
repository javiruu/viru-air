import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const DETAIL_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const ACTIONS_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "useWatchlistActions.ts");

test("watchlist route no longer wires manual refresh actions into list or detail panels", () => {
  const pageSource = fs.readFileSync(WATCHLIST_PAGE, "utf8");

  assert.doesNotMatch(pageSource, /onRefreshWatch=/);
  assert.doesNotMatch(pageSource, /onBulkRefresh=/);
  assert.doesNotMatch(pageSource, /refreshingWatchId=/);
  assert.doesNotMatch(pageSource, /isRefreshingBulk=/);
});

test("watchlist panels show freshness context without manual refresh buttons", () => {
  const smartSource = fs.readFileSync(SMART_PANEL, "utf8");
  const detailSource = fs.readFileSync(DETAIL_PANEL, "utf8");

  assert.match(smartSource, /watchlist\.detail\.latestSnapshot/);
  assert.match(smartSource, /watchlist\.detail\.freshness/);
  assert.doesNotMatch(smartSource, /watchlist\.smartList\.refresh|watchlist\.smartList\.updating/);
  assert.doesNotMatch(detailSource, /watchlist\.detail\.actions\.refresh/);
});

test("watchlist actions hook no longer exposes single or bulk manual refresh state", () => {
  const source = fs.readFileSync(ACTIONS_FILE, "utf8");

  assert.doesNotMatch(source, /refreshingWatchId/);
  assert.doesNotMatch(source, /isRefreshingBulk/);
  assert.doesNotMatch(source, /\brefresh,\s*$/m);
  assert.doesNotMatch(source, /bulkRefresh/);
});
