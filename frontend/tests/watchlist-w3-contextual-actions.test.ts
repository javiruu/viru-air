import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const DETAIL_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const COMPARE_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "ComparePanels.tsx");
const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");

const FORBIDDEN_WATCHLIST_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W3: bulk actions toolbar is contextual and hidden when selection is empty", () => {
  const source = fs.readFileSync(SMART_PANEL, "utf8");

  assert.match(source, /const hasSelection = selectedIds\.length > 0;/);
  assert.match(source, /\{hasSelection \? \(/);
  assert.match(source, /data-testid="watchlist-bulk-toolbar"/);
  assert.match(source, /role="toolbar"/);
  assert.match(source, /watchlist\.bulk\.toolbarAriaLabel/);
  assert.match(source, /watchlist\.bulk\.refreshSelected/);
});

test("W3: bulk toolbar exposes count and allowed actions only with explicit bulk selection", () => {
  const source = fs.readFileSync(SMART_PANEL, "utf8");

  assert.match(source, /watchlist\.bulk\.selectedCount/);
  assert.match(source, /onBulkRefresh\(selectedIds\)/);
  assert.match(source, /onBulkPause\(selectedIds\)/);
  assert.match(source, /onBulkResume\(selectedIds\)/);
  assert.match(source, /onBulkDelete\(selectedIds\)/);
});

test("W3: compare selection remains independent from bulk actions", () => {
  const smartSource = fs.readFileSync(SMART_PANEL, "utf8");
  const compareSource = fs.readFileSync(COMPARE_PANEL, "utf8");

  assert.match(smartSource, /setSelectedIds/);
  assert.match(compareSource, /name="compare_selection"/);
  assert.match(compareSource, /onToggleCompare\(option\.id\)/);
  assert.doesNotMatch(compareSource, /onBulkDelete|onBulkPause|onBulkResume/);
});

test("W3: row and detail actions stay available", () => {
  const smartSource = fs.readFileSync(SMART_PANEL, "utf8");
  const detailSource = fs.readFileSync(DETAIL_PANEL, "utf8");

  assert.match(smartSource, /onRefreshWatch\(watch\.id\)/);
  assert.match(smartSource, /onPauseWatch\(watch\.id\)/);
  assert.match(smartSource, /onResumeWatch\(watch\.id\)/);
  assert.match(smartSource, /onDeleteWatch\(watch\.id\)/);

  assert.match(detailSource, /watchlist\.detail\.actions\.refresh/);
  assert.match(detailSource, /watchlist\.detail\.actions\.pause/);
  assert.match(detailSource, /watchlist\.detail\.actions\.resume/);
});

test("W3: watchlist route source keeps forbidden EN literals blocked", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_WATCHLIST_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});
