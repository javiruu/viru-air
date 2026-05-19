import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const QUICK_SEARCH_VIEW = path.join(process.cwd(), "src", "modules", "quick-search", "QuickSearchView.tsx");

test("quick-search requests monthly calendar hints from backend", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /\/search\/quick\/calendar-hints/);
  assert.match(source, /setCalendarHintsByMonth/);
  assert.match(source, /calendarVisibleMonth/);
});

test("outbound date picker is wired with hints props and visible-month callback", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /name="travel_date"/);
  assert.match(source, /dayHintsByIso=\{calendarHintsByMonth\[calendarVisibleMonth\] \|\| \{\}\}/);
  assert.match(source, /hintsLoading=\{calendarHintsLoadingMonth === calendarVisibleMonth\}/);
  assert.match(source, /onVisibleMonthChange=\{setCalendarVisibleMonth\}/);
});
