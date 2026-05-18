import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const HISTORY_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "HistoryIntegratedPanel.tsx");

test("calendar selector trigger lives in SmartWatchListPanel", () => {
  const source = fs.readFileSync(SMART_PANEL, "utf8");
  assert.match(source, /aria-controls="watchlist-calendar-selector"/);
  assert.match(source, /watchlist\.history\.viewCalendar/);
  assert.match(source, /id="watchlist-calendar-selector"/);
});

test("calendar selector chooses single-day flight directly and opens chooser for multi-flight day", () => {
  const source = fs.readFileSync(SMART_PANEL, "utf8");
  assert.match(source, /if \(flights\.length <= 1\)/);
  assert.match(source, /onSelectWatchById\(single\.watchId\)/);
  assert.match(source, /onCalendarSelectorDayChange\(day\)/);
});

test("watchlist page wires calendar selector with watch selection callback", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  assert.match(source, /onToggleCalendarSelector=\{view\.toggleCalendarSelector\}/);
  assert.match(source, /onCalendarSelectorDayChange=\{view\.setCalendarSelectorDay\}/);
  assert.match(source, /onSelectWatchById=\{selectWatchById\}/);
});

test("history panel still renders history svg", () => {
  const source = fs.readFileSync(HISTORY_PANEL, "utf8");
  assert.match(source, /className="history-svg"/);
});
