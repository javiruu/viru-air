import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const COMPARE_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "ComparePanels.tsx");
const VIEW_STATE = path.join(process.cwd(), "src", "modules", "watchlist", "useWatchlistViewState.ts");
const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");

const FORBIDDEN_EN_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W8: compare empty/one/mixed states and compare data source are explicit", () => {
  const source = fs.readFileSync(COMPARE_PANEL, "utf8");

  assert.match(source, /selectedCount === 0/);
  assert.match(source, /watchlist\.compare\.emptySelectionMessage/);
  assert.match(source, /selectedCount === 1/);
  assert.match(source, /watchlist\.compare\.oneSelectionMessage/);
  assert.match(source, /selectedCount > 4/);
  assert.match(source, /watchlist\.compare\.maxSelectionMessage/);
  assert.match(source, /currency_mode === "mixed"/);
  assert.match(source, /watchlist\.compare\.mixedCurrencyWarning/);
  assert.match(source, /apiFetch<PriceCompareResponse>\(`\/prices\/compare\?watch_ids=\$\{compareQuery\}`\)/);
});

test("W8: badges are derived from compare response, not local history rows", () => {
  const source = fs.readFileSync(COMPARE_PANEL, "utf8");

  assert.match(source, /compareBadgesFromResponse\.bestPriceId/);
  assert.match(source, /watchlist\.compare\.bestPriceBadge/);
  assert.match(source, /compareBadgesFromResponse\.stableId/);
  assert.match(source, /watchlist\.compare\.mostStableBadge/);
  assert.match(source, /compareBadgesFromResponse\.freshestId/);
  assert.match(source, /watchlist\.compare\.freshestBadge/);
  assert.match(source, /compareResponse\?\.points/);
  assert.doesNotMatch(source, /historyRows/);
});

test("W8: compare selection guard keeps hard limit at 4 routes", () => {
  const source = fs.readFileSync(VIEW_STATE, "utf8");

  assert.match(source, /if \(prev\.length >= 4\)/);
  assert.match(source, /watchlist\.compare\.maxSelectionMessage/);
});

test("W8: compare selection remains isolated from bulk destructive toolbar", () => {
  const compareSource = fs.readFileSync(COMPARE_PANEL, "utf8");
  const smartSource = fs.readFileSync(SMART_PANEL, "utf8");

  assert.match(compareSource, /name="compare_selection"/);
  assert.match(compareSource, /onToggleCompare\(option\.id\)/);
  assert.doesNotMatch(compareSource, /onBulkDelete|onBulkPause|onBulkResume|onBulkRefresh/);
  assert.match(smartSource, /data-testid="watchlist-bulk-toolbar"/);
});

test("W8: watchlist route source still blocks forbidden EN literals", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_EN_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});
