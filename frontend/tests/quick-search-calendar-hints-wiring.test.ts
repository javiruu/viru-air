import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const QUICK_SEARCH_VIEW = path.join(process.cwd(), "src", "modules", "quick-search", "QuickSearchView.tsx");

test("quick-search requests monthly calendar hints from backend", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /\/search\/quick\/calendar-hints/);
  assert.match(source, /setCalendarHintsByKey/);
  assert.match(source, /calendarHintsRequestKey/);
  assert.match(source, /aggregation_mode:\s*calendarHintAggregationMode/);
  assert.match(source, /bucket_mode:\s*calendarHintBucketMode/);
  assert.match(source, /guideline_thresholds:\s*calendarHintBucketMode === "guidelines" \? calendarHintGuidelineThresholds : undefined/);
  assert.match(source, /origin_iata:\s*originCountryOnly/);
  assert.match(source, /destination_iata:\s*destinationCountryOnly/);
});

test("outbound date picker is wired with hints props and visible-month callback", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  assert.match(source, /name="travel_date"/);
  assert.match(source, /dayHintsByIso=\{calendarHintsActive\?\.dayHintsByIso \|\| \{\}\}/);
  assert.match(source, /hintsLoading=\{calendarHintsLoadingKey === calendarHintsRequestKey\}/);
  assert.match(source, /showCountryEstimateBadge=\{canRequestCalendarHints && hasCountryScopeForCalendarHints\}/);
  assert.match(source, /hintScopeMode=\{calendarHintsActive\?\.scopeMode \|\| calendarHintsScopeMode\}/);
  assert.match(source, /onVisibleMonthChange=\{setCalendarVisibleMonth\}/);
});
