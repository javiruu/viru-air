import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const WATCH_ROW = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchRow.tsx");
const DETAIL_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const COMPARE_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "ComparePanels.tsx");
const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");

const FORBIDDEN_WATCHLIST_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W3: ticket selection is integrated into the row without a bulk toolbar", () => {
  const smartSource = fs.readFileSync(SMART_PANEL, "utf8");
  const rowSource = fs.readFileSync(WATCH_ROW, "utf8");

  assert.match(smartSource, /selectedWatchId === watch\.id/);
  assert.match(smartSource, /onSelect=\{onSelectWatch\}/);
  assert.match(rowSource, /onClick=\{\(\) => onSelect\(watch\)\}/);
  assert.match(rowSource, /aria-pressed=\{isSelected\}/);
  assert.doesNotMatch(smartSource, /data-testid="watchlist-bulk-toolbar"/);
});

test("W3: ticket rows retain their individual lifecycle actions", () => {
  const source = fs.readFileSync(SMART_PANEL, "utf8");

  assert.match(source, /onPause=\{onPauseWatch\}/);
  assert.match(source, /onResume=\{onResumeWatch\}/);
  assert.match(source, /onDelete=\{onDeleteWatch\}/);
  assert.doesNotMatch(source, /onBulkPause|onBulkResume|onBulkDelete/);
});

test("W3: compare selection remains independent from ticket selection", () => {
  const smartSource = fs.readFileSync(SMART_PANEL, "utf8");
  const compareSource = fs.readFileSync(COMPARE_PANEL, "utf8");

  assert.match(smartSource, /selectedWatchId/);
  assert.match(compareSource, /name="compare_selection"/);
  assert.match(compareSource, /onToggleCompare\(option\.id\)/);
  assert.doesNotMatch(compareSource, /onBulkDelete|onBulkPause|onBulkResume|onBulkRefresh/);
});

test("W3: row and detail actions keep lifecycle controls without manual refresh affordances", () => {
  const rowSource = fs.readFileSync(WATCH_ROW, "utf8");
  const detailSource = fs.readFileSync(DETAIL_PANEL, "utf8");

  assert.match(rowSource, /onPause\(watch\.id\)/);
  assert.match(rowSource, /onResume\(watch\.id\)/);
  assert.match(rowSource, /onDelete\(watch\.id\)/);
  assert.doesNotMatch(rowSource, /onRefresh\(watch\.id\)/);

  assert.match(detailSource, /watchlist\.detail\.actions\.pause/);
  assert.match(detailSource, /watchlist\.detail\.actions\.resume/);
  assert.doesNotMatch(detailSource, /watchlist\.detail\.actions\.refresh/);
});

test("W3: purchased tickets use Comprado in the action area and retain delete", () => {
  const rowSource = fs.readFileSync(WATCH_ROW, "utf8");

  assert.match(rowSource, /watch\.status === "purchased"/);
  assert.match(rowSource, /watch-ticket-purchased-action/);
  assert.match(rowSource, /onDelete\(watch\.id\)/);
});

test("W3: watchlist route source keeps forbidden EN literals blocked", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_WATCHLIST_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});
